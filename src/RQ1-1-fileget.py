"""
AIファイル作成分析プログラム
機能: 100リポジトリを調査し、2025/1/1～2025/8/20のコミットからAI作成ファイルを検出
     月ごとのAIファイル作成数を集計
"""

import os
import pandas as pd
from datetime import datetime, timedelta, timezone
import re
import time
from github import Github
from dotenv import load_dotenv
import json
import csv
import socket  # ネットワーク接続確認用
from collections import defaultdict
from tqdm import tqdm  # 進捗表示用
import random  # ランダム選択用

# srcフォルダ内の.envファイルを読み込む
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path)


# ネットワーク再接続機能
def check_network_connectivity(host="api.github.com", port=443, timeout=5):
    """
    ネットワーク接続を確認する
    
    Args:
        host: 接続先ホスト
        port: 接続ポート
        timeout: タイムアウト（秒）
    
    Returns:
        bool: 接続可能ならTrue
    """
    try:
        socket.create_connection((host, port), timeout=timeout)
        return True
    except (socket.gaierror, socket.timeout, OSError):
        return False

def retry_with_network_check(func):
    """
    ネットワークエラー時に自動的に再接続を試みるデコレータ
    
    Args:
        func: ラップする関数
    
    Returns:
        ラップされた関数
    """
    def wrapper(*args, **kwargs):
        max_wait = 60  # 最大待機時間（秒）
        wait_time = 10  # 初期待機時間（秒）
        
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e).lower()
                # DNS解決エラーやConnectionErrorを検出
                if 'nameresolutionerror' in error_str or 'failed to resolve' in error_str or \
                   'connectionerror' in error_str or 'connection error' in error_str or \
                   'getaddrinfo failed' in error_str:
                    
                    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ネットワークエラーを検出しました: {e}")
                    print(f"ネットワーク接続を確認中...")
                    
                    # ネットワークが復旧するまで待機
                    while not check_network_connectivity():
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ネットワークに接続できません。{wait_time}秒後に再試行します...")
                        time.sleep(wait_time)
                        # 指数バックオフ（最大60秒まで）
                        wait_time = min(wait_time * 2, max_wait)
                    
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ネットワーク接続が復旧しました。処理を再開します...")
                    wait_time = 10  # 待機時間をリセット
                    continue  # 関数を再実行
                else:
                    # ネットワーク以外のエラーはそのまま送出
                    raise
    
    return wrapper


class AIFileAnalyzer:
    """AIファイル作成分析クラス"""
    
    # AIボットアカウント定義
    AI_BOT_ACCOUNTS = {
        'copilot': ['copilot'],
        'cursor': ['cursor'],
        'devin': ['devin-ai-integration'],
        'claude': ['claude']
    }
    
    def __init__(self, github_token):
        """初期化"""
        self.github_token = github_token
        if not self.github_token:
            raise ValueError("GitHub tokenが必要です。.envファイルにGITHUB_TOKENを設定してください。")
        
        self.g = Github(self.github_token)
        
        # 出力ディレクトリ
        self.output_dir = os.path.join(script_dir, "../dataset")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 分析期間設定（2025/1/1 ～ 2025/7/31）
        # UTCタイムゾーン付きで作成（GitHubのコミット日時と比較できるように）
        self.start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.end_date = datetime(2025, 7, 31, 23, 59, 59, tzinfo=timezone.utc)
        self.end_date_may = datetime(2025, 5, 31, 23, 59, 59, tzinfo=timezone.utc)  # 5月末
        self.end_date_june = datetime(2025, 6, 30, 23, 59, 59, tzinfo=timezone.utc)  # 6月末（6/31は存在しないので6/30）
        
        # 結果保存用
        self.all_ai_files = []  # 全AI作成ファイル情報
        self.monthly_stats = defaultdict(int)  # 月ごとのAIファイル作成数
        
        # CSVファイルの初期化
        self.csv_path = os.path.join(self.output_dir, "file_list.csv")
        self._initialize_csv()
    
    def _initialize_csv(self):
        """CSVファイルを初期化してヘッダーを書き込む"""
        with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['リポジトリ名', 'ファイル名', 'ファイル作成者（全員）', 'AI/人間'])
    
    def is_ai_generated_commit(self, commit):
        """コミットがAI生成かどうか判定"""
        try:
            # コミット作成者名を取得
            author_name = ""
            if commit.author:
                author_name = commit.author.login.lower() if commit.author.login else ""
            
            # コミッターも確認
            committer_name = ""
            if commit.committer:
                committer_name = commit.committer.login.lower() if commit.committer.login else ""
            
            # AI判定
            all_authors = [author_name, committer_name]
            
            for author in all_authors:
                for ai_type, keywords in self.AI_BOT_ACCOUNTS.items():
                    for keyword in keywords:
                        if keyword in author:
                            return True, ai_type.capitalize()
            
            return False, None
            
        except Exception as e:
            return False, None
    
    def detect_ai_tool(self, commit):
        """AIツールを特定"""
        try:
            author_name = ""
            if commit.author:
                author_name = commit.author.login.lower() if commit.author.login else ""
            
            committer_name = ""
            if commit.committer:
                committer_name = commit.committer.login.lower() if commit.committer.login else ""
            
            all_authors = [author_name, committer_name]
            
            tool_map = {
                'copilot': 'Copilot',
                'cursor': 'Cursor',
                'devin': 'Devin',
                'claude': 'Claude'
            }
            
            for author in all_authors:
                for key, tool_name in tool_map.items():
                    if key in author:
                        return tool_name
            
            return 'Unknown'
            
        except Exception:
            return 'Unknown'
    
    @retry_with_network_check
    def get_human_created_files(self, repo_full_name, count):
        """人間作成ファイルを取得"""
        try:
            repo = self.g.get_repo(repo_full_name)
            commits = repo.get_commits(since=self.start_date, until=self.end_date)
            
            human_files = []
            checked_files = set()
            
            for commit in commits:
                # AI生成コミットでないか判定
                is_ai, _ = self.is_ai_generated_commit(commit)
                
                if not is_ai:
                    try:
                        for file in commit.files:
                            # 新規追加ファイルのみ
                            if file.status == 'added' and file.filename not in checked_files:
                                checked_files.add(file.filename)
                                
                                # 作成者情報を取得
                                authors = set()
                                if commit.author and commit.author.login:
                                    authors.add(commit.author.login)
                                if commit.committer and commit.committer.login:
                                    authors.add(commit.committer.login)
                                
                                human_files.append({
                                    'file_path': file.filename,
                                    'authors': ', '.join(sorted(authors)) if authors else 'Unknown',
                                    'commit_sha': commit.sha
                                })
                                
                                # 十分な数が集まったら終了
                                if len(human_files) >= count * 3:  # 少し多めに取得
                                    break
                    except Exception:
                        continue
                
                if len(human_files) >= count * 3:
                    break
                
                time.sleep(0.05)
            
            return human_files
            
        except Exception as e:
            tqdm.write(f"  人間作成ファイル取得エラー: {e}")
            return []
    
    def save_files_to_csv(self, repo_full_name, ai_files, human_files):
        """AI作成ファイルと人間作成ファイルをCSVに記録"""
        with open(self.csv_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            
            # AI作成ファイルを記録
            for ai_file in ai_files:
                # 作成者情報を取得（AI toolと実際の作成者）
                authors = ai_file.get('ai_tool', 'AI')
                writer.writerow([
                    repo_full_name,
                    ai_file['file_path'],
                    authors,
                    'AI'
                ])
            
            # 人間作成ファイルを記録
            for human_file in human_files:
                writer.writerow([
                    repo_full_name,
                    human_file['file_path'],
                    human_file['authors'],
                    '人間'
                ])
    
    @retry_with_network_check
    def analyze_repo_ai_files(self, repo_full_name):
        """リポジトリのAI作成ファイルを分析"""
        print(f"\n分析中: {repo_full_name}")
        
        try:
            repo = self.g.get_repo(repo_full_name)
            
            # 期間内のコミットを取得（新しい順）
            commits = repo.get_commits(since=self.start_date, until=self.end_date)
            
            # コミット総数を取得（進捗バー用）
            commits_list = list(commits)
            
            ai_files_in_repo = []
            checked_files = set()  # 重複チェック用
            
            # 期間別コミット数カウント用
            commit_count = 0
            commit_count_until_may = 0
            commit_count_until_june = 0
            
            # 期間別AI作成ファイル数カウント用
            ai_files_count_total = 0
            ai_files_count_until_may = 0
            ai_files_count_until_june = 0
            
            for commit in tqdm(commits_list, desc=f"  コミット処理", leave=False):
                commit_count += 1
                
                # コミット日時取得
                commit_date = commit.commit.author.date
                
                # 5月末までのコミットか判定
                if commit_date <= self.end_date_may:
                    commit_count_until_may += 1
                
                # 6月末までのコミットか判定
                if commit_date <= self.end_date_june:
                    commit_count_until_june += 1
                
                # AI生成コミットか判定
                is_ai, ai_tool = self.is_ai_generated_commit(commit)
                
                if is_ai:
                    # コミットで追加されたファイルを確認
                    try:
                        for file in commit.files:
                            # 新規追加ファイルのみ
                            if file.status == 'added' and file.filename not in checked_files:
                                checked_files.add(file.filename)
                                
                                # 月別キーを生成
                                month_key = f"{commit_date.year}-{commit_date.month:02d}"
                                
                                ai_file_info = {
                                    'repo': repo_full_name,
                                    'file_path': file.filename,
                                    'ai_tool': ai_tool if ai_tool else self.detect_ai_tool(commit),
                                    'created_date': commit_date.strftime('%Y-%m-%d %H:%M:%S'),
                                    'month': month_key,
                                    'commit_sha': commit.sha
                                }
                                
                                ai_files_in_repo.append(ai_file_info)
                                self.monthly_stats[month_key] += 1
                                
                                # 期間別AI作成ファイル数カウント
                                ai_files_count_total += 1
                                if commit_date <= self.end_date_may:
                                    ai_files_count_until_may += 1
                                if commit_date <= self.end_date_june:
                                    ai_files_count_until_june += 1
                                
                    except Exception as e:
                        print(f"  ファイル情報取得エラー: {e}")
                        continue
                
                # API rate limit対策
                time.sleep(0.05)
            
            print(f"  → コミット総数: {commit_count}件")
            print(f"  → AI作成ファイル数: {len(ai_files_in_repo)}件")
            
            # AI作成ファイルと人間作成ファイルをランダム選択してCSVに記録
            if len(ai_files_in_repo) > 0:
                # AI作成ファイルをランダムに最大10個選択
                num_ai_files = min(10, len(ai_files_in_repo))
                selected_ai_files = random.sample(ai_files_in_repo, num_ai_files)
                
                # 同数の人間作成ファイルを取得
                tqdm.write(f"  人間作成ファイルを取得中...")
                all_human_files = self.get_human_created_files(repo_full_name, num_ai_files)
                
                # 人間作成ファイルをランダムに選択
                if len(all_human_files) >= num_ai_files:
                    selected_human_files = random.sample(all_human_files, num_ai_files)
                else:
                    selected_human_files = all_human_files  # 全部使う
                
                # CSVに記録
                self.save_files_to_csv(repo_full_name, selected_ai_files, selected_human_files)
                tqdm.write(f"  → CSV記録: AI {len(selected_ai_files)}件, 人間 {len(selected_human_files)}件")
            
            return {
                'repo': repo_full_name,
                'stars': repo.stargazers_count,
                'ai_files_count': len(ai_files_in_repo),
                'ai_files': ai_files_in_repo,
                'total_commits': commit_count,
                'commits_until_may': commit_count_until_may,
                'commits_until_june': commit_count_until_june,
                'ai_files_count_total': ai_files_count_total,
                'ai_files_count_until_may': ai_files_count_until_may,
                'ai_files_count_until_june': ai_files_count_until_june
            }
            
        except Exception as e:
            print(f"  エラー: {e}")
            return None
    
    def analyze_repositories(self, target_count=100):
        """複数リポジトリを分析（AIファイルがないリポジトリはスキップ）"""
        print("="*80)
        print("AIファイル作成分析開始")
        print(f"対象期間: {self.start_date.strftime('%Y/%m/%d')} ～ {self.end_date.strftime('%Y/%m/%d')}")
        print(f"目標リポジトリ数: {target_count}件（AIファイルがあるもののみ）")
        print("="*80)
        
        # repository_list.csvを読み込む
        csv_path = os.path.join(script_dir, "../dataset/repository_list.csv")
        if not os.path.exists(csv_path):
            print(f"エラー: {csv_path} が見つかりません")
            return
        
        df = pd.read_csv(csv_path)
        print(f"リポジトリリスト読み込み完了: {len(df)}件\n")
        
        results = []
        skipped_repos = []
        failed_repos = []
        
        index = 0
        # 進捗バーを作成（目標数ではなく試行数をカウント）
        pbar = tqdm(total=target_count, desc="リポジトリ分析", unit="repo")
        
        while len(results) < target_count and index < len(df):
            row = df.iloc[index]
            repo_full_name = f"{row['owner']}/{row['repository_name']}"
            
            pbar.set_description(f"リポジトリ分析 [試行: {index + 1}] [成功: {len(results)}/{target_count}]")
            
            result = self.analyze_repo_ai_files(repo_full_name)
            
            if result:
                if result['ai_files_count'] > 0:
                    # AI作成ファイルがある場合のみ成功とする
                    results.append(result)
                    self.all_ai_files.extend(result['ai_files'])
                    pbar.update(1)
                    tqdm.write(f"  ✓ 成功: {repo_full_name} (AI作成ファイル: {result['ai_files_count']}件)")
                else:
                    # AI作成ファイルがない場合はスキップ（コミット数情報は保持）
                    skipped_repos.append({
                        'repo': repo_full_name,
                        'reason': 'AIファイルが見つからない',
                        'stars': result['stars'],
                        'total_commits': result['total_commits'],
                        'commits_until_may': result['commits_until_may'],
                        'commits_until_june': result['commits_until_june']
                    })
                    tqdm.write(f"  ⊘ スキップ: {repo_full_name} (AIファイルなし)")
            else:
                failed_repos.append(repo_full_name)
                tqdm.write(f"  ✗ エラー: {repo_full_name}")
            
            index += 1
            
            # API rate limit対策
            time.sleep(1)
        
        pbar.close()
        
        print(f"\n{'='*80}")
        print(f"分析完了")
        print(f"  成功: {len(results)}件")
        print(f"  スキップ: {len(skipped_repos)}件")
        print(f"  失敗: {len(failed_repos)}件")
        print(f"  試行総数: {index}件")
        print(f"  AI作成ファイル総数: {len(self.all_ai_files)}件")
        print(f"{'='*80}")
        
        # 結果を保存
        self.save_results(results, skipped_repos, failed_repos)
        self.save_monthly_stats()
        
        return results
    
    def save_results(self, results, skipped_repos, failed_repos):
        """結果をテキストファイルに保存"""
        output_path = os.path.join(self.output_dir, "ai_files_analysis_results.txt")
        
        total_ai_files = sum(r['ai_files_count'] for r in results)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("AIファイル作成分析結果\n")
            f.write(f"対象期間: {self.start_date.strftime('%Y/%m/%d')} ～ {self.end_date.strftime('%Y/%m/%d')}\n")
            f.write(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"分析成功リポジトリ数: {len(results)}\n")
            f.write(f"スキップリポジトリ数: {len(skipped_repos)}\n")
            f.write(f"失敗リポジトリ数: {len(failed_repos)}\n")
            f.write(f"AI作成ファイル総数: {total_ai_files}件\n")
            f.write("="*80 + "\n\n")
            
            f.write("■ 分析成功リポジトリ一覧\n")
            f.write("-"*80 + "\n")
            for i, result in enumerate(results, 1):
                f.write(f"{i}. {result['repo']}\n")
                f.write(f"   スター数: {result['stars']:,}\n")
                f.write(f"   [2025/1/1～2025/8/20]\n")
                f.write(f"     コミット数: {result['total_commits']}件\n")
                f.write(f"     AI作成ファイル数: {result['ai_files_count_total']}件\n")
                f.write(f"   [2025/1/1～2025/5/31]\n")
                f.write(f"     コミット数: {result['commits_until_may']}件\n")
                f.write(f"     AI作成ファイル数: {result['ai_files_count_until_may']}件\n")
                f.write(f"   [2025/1/1～2025/6/30]\n")
                f.write(f"     コミット数: {result['commits_until_june']}件\n")
                f.write(f"     AI作成ファイル数: {result['ai_files_count_until_june']}件\n\n")
            
            if skipped_repos:
                f.write("\n■ スキップしたリポジトリ\n")
                f.write("-"*80 + "\n")
                for i, skipped in enumerate(skipped_repos, 1):
                    f.write(f"{i}. {skipped['repo']} ({skipped['reason']})\n")
                    if 'stars' in skipped:
                        f.write(f"   スター数: {skipped['stars']:,}\n")
                    if 'total_commits' in skipped:
                        f.write(f"\n")
                        f.write(f"   [2025/1/1～2025/8/20]\n")
                        f.write(f"     コミット数: {skipped['total_commits']}件\n")
                        f.write(f"\n")
                        f.write(f"   [2025/1/1～2025/5/31]\n")
                        f.write(f"     コミット数: {skipped['commits_until_may']}件\n")
                        f.write(f"\n")
                        f.write(f"   [2025/1/1～2025/6/30]\n")
                        f.write(f"     コミット数: {skipped['commits_until_june']}件\n")
                    f.write(f"\n")
                f.write("\n")
            
            if failed_repos:
                f.write("\n■ 失敗したリポジトリ\n")
                f.write("-"*80 + "\n")
                for failed in failed_repos:
                    f.write(f"  - {failed}\n")
        
        print(f"\n結果を保存しました: {output_path}")
    
    def save_monthly_stats(self):
        """月ごとの統計を保存"""
        output_path = os.path.join(self.output_dir, "ai_files_monthly_stats.txt")
        
        # 月ごとにソート
        sorted_months = sorted(self.monthly_stats.items())
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("月ごとのAIファイル作成数統計\n")
            f.write(f"対象期間: {self.start_date.strftime('%Y/%m/%d')} ～ {self.end_date.strftime('%Y/%m/%d')}\n")
            f.write(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*80 + "\n\n")
            
            total = sum(self.monthly_stats.values())
            
            for month, count in sorted_months:
                percentage = (count / total * 100) if total > 0 else 0
                f.write(f"{month}: {count}件 ({percentage:.1f}%)\n")
            
            f.write(f"\n合計: {total}件\n")
            
            # 最も多い月を特定
            if sorted_months:
                max_month = max(sorted_months, key=lambda x: x[1])
                f.write(f"\n最もAIファイル作成が多い月: {max_month[0]} ({max_month[1]}件)\n")
        
        print(f"月ごとの統計を保存しました: {output_path}")
        
        # コンソールにも表示
        print("\n" + "="*80)
        print("月ごとのAIファイル作成数")
        print("="*80)
        for month, count in sorted_months:
            percentage = (count / sum(self.monthly_stats.values()) * 100) if sum(self.monthly_stats.values()) > 0 else 0
            print(f"{month}: {count}件 ({percentage:.1f}%)")
        print(f"\n合計: {sum(self.monthly_stats.values())}件")
        if sorted_months:
            max_month = max(sorted_months, key=lambda x: x[1])
            print(f"最も多い月: {max_month[0]} ({max_month[1]}件)")
        print("="*80)


def main():
    """メイン処理"""
    # GitHub tokenを取得
    github_token = os.getenv('GITHUB_TOKEN')
    
    if not github_token:
        print("エラー: GITHUB_TOKENが設定されていません")
        print("src/.envファイルにGITHUB_TOKEN=your_token_hereを設定してください")
        return
    
    # 分析実行
    analyzer = AIFileAnalyzer(github_token)
    results = analyzer.analyze_repositories(target_count=100)
    
    print("\n" + "="*80)
    print("全ての処理が完了しました！")
    print("="*80)


if __name__ == "__main__":
    main()
