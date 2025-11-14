"""
180日以前のコミット分析プログラム
機能: repository_listから上位100個のリポジトリの180日以前のコミットを分析
"""

import os
import pandas as pd
from datetime import datetime, timedelta
import re
import time
from github import Github
from dotenv import load_dotenv
import json

# srcフォルダ内の.envファイルを読み込む
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path)


class OldCommitAnalyzer:
    """180日以前のコミットを分析するクラス"""
    
    # AIパターン定義
    AI_PATTERNS = {
        'copilot': [r'github.*copilot', r'copilot', r'co-authored-by:.*github.*copilot'],
        'codex': [r'openai.*codex', r'codex', r'gpt-.*code'],
        'devin': [r'devin', r'devin.*ai'],
        'cursor': [r'cursor.*ai', r'cursor.*editor'],
        'claude': [r'claude.*code', r'claude.*ai', r'anthropic'],
        'general': [r'ai.*assisted', r'machine.*generated', r'bot.*commit', r'automated.*commit', r'ai.*commit']
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
        
    def is_ai_generated_commit(self, commit_message, author_name, author_email):
        """AIコミット判定"""
        text = f"{commit_message} {author_name} {author_email}".lower()
        
        for ai_type, patterns in self.AI_PATTERNS.items():
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
                return True, ai_type
        return False, "human"
    
    def detect_specific_ai_tool(self, commit_message, author_name, author_email):
        """AIツール特定"""
        text = f"{commit_message} {author_name} {author_email}".lower()
        
        tool_map = {
            'GitHub Copilot': [r'github.*copilot', r'copilot'],
            'OpenAI Codex': [r'openai.*codex', r'codex'],
            'Devin': [r'devin'],
            'Cursor': [r'cursor.*ai', r'cursor.*editor'],
            'Claude Code': [r'claude.*code', r'claude.*ai', r'anthropic'],
            'ChatGPT/OpenAI': [r'gpt', r'chatgpt', r'openai']
        }
        
        for tool, patterns in tool_map.items():
            if any(re.search(pattern, text) for pattern in patterns):
                return tool
        return 'General AI'
    
    def check_repo_has_old_commits(self, repo_full_name):
        """リポジトリに180日以前のコミットがあるかチェック"""
        try:
            repo = self.g.get_repo(repo_full_name)
            cutoff_date = datetime.now() - timedelta(days=180)
            
            # 180日以前のコミットを取得（1件でも取得できればOK）
            commits = repo.get_commits(until=cutoff_date)
            
            # 最初の1件だけ確認
            try:
                first_commit = commits[0]
                return True
            except:
                return False
                
        except Exception as e:
            print(f"  エラー: {e}")
            return False
    
    def analyze_repo_commits(self, repo_full_name, max_commits=500):
        """リポジトリの180日以前のコミットを分析"""
        print(f"\n{'='*80}")
        print(f"分析中: {repo_full_name}")
        print(f"{'='*80}")
        
        try:
            repo = self.g.get_repo(repo_full_name)
            print(f"スター数: {repo.stargazers_count}, フォーク数: {repo.forks_count}")
            
            cutoff_date = datetime.now() - timedelta(days=180)
            print(f"対象期間: ~{cutoff_date.date()}")
            
            # 180日以前のコミットを取得
            commits = repo.get_commits(until=cutoff_date)
            
            ai_count = 0
            human_count = 0
            ai_tools = {}
            total_analyzed = 0
            
            for commit in commits:
                if total_analyzed >= max_commits:
                    print(f"最大コミット数({max_commits})に達しました")
                    break
                
                total_analyzed += 1
                if total_analyzed % 100 == 0:
                    print(f"  処理中: {total_analyzed}件...")
                
                try:
                    author_name = commit.commit.author.name or "Unknown"
                    author_email = commit.commit.author.email or "unknown@example.com"
                    message = commit.commit.message
                    
                    # AI判定
                    is_ai, ai_type = self.is_ai_generated_commit(message, author_name, author_email)
                    
                    if is_ai:
                        ai_count += 1
                        ai_tool = self.detect_specific_ai_tool(message, author_name, author_email)
                        ai_tools[ai_tool] = ai_tools.get(ai_tool, 0) + 1
                    else:
                        human_count += 1
                    
                    # API rate limit対策
                    time.sleep(0.05)
                    
                except Exception as e:
                    print(f"  コミット処理エラー: {e}")
                    continue
            
            result = {
                'repo': repo_full_name,
                'stars': repo.stargazers_count,
                'total_commits': total_analyzed,
                'ai_commits': ai_count,
                'human_commits': human_count,
                'ai_tools': ai_tools,
                'ai_ratio': ai_count / total_analyzed if total_analyzed > 0 else 0
            }
            
            print(f"\n結果:")
            print(f"  総コミット数: {total_analyzed}")
            print(f"  AIコミット: {ai_count} ({ai_count/total_analyzed*100:.2f}%)")
            print(f"  Humanコミット: {human_count} ({human_count/total_analyzed*100:.2f}%)")
            if ai_tools:
                print(f"  使用AIツール: {ai_tools}")
            
            return result
            
        except Exception as e:
            print(f"リポジトリ分析エラー: {e}")
            return None
    
    def analyze_top_100_repos(self):
        """repository_listから上位100個のリポジトリを分析"""
        print("="*80)
        print("180日以前のコミット分析開始")
        print("="*80)
        
        # repository_list.csvを読み込む
        csv_path = os.path.join(script_dir, "../dataset/repository_list.csv")
        if not os.path.exists(csv_path):
            print(f"エラー: {csv_path} が見つかりません")
            return
        
        df = pd.read_csv(csv_path)
        print(f"リポジトリリスト読み込み完了: {len(df)}件")
        
        results = []
        analyzed_count = 0
        skipped_count = 0
        index = 0
        
        while analyzed_count < 100 and index < len(df):
            row = df.iloc[index]
            repo_full_name = f"{row['owner']}/{row['repository_name']}"
            
            print(f"\n[{analyzed_count + 1}/100] チェック中: {repo_full_name} (スター: {row['stars']})")
            
            # 180日以前のコミットがあるかチェック
            has_old_commits = self.check_repo_has_old_commits(repo_full_name)
            
            if has_old_commits:
                print(f"  ✓ 180日以前のコミットあり - 分析開始")
                result = self.analyze_repo_commits(repo_full_name)
                
                if result:
                    results.append(result)
                    analyzed_count += 1
                    print(f"  ✓ 分析完了 ({analyzed_count}/100)")
                else:
                    print(f"  × 分析失敗 - スキップ")
                    skipped_count += 1
            else:
                print(f"  × 180日以前のコミットなし - スキップ")
                skipped_count += 1
            
            index += 1
            
            # 進捗保存（10件ごと）
            if analyzed_count % 10 == 0 and analyzed_count > 0:
                self.save_intermediate_results(results)
            
            # API rate limit対策
            time.sleep(1)
        
        print(f"\n{'='*80}")
        print(f"分析完了")
        print(f"  分析成功: {analyzed_count}件")
        print(f"  スキップ: {skipped_count}件")
        print(f"  確認総数: {index}件")
        print(f"{'='*80}")
        
        # 最終結果を保存
        self.save_final_results(results)
        return results
    
    def save_intermediate_results(self, results):
        """中間結果を保存"""
        output_path = os.path.join(self.output_dir, "dataset_AI_progress.txt")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("180日以前のコミット分析 - 中間結果\n")
            f.write(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"分析済みリポジトリ数: {len(results)}\n")
            f.write("="*80 + "\n\n")
            
            for result in results:
                self.write_result(f, result)
        
        print(f"  中間結果を保存: {output_path}")
    
    def save_final_results(self, results):
        """最終結果を保存"""
        output_path = os.path.join(self.output_dir, "dataset_AI.txt")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("180日以前のコミット分析 - 最終結果\n")
            f.write(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"分析リポジトリ数: {len(results)}\n")
            f.write("="*80 + "\n\n")
            
            # 全体統計
            total_commits = sum(r['total_commits'] for r in results)
            total_ai = sum(r['ai_commits'] for r in results)
            total_human = sum(r['human_commits'] for r in results)
            
            f.write("【全体統計】\n")
            f.write(f"総コミット数: {total_commits:,}\n")
            f.write(f"AIコミット数: {total_ai:,} ({total_ai/total_commits*100:.2f}%)\n")
            f.write(f"Humanコミット数: {total_human:,} ({total_human/total_commits*100:.2f}%)\n\n")
            
            # AIツール統計
            all_ai_tools = {}
            for result in results:
                for tool, count in result['ai_tools'].items():
                    all_ai_tools[tool] = all_ai_tools.get(tool, 0) + count
            
            if all_ai_tools:
                f.write("【使用AIツール統計】\n")
                sorted_tools = sorted(all_ai_tools.items(), key=lambda x: x[1], reverse=True)
                for tool, count in sorted_tools:
                    f.write(f"  {tool}: {count:,}件 ({count/total_ai*100:.2f}%)\n")
                f.write("\n")
            
            f.write("="*80 + "\n\n")
            
            # リポジトリ別詳細
            f.write("【リポジトリ別詳細】\n\n")
            for i, result in enumerate(results, 1):
                f.write(f"{i}. ")
                self.write_result(f, result)
        
        print(f"\n最終結果を保存しました: {output_path}")
        
        # JSON形式でも保存
        json_path = os.path.join(self.output_dir, "dataset_AI.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"JSON形式でも保存しました: {json_path}")
    
    def write_result(self, f, result):
        """結果を1件書き込む"""
        f.write(f"リポジトリ: {result['repo']}\n")
        f.write(f"  スター数: {result['stars']:,}\n")
        f.write(f"  総コミット数: {result['total_commits']:,}\n")
        f.write(f"  AIコミット: {result['ai_commits']:,} ({result['ai_ratio']*100:.2f}%)\n")
        f.write(f"  Humanコミット: {result['human_commits']:,}\n")
        
        if result['ai_tools']:
            f.write(f"  使用AIツール:\n")
            sorted_tools = sorted(result['ai_tools'].items(), key=lambda x: x[1], reverse=True)
            for tool, count in sorted_tools:
                f.write(f"    - {tool}: {count}件\n")
        
        f.write("\n")


def main():
    """メイン処理"""
    # GitHub tokenを取得
    github_token = os.getenv('GITHUB_TOKEN')
    
    if not github_token:
        print("エラー: GITHUB_TOKENが設定されていません")
        print("src/.envファイルにGITHUB_TOKEN=your_token_hereを設定してください")
        return
    
    # 分析実行
    analyzer = OldCommitAnalyzer(github_token)
    results = analyzer.analyze_top_100_repos()
    
    print("\n" + "="*80)
    print("全ての分析が完了しました！")
    print("="*80)


if __name__ == "__main__":
    main()
