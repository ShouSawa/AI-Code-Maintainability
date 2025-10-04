import os
import json
import subprocess
import statistics
import random
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

class NonBugInducingCommitAnalyzer:
    def __init__(self, json_file_path, repo_name):
        self.json_file_path = json_file_path
        self.repo_name = repo_name
        self.repo_path = Path(f"../cloned_Repository/{repo_name}")
        self.output_path = Path("../data_list/RQ2/final_result/")
        
        # AI判定用パターン
        self.ai_patterns = {
            'openai_codex': [
                r'openai.*codex', r'codex', r'gpt-.*code', r'ai.*generated',
                r'automated.*fix', r'auto.*generated'
            ],
            'devin': [
                r'devin', r'devin.*ai', r'automated.*devin'
            ],
            'github_copilot': [
                r'github.*copilot', r'copilot', r'co-authored-by:.*github.*copilot',
                r'suggested.*by.*copilot', r'copilot.*suggestion'
            ],
            'cursor': [
                r'cursor.*ai', r'cursor.*editor', r'cursor.*suggestion'
            ],
            'claude_code': [
                r'claude.*code', r'claude.*ai', r'anthropic.*claude'
            ],
            'general_ai': [
                r'ai.*assisted', r'machine.*generated', r'automatically.*generated',
                r'bot.*commit', r'automated.*commit', r'ai.*commit'
            ]
        }
        
        # 統計用データ
        self.ai_change_lines = []
        self.human_change_lines = []
        self.ai_changed_files = []
        self.human_changed_files = []
        self.bug_inducing_hashes = set()
        
        # AI/Human統計
        self.stats = defaultdict(int)
        self.detailed_results = []
        
    def load_json_data(self):
        """JSONファイルを読み込む"""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading JSON file: {e}")
            return []
    
    def extract_bug_inducing_commits(self, data):
        """バグ誘発コミットのハッシュを抽出"""
        bug_inducing_commits = set()
        for entry in data:
            inducing_commits = entry.get('inducing_commit_hash', [])
            for commit_hash in inducing_commits:
                bug_inducing_commits.add(commit_hash)
        
        print(f"バグ誘発コミット数: {len(bug_inducing_commits)}")
        return bug_inducing_commits
    
    def get_all_commits(self):
        """リポジトリから全てのコミットハッシュを取得"""
        try:
            cmd = ['git', '-C', str(self.repo_path), 'log', '--all', '--pretty=format:%H']
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                print(f"Git log failed: {result.stderr}")
                return []
            
            commits = result.stdout.strip().split('\n')
            commits = [commit.strip() for commit in commits if commit.strip()]
            print(f"総コミット数: {len(commits)}")
            return commits
            
        except Exception as e:
            print(f"Error getting all commits: {e}")
            return []
    
    def get_commit_info(self, commit_hash):
        """Gitリポジトリからコミット情報を取得"""
        try:
            # コミットメッセージと作成者情報を取得
            cmd = ['git', '-C', str(self.repo_path), 'show', '--format=%B%n---AUTHOR---%n%an%n%ae', '--no-patch', commit_hash]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                return None
            
            output = result.stdout.strip()
            parts = output.split('---AUTHOR---')
            
            if len(parts) >= 2:
                commit_message = parts[0].strip()
                author_info = parts[1].strip().split('\n')
                author_name = author_info[0] if len(author_info) > 0 else ""
                author_email = author_info[1] if len(author_info) > 1 else ""
                
                return {
                    'message': commit_message,
                    'author_name': author_name,
                    'author_email': author_email
                }
            
        except Exception as e:
            print(f"Error getting commit info for {commit_hash}: {e}")
        
        return None
    
    def get_commit_changes(self, commit_hash):
        """コミットの変更行数とファイル数を取得"""
        try:
            # 変更行数を取得（--numstatで追加/削除行数を取得）
            cmd = ['git', '-C', str(self.repo_path), 'show', '--numstat', '--format=', commit_hash]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                return None
            
            total_added = 0
            total_deleted = 0
            changed_files = 0
            
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        try:
                            added = int(parts[0]) if parts[0] != '-' else 0
                            deleted = int(parts[1]) if parts[1] != '-' else 0
                            total_added += added
                            total_deleted += deleted
                            changed_files += 1
                        except ValueError:
                            # バイナリファイルなどで数値でない場合もファイルとしてカウント
                            changed_files += 1
                            continue
            
            return {
                'added': total_added,
                'deleted': total_deleted,
                'total_changes': total_added + total_deleted,
                'files_changed': changed_files
            }
            
        except Exception as e:
            print(f"Error getting commit changes for {commit_hash}: {e}")
            return None
    
    def detect_ai_commit(self, commit_info):
        """コミット情報からAIによるものか判定"""
        if not commit_info:
            return False, "unknown"
        
        text_to_check = f"{commit_info['message']} {commit_info['author_name']} {commit_info['author_email']}".lower()
        
        for ai_type, patterns in self.ai_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_to_check, re.IGNORECASE):
                    return True, ai_type
        
        return False, "human"
    
    def analyze_non_bug_commits(self):
        """バグ誘発コミット以外のコミットを分析（バグ誘発コミットの3倍の数）"""
        print("分析を開始します...")
        
        # リポジトリの存在確認
        if not self.repo_path.exists():
            print(f"エラー: リポジトリが見つかりません: {self.repo_path}")
            return
        
        # 出力ディレクトリの作成
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # JSONデータを読み込み
        data = self.load_json_data()
        if not data:
            print("JSONデータが取得できませんでした。")
            return
        
        # バグ誘発コミットを抽出
        bug_inducing_commits = self.extract_bug_inducing_commits(data)
        self.bug_inducing_hashes = bug_inducing_commits
        bug_count = len(bug_inducing_commits)
        target_non_bug_count = bug_count * 3  # 3倍に変更
        
        # 全コミットを取得
        all_commits = self.get_all_commits()
        if not all_commits:
            print("コミットが取得できませんでした。")
            return
        
        # バグ誘発コミット以外のコミットを特定
        non_bug_commits = [commit for commit in all_commits if commit not in bug_inducing_commits]
        print(f"バグ誘発コミット以外のコミット数: {len(non_bug_commits)}")
        
        # バグ誘発コミットの3倍の数だけランダムに選択
        if len(non_bug_commits) < target_non_bug_count:
            print(f"警告: 非バグ誘発コミット数({len(non_bug_commits)})がバグ誘発コミット数の3倍({target_non_bug_count})より少ないです。")
            selected_non_bug_commits = non_bug_commits
        else:
            # シードを固定してランダムサンプリングの再現性を確保
            random.seed(42)
            selected_non_bug_commits = random.sample(non_bug_commits, target_non_bug_count)
            print(f"ランダムに選択された非バグ誘発コミット数: {len(selected_non_bug_commits)} (バグ誘発コミットの3倍)")
        
        # 各コミットの変更統計とAI判定を収集
        processed_count = 0
        failed_count = 0
        
        for i, commit_hash in enumerate(selected_non_bug_commits):
            if i % 100 == 0:
                print(f"進捗: {i}/{len(selected_non_bug_commits)} コミット処理済み")
            
            # コミット情報を取得
            commit_info = self.get_commit_info(commit_hash)
            changes = self.get_commit_changes(commit_hash)
            
            if commit_info and changes:
                # AI判定を実行
                is_ai, ai_type = self.detect_ai_commit(commit_info)
                
                # 統計情報を更新
                if is_ai:
                    self.stats[f'ai_{ai_type}'] += 1
                    self.stats['total_ai'] += 1
                    # AI用の変更行数とファイル数を記録
                    self.ai_change_lines.append(changes['total_changes'])
                    self.ai_changed_files.append(changes['files_changed'])
                else:
                    self.stats['human'] += 1
                    # 人間用の変更行数とファイル数を記録
                    self.human_change_lines.append(changes['total_changes'])
                    self.human_changed_files.append(changes['files_changed'])
                
                # 詳細結果を保存
                result = {
                    'repo_name': self.repo_name,
                    'commit_hash': commit_hash,
                    'is_ai': is_ai,
                    'ai_type': ai_type,
                    'author_name': commit_info['author_name'],
                    'author_email': commit_info['author_email'],
                    'message_preview': commit_info['message'][:100] + '...' if len(commit_info['message']) > 100 else commit_info['message'],
                    'lines_added': changes['added'],
                    'lines_deleted': changes['deleted'],
                    'total_changes': changes['total_changes'],
                    'files_changed': changes['files_changed']
                }
                self.detailed_results.append(result)
                processed_count += 1
            else:
                failed_count += 1
        
        print(f"処理完了: {processed_count}件成功, {failed_count}件失敗")
        
        # 統計を計算して保存
        self.generate_and_save_report(len(all_commits), len(bug_inducing_commits), len(selected_non_bug_commits), processed_count)
    
    def calculate_statistics(self, data_list, data_name):
        """統計値を計算"""
        if not data_list:
            return None
        
        return {
            'name': data_name,
            'count': len(data_list),
            'mean': statistics.mean(data_list),
            'stdev': statistics.stdev(data_list) if len(data_list) > 1 else 0,
            'median': statistics.median(data_list),
            'min': min(data_list),
            'max': max(data_list),
            'q1': statistics.quantiles(data_list, n=4)[0] if len(data_list) >= 4 else None,
            'q3': statistics.quantiles(data_list, n=4)[2] if len(data_list) >= 4 else None
        }
    
    def generate_and_save_report(self, total_commits, bug_commits_count, selected_commits_count, processed_count):
        """統計レポートを生成・保存"""
        # 変更行数統計（AI/Human別）
        ai_line_stats = self.calculate_statistics(self.ai_change_lines, "AI変更行数")
        human_line_stats = self.calculate_statistics(self.human_change_lines, "人間変更行数")
        
        # 変更ファイル数統計（AI/Human別）
        ai_file_stats = self.calculate_statistics(self.ai_changed_files, "AI変更ファイル数")
        human_file_stats = self.calculate_statistics(self.human_changed_files, "人間変更ファイル数")
        
        # レポート生成（リポジトリ名を先頭に追加）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_path / f"{self.repo_name}_non_bug_commits_ai_analysis_{timestamp}.txt"
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("バグ誘発コミット以外のコミット AI/Human 分析結果")
        report_lines.append("=" * 80)
        report_lines.append(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"リポジトリ: {self.repo_name}")
        report_lines.append(f"リポジトリパス: {self.repo_path.absolute()}")
        report_lines.append(f"JSONファイル: {self.json_file_path}")
        report_lines.append("")
        
        # 全体統計
        report_lines.append("=" * 50)
        report_lines.append("全体統計")
        report_lines.append("=" * 50)
        report_lines.append(f"総コミット数: {total_commits:,}")
        report_lines.append(f"バグ誘発コミット数: {bug_commits_count:,}")
        report_lines.append(f"選択された非バグ誘発コミット数: {selected_commits_count:,}")
        report_lines.append(f"分析成功コミット数: {processed_count:,}")
        report_lines.append(f"分析成功率: {(processed_count/selected_commits_count)*100:.2f}%")
        report_lines.append(f"※バグ誘発コミットの3倍の数だけランダムに選択（シード値: 42）")  # 変更
        report_lines.append("")
        
        # AI vs Human統計
        total_ai = self.stats['total_ai']
        human_commits = self.stats['human']
        total_analyzed = total_ai + human_commits
        
        if total_analyzed > 0:
            report_lines.append("=" * 50)
            report_lines.append("AI vs Human 統計")
            report_lines.append("=" * 50)
            report_lines.append(f"AIコミット数: {total_ai:,} ({total_ai/total_analyzed*100:.1f}%)")
            report_lines.append(f"人間コミット数: {human_commits:,} ({human_commits/total_analyzed*100:.1f}%)")
            report_lines.append("")
            
            # AI種類別統計
            if total_ai > 0:
                report_lines.append("AI種類別内訳:")
                for key, count in self.stats.items():
                    if key.startswith('ai_') and count > 0:
                        ai_type = key.replace('ai_', '').replace('_', ' ').title()
                        percentage = count / total_ai * 100
                        report_lines.append(f"  {ai_type}: {count} ({percentage:.1f}% of AI commits)")
                report_lines.append("")
        
        # AI変更行数統計
        if ai_line_stats:
            report_lines.append("=" * 50)
            report_lines.append("AI変更行数統計 (バグ誘発コミット以外)")
            report_lines.append("=" * 50)
            report_lines.append(f"分析対象コミット数: {ai_line_stats['count']:,}")
            report_lines.append(f"平均変更行数: {ai_line_stats['mean']:.2f}")
            report_lines.append(f"標準偏差: {ai_line_stats['stdev']:.2f}")
            report_lines.append(f"中央値: {ai_line_stats['median']:.0f}")
            report_lines.append(f"最小値: {ai_line_stats['min']:,}")
            report_lines.append(f"最大値: {ai_line_stats['max']:,}")
            if ai_line_stats['q1'] and ai_line_stats['q3']:
                report_lines.append(f"第1四分位数 (Q1): {ai_line_stats['q1']:.2f}")
                report_lines.append(f"第3四分位数 (Q3): {ai_line_stats['q3']:.2f}")
                report_lines.append(f"四分位範囲 (IQR): {ai_line_stats['q3'] - ai_line_stats['q1']:.2f}")
            report_lines.append("")
        
        # 人間変更行数統計
        if human_line_stats:
            report_lines.append("=" * 50)
            report_lines.append("人間変更行数統計 (バグ誘発コミット以外)")
            report_lines.append("=" * 50)
            report_lines.append(f"分析対象コミット数: {human_line_stats['count']:,}")
            report_lines.append(f"平均変更行数: {human_line_stats['mean']:.2f}")
            report_lines.append(f"標準偏差: {human_line_stats['stdev']:.2f}")
            report_lines.append(f"中央値: {human_line_stats['median']:.0f}")
            report_lines.append(f"最小値: {human_line_stats['min']:,}")
            report_lines.append(f"最大値: {human_line_stats['max']:,}")
            if human_line_stats['q1'] and human_line_stats['q3']:
                report_lines.append(f"第1四分位数 (Q1): {human_line_stats['q1']:.2f}")
                report_lines.append(f"第3四分位数 (Q3): {human_line_stats['q3']:.2f}")
                report_lines.append(f"四分位範囲 (IQR): {human_line_stats['q3'] - human_line_stats['q1']:.2f}")
            report_lines.append("")
        
        # AI変更ファイル数統計
        if ai_file_stats:
            report_lines.append("=" * 50)
            report_lines.append("AI変更ファイル数統計 (バグ誘発コミット以外)")
            report_lines.append("=" * 50)
            report_lines.append(f"分析対象コミット数: {ai_file_stats['count']:,}")
            report_lines.append(f"平均変更ファイル数: {ai_file_stats['mean']:.2f}")
            report_lines.append(f"標準偏差: {ai_file_stats['stdev']:.2f}")
            report_lines.append(f"中央値: {ai_file_stats['median']:.0f}")
            report_lines.append(f"最小値: {ai_file_stats['min']:,}")
            report_lines.append(f"最大値: {ai_file_stats['max']:,}")
            if ai_file_stats['q1'] and ai_file_stats['q3']:
                report_lines.append(f"第1四分位数 (Q1): {ai_file_stats['q1']:.2f}")
                report_lines.append(f"第3四分位数 (Q3): {ai_file_stats['q3']:.2f}")
                report_lines.append(f"四分位範囲 (IQR): {ai_file_stats['q3'] - ai_file_stats['q1']:.2f}")
            report_lines.append("")
        
        # 人間変更ファイル数統計
        if human_file_stats:
            report_lines.append("=" * 50)
            report_lines.append("人間変更ファイル数統計 (バグ誘発コミット以外)")
            report_lines.append("=" * 50)
            report_lines.append(f"分析対象コミット数: {human_file_stats['count']:,}")
            report_lines.append(f"平均変更ファイル数: {human_file_stats['mean']:.2f}")
            report_lines.append(f"標準偏差: {human_file_stats['stdev']:.2f}")
            report_lines.append(f"中央値: {human_file_stats['median']:.0f}")
            report_lines.append(f"最小値: {human_file_stats['min']:,}")
            report_lines.append(f"最大値: {human_file_stats['max']:,}")
            if human_file_stats['q1'] and human_file_stats['q3']:
                report_lines.append(f"第1四分位数 (Q1): {human_file_stats['q1']:.2f}")
                report_lines.append(f"第3四分位数 (Q3): {human_file_stats['q3']:.2f}")
                report_lines.append(f"四分位範囲 (IQR): {human_file_stats['q3'] - human_file_stats['q1']:.2f}")
            report_lines.append("")
        
        # 比較サマリー
        if ai_line_stats and human_line_stats and ai_file_stats and human_file_stats:
            report_lines.append("=" * 50)
            report_lines.append("AI vs Human 比較サマリー")
            report_lines.append("=" * 50)
            report_lines.append("変更行数比較:")
            report_lines.append(f"  AI平均: {ai_line_stats['mean']:.2f} 行")
            report_lines.append(f"  人間平均: {human_line_stats['mean']:.2f} 行")
            report_lines.append(f"  差異: {ai_line_stats['mean'] - human_line_stats['mean']:.2f} 行")
            report_lines.append("")
            report_lines.append("変更ファイル数比較:")
            report_lines.append(f"  AI平均: {ai_file_stats['mean']:.2f} ファイル")
            report_lines.append(f"  人間平均: {human_file_stats['mean']:.2f} ファイル")
            report_lines.append(f"  差異: {ai_file_stats['mean'] - human_file_stats['mean']:.2f} ファイル")
            report_lines.append("")
        
        # ファイルに保存
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            print(f"\n結果が保存されました: {output_file}")
        except Exception as e:
            print(f"ファイル保存エラー: {e}")
            return
        
        # コンソール出力
        print("\n" + "=" * 60)
        print("分析結果サマリー")
        print("=" * 60)
        print(f"リポジトリ: {self.repo_name}")
        print(f"総コミット数: {total_commits:,}")
        print(f"バグ誘発コミット数: {bug_commits_count:,}")
        print(f"選択された非バグ誘発コミット数: {selected_commits_count:,}")
        print(f"分析成功: {processed_count:,} コミット")
        print(f"AIコミット: {total_ai:,}, 人間コミット: {human_commits:,}")
        
        if ai_line_stats:
            print(f"\nAI変更行数統計:")
            print(f"  平均: {ai_line_stats['mean']:.2f} 行")
            print(f"  標準偏差: {ai_line_stats['stdev']:.2f}")
            print(f"  中央値: {ai_line_stats['median']:.0f} 行")
        
        if human_line_stats:
            print(f"\n人間変更行数統計:")
            print(f"  平均: {human_line_stats['mean']:.2f} 行")
            print(f"  標準偏差: {human_line_stats['stdev']:.2f}")
            print(f"  中央値: {human_line_stats['median']:.0f} 行")
        
        if ai_file_stats:
            print(f"\nAI変更ファイル数統計:")
            print(f"  平均: {ai_file_stats['mean']:.2f} ファイル")
            print(f"  標準偏差: {ai_file_stats['stdev']:.2f}")
            print(f"  中央値: {ai_file_stats['median']:.0f} ファイル")
        
        if human_file_stats:
            print(f"\n人間変更ファイル数統計:")
            print(f"  平均: {human_file_stats['mean']:.2f} ファイル")
            print(f"  標準偏差: {human_file_stats['stdev']:.2f}")
            print(f"  中央値: {human_file_stats['median']:.0f} ファイル")

def main():
    # 設定 - ここを変更して使用
    repo_name = "Python"  # リポジトリ名
    json_file = rf"c:\Users\Shota\Local_document\AI-Code-Maintainability\pyszz_v2\out\{repo_name}_bic_config.json"
    
    # ファイルの存在確認
    if not os.path.exists(json_file):
        print(f"JSONファイルが見つかりません: {json_file}")
        return
    
    # 分析実行
    analyzer = NonBugInducingCommitAnalyzer(json_file, repo_name)
    analyzer.analyze_non_bug_commits()

if __name__ == "__main__":
    main()