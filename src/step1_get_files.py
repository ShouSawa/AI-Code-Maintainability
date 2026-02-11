"""
Step1: ファイル追加情報取得
機能: repository_list.csvから各リポジトリの2025/1/1～2025/7/31に追加されたファイルを取得してCSVに保存
"""

import os
import pandas as pd
from datetime import datetime
from github import Github
from dotenv import load_dotenv
from tqdm import tqdm
import time

# componentsフォルダからインポート
from components.check_network import retry_with_network_check

# .envファイルを読み込む
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path)


class FileAdditionCollector:
    def __init__(self, repo_name_full, github_token):
        """
        Args:
            repo_name_full: 'owner/repo' 形式のリポジトリ名
            github_token: GitHub Personal Access Token
        """
        self.repo_name_full = repo_name_full
        self.repo_name = repo_name_full.split('/')[-1]
        self.github_token = github_token
        
        # GitHub API初期化
        self.g = Github(self.github_token)
        self.repo = self.g.get_repo(repo_name_full)
        
        print(f"リポジトリ接続: {repo_name_full}")

    @retry_with_network_check
    def get_all_commits_with_file_additions(self):
        """2025/1/1～2025/7/31の全コミットを取得（ファイル追加のみ）
        
        Returns:
            list: コミット情報のリスト
        """
        print(f"  コミット取得中...")
        commits_data = []
        
        try:
            # 2025/1/1～2025/12/31の期間のコミットを取得
            since_date = datetime(2025, 1, 1)
            until_date = datetime(2025, 12, 31)
            
            commits = self.repo.get_commits(since=since_date, until=until_date)
            commits_list = list(commits)
            
            # 全コミットを処理
            for commit in tqdm(commits_list, desc=f"  {self.repo_name}", leave=False):
                try:
                    # コミット情報取得
                    commit_sha = commit.sha
                    author_name = commit.commit.author.name or "Unknown"
                    author_email = commit.commit.author.email or "unknown@example.com"
                    commit_date = commit.commit.author.date.isoformat()
                    message = commit.commit.message
                    
                    # コミットアカウント取得（author + committer）
                    all_authors = [author_name]
                    
                    # committerも追加（authorと異なる場合）
                    if commit.commit.committer and commit.commit.committer.name:
                        committer_name = commit.commit.committer.name
                        if committer_name != author_name and committer_name not in all_authors:
                            all_authors.append(committer_name)
                    
                    # 追加されたファイルを検索
                    added_files = []
                    for file in commit.files:
                        if file.status == 'added':
                            added_files.append(file.filename)
                    
                    if added_files:
                        commit_info = {
                            'repository_name': self.repo_name_full,
                            'commit_hash': commit_sha,
                            'commit_date': commit_date,
                            'author_name': author_name,
                            'author_email': author_email,
                            'all_authors': ', '.join(all_authors),
                            'commit_message': message,
                            'added_files': added_files
                        }
                        commits_data.append(commit_info)
                    
                    # API rate limit対策
                    time.sleep(0.05)
                    
                except Exception as e:
                    print(f"\n  コミット処理エラー {commit.sha[:8]}: {e}")
                    continue
            
            return commits_data
            
        except Exception as e:
            print(f"  GitHub API エラー: {e}")
            return []


def process_repository(repo_info, github_token):
    """単一リポジトリの処理
    
    Args:
        repo_info: リポジトリ情報の辞書
        github_token: GitHub token
        
    Returns:
        list: ファイル追加情報のリスト
    """
    repo_name_full = f"{repo_info['owner']}/{repo_info['repository_name']}"
    
    try:
        collector = FileAdditionCollector(repo_name_full, github_token)
        commits_data = collector.get_all_commits_with_file_additions()
        
        # DataFrameに変換
        all_file_records = []
        for commit in commits_data:
            for file_path in commit['added_files']:
                all_file_records.append({
                    'repository_name': commit['repository_name'],
                    'file_path': file_path,
                    'commit_hash': commit['commit_hash'],
                    'commit_date': commit['commit_date'],
                    'author_name': commit['author_name'],
                    'author_email': commit['author_email'],
                    'all_authors': commit['all_authors'],
                    'commit_message': commit['commit_message']
                })
        
        return all_file_records
        
    except Exception as e:
        print(f"  エラー: {e}")
        return []


def main():
    """メイン実行"""
    # GitHub token取得
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("エラー: GitHub tokenが設定されていません")
        return
    
    # CSVからリポジトリリスト読み込み
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.join(script_dir, "../dataset/repository_list.csv")
    output_csv = os.path.join(script_dir, "../results/EASE-results/csv/step1_all_files.csv")
    
    # 出力ディレクトリ作成
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    
    print("=" * 80)
    print("Step1: ファイル追加情報取得")
    print("=" * 80)
    print(f"入力: {input_csv}")
    print(f"出力: {output_csv}")
    print(f"期間: 2025/1/1 ～ 2025/7/31")
    print("=" * 80)
    
    # リポジトリリスト読み込み
    repo_df = pd.read_csv(input_csv)
    repo_list = repo_df.to_dict('records')
    
    print(f"\n総リポジトリ数: {len(repo_list)}件")
    
    # 処理開始
    start_time = datetime.now()
    all_files = []
    
    for idx, repo_info in enumerate(repo_list, 1):
        print(f"\n[{idx}/{len(repo_list)}] {repo_info['owner']}/{repo_info['repository_name']}")
        file_records = process_repository(repo_info, github_token)
        all_files.extend(file_records)
    
    # CSV保存
    if all_files:
        df = pd.DataFrame(all_files)
        df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        print(f"\n✓ 保存完了: {len(df)}件のファイル")
    else:
        print("\n✗ ファイルが見つかりませんでした")
    
    # 処理時間表示
    elapsed_time = datetime.now() - start_time
    print(f"\n総処理時間: {elapsed_time}")
    print("=" * 80)


if __name__ == "__main__":
    main()
