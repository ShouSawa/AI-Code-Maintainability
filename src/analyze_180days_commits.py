"""
90日以前のコミット分析プログラム
機能: repository_listから上位100個のリポジトリの90日以前のコミットを分析（上限なし）
"""

import os
import pandas as pd
from datetime import datetime, timedelta
import re
import time
from github import Github
from dotenv import load_dotenv
import json
import csv
import socket  # ネットワーク接続確認用

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


class OldCommitAnalyzer:
    """90日以前のコミットを分析するクラス"""
    
    # AIボットアカウント定義（作成者名で判定）
    AI_BOT_ACCOUNTS = {
        'copilot': ['copilot'],  # GitHub Copilot
        'cursor': ['cursor'],  # Cursor
        'devin': ['devin-ai-integration'],  # Devin
        'claude': ['claude']  # Claude
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
        
        # コミット情報を格納するリスト
        self.all_commits_data = []
        
    def is_ai_generated_commit(self, author_names):
        """
        コミットがAIによって生成されたかどうかを判定（作成者名のみで判定）
        
        Args:
            author_names: コミット作成者名（文字列またはリスト）
            
        Returns:
            tuple: (bool, str) - AIかどうか, AIの種類またはhuman
        """
        # 文字列の場合はリストに変換
        if isinstance(author_names, str):
            author_names = [author_names]
        
        # 各作成者名をチェック
        for author_name in author_names:
            author_lower = author_name.lower()
            
            # ボットアカウント名で判定
            for ai_type, bot_names in self.AI_BOT_ACCOUNTS.items():
                # bot_nameの中にauthor_lowerが含まれているかチェック
                if any(bot_name.lower() in author_lower for bot_name in bot_names):
                    return True, ai_type
        
        return False, "human"
    
    def detect_specific_ai_tool(self, author_names):
        """
        特定のAIツールを識別（作成者名のみで判定）
        
        Args:
            author_names: コミット作成者名（文字列またはリスト）
            
        Returns:
            str: AIツール名、または'N/A'
        """
        # 文字列の場合はリストに変換
        if isinstance(author_names, str):
            author_names = [author_names]
        
        # 各作成者名をチェック
        for author_name in author_names:
            author_lower = author_name.lower()
            
            # ボットアカウント名で特定のツールを識別
            for ai_type, bot_names in self.AI_BOT_ACCOUNTS.items():
                if any(bot_name.lower() in author_lower for bot_name in bot_names):
                    tool_map = {
                        'copilot': 'GitHub Copilot',
                        'cursor': 'Cursor',
                        'devin': 'Devin',
                        'claude': 'Claude'
                    }
                    return tool_map.get(ai_type, 'N/A')
        
        return 'N/A'
    
    def check_repo_has_old_commits(self, repo_full_name):
        """リポジトリに90日以前のコミットがあるかチェック"""
        try:
            repo = self.g.get_repo(repo_full_name)
            cutoff_date = datetime.now() - timedelta(days=90)
            
            # 90日以前のコミットを取得（1件でも取得できればOK）
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
    
    @retry_with_network_check
    @retry_with_network_check
    def analyze_repo_commits(self, repo_full_name):
        """リポジトリの90日以前のコミットを分析（上限なし）"""
        print(f"\n{'='*80}")
        print(f"分析中: {repo_full_name}")
        print(f"{'='*80}")
        
        try:
            repo = self.g.get_repo(repo_full_name)
            print(f"スター数: {repo.stargazers_count}, フォーク数: {repo.forks_count}")
            
            cutoff_date = datetime.now() - timedelta(days=90)
            print(f"対象期間: ~{cutoff_date.date()}")
            
            # 90日以前のコミットを全て取得（上限なし）
            commits = repo.get_commits(until=cutoff_date)
            
            ai_count = 0
            human_count = 0
            ai_tools = {}
            total_analyzed = 0
            
            for commit in commits:
                total_analyzed += 1
                if total_analyzed % 100 == 0:
                    print(f"  処理中: {total_analyzed}件...")
                
                try:
                    author_name = commit.commit.author.name or "Unknown"
                    author_email = commit.commit.author.email or "unknown@example.com"
                    message = commit.commit.message
                    commit_date = commit.commit.author.date
                    
                    # コミットアカウントのみ取得（author + committer）
                    all_authors = [author_name]
                    
                    # committerも追加（authorと異なる場合）
                    if commit.commit.committer and commit.commit.committer.name:
                        committer_name = commit.commit.committer.name
                        if committer_name != author_name and committer_name not in all_authors:
                            all_authors.append(committer_name)
                    
                    # AI判定（全作成者で判定）
                    is_ai = self.is_ai_generated_commit(all_authors)
                    ai_tool = self.detect_specific_ai_tool(all_authors)
                    
                    # RQ1_result_v2.csv形式でコミット情報を保存
                    commit_info = {
                        'repository_name': repo_full_name,
                        'file_name': '',  # 90日以前のコミットではファイル情報なし
                        'file_created_by': '',
                        'file_line_count': 0,
                        'file_creation_date': '',
                        'file_commit_count': 0,
                        'commit_message': message.replace('\n', ' ').replace('\r', ' ')[:200] if message else '',
                        'commit_created_by': 'AI' if is_ai else 'Human',
                        'commit_changed_lines': commit.stats.total if commit.stats else 0,
                        'commit_date': commit_date.isoformat()
                    }
                    self.all_commits_data.append(commit_info)
                    
                    if is_ai:
                        ai_count += 1
                        if ai_tool != 'N/A':
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
        print("90日以前のコミット分析開始")
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
            
            # 90日以前のコミットがあるかチェック
            has_old_commits = self.check_repo_has_old_commits(repo_full_name)
            
            if has_old_commits:
                print(f"  ✓ 90日以前のコミットあり - 分析開始")
                result = self.analyze_repo_commits(repo_full_name)
                
                if result:
                    results.append(result)
                    analyzed_count += 1
                    print(f"  ✓ 分析完了 ({analyzed_count}/100)")
                else:
                    print(f"  × 分析失敗 - スキップ")
                    skipped_count += 1
            else:
                print(f"  × 90日以前のコミットなし - スキップ")
                skipped_count += 1
            
            index += 1
            
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
        
        # CSVファイルを保存
        self.save_commits_csv()
        
        return results
    
    def save_final_results(self, results):
        """最終結果を保存"""
        output_path = os.path.join(self.output_dir, "dataset_AI_90days.txt")
        
        # 全体統計を事前計算
        total_commits = sum(r['total_commits'] for r in results)
        total_ai = sum(r['ai_commits'] for r in results)
        total_human = sum(r['human_commits'] for r in results)
        
        # AIツール統計を事前計算
        all_ai_tools = {}
        for result in results:
            for tool, count in result['ai_tools'].items():
                all_ai_tools[tool] = all_ai_tools.get(tool, 0) + count
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("90日以前のコミット分析 - 最終結果\n")
            f.write(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"分析リポジトリ数: {len(results)}\n")
            f.write("="*80 + "\n\n")
            
            # ★★★ 一番上にAI全体統計を表示 ★★★
            f.write("【AIコミット統計サマリー】\n")
            f.write(f"AIコミット総数: {total_ai:,}件\n")
            if all_ai_tools:
                f.write(f"\n各エージェント別コミット数:\n")
                sorted_tools = sorted(all_ai_tools.items(), key=lambda x: x[1], reverse=True)
                for tool, count in sorted_tools:
                    percentage = count / total_ai * 100 if total_ai > 0 else 0
                    f.write(f"  - {tool}: {count:,}件 ({percentage:.2f}%)\n")
            f.write("\n" + "="*80 + "\n\n")
            
            # 全体統計
            f.write("【全体統計】\n")
            f.write(f"総コミット数: {total_commits:,}\n")
            f.write(f"AIコミット数: {total_ai:,} ({total_ai/total_commits*100:.2f}%)\n")
            f.write(f"Humanコミット数: {total_human:,} ({total_human/total_commits*100:.2f}%)\n\n")
            
            # AIツール統計（詳細版）
            if all_ai_tools:
                f.write("【使用AIツール統計（詳細）】\n")
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
        json_path = os.path.join(self.output_dir, "dataset_AI_90days.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"JSON形式でも保存しました: {json_path}")
    
    def save_commits_csv(self):
        """全コミット情報をRQ1_result_v2.csvに追記保存"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(script_dir, "../data_list/RQ1/final_result/RQ1_result_v2.csv")
        
        if not self.all_commits_data:
            print("CSVに保存するコミットデータがありません")
            return
        
        # 新しいデータをDataFrameに変換
        new_df = pd.DataFrame(self.all_commits_data)
        
        # 既存のCSVがあれば読み込んで結合
        if os.path.exists(csv_path):
            existing_df = pd.read_csv(csv_path)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            print(f"既存データに追加: {len(existing_df):,}件 → {len(combined_df):,}件")
        else:
            combined_df = new_df
            print(f"新規作成: {len(combined_df):,}件")
        
        # CSVに保存
        combined_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"✓ コミット情報をCSVに保存しました: {csv_path}")
        print(f"  今回追加: {len(new_df):,}件, 合計: {len(combined_df):,}件")
        
        # 統計情報も表示
        ai_commits = sum(1 for c in self.all_commits_data if c['commit_created_by'] == 'AI')
        human_commits = sum(1 for c in self.all_commits_data if c['commit_created_by'] == 'Human')
        print(f"  今回のAIコミット: {ai_commits:,}件")
        print(f"  今回のHumanコミット: {human_commits:,}件")
    
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
