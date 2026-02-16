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
<<<<<<< HEAD
=======
from components.prepere_csv import prepere_csv
>>>>>>> 01feb99 (first commit)

# .envファイルを読み込む
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path)


class FileAdditionCollector:
<<<<<<< HEAD
=======
    @retry_with_network_check
>>>>>>> 01feb99 (first commit)
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
<<<<<<< HEAD
            # 2025/1/1～2025/12/31の期間のコミットを取得
            since_date = datetime(2025, 1, 1)
            until_date = datetime(2025, 12, 31)
=======
            since_date = datetime(2025, 1, 1)
            until_date = datetime(2025, 7, 31)
>>>>>>> 01feb99 (first commit)
            
            commits = tqdm(self.repo.get_commits(since=since_date, until=until_date))
            commits_list = list(commits)
            
            # 全コミットを処理
            for commit in tqdm(commits_list, desc=f"  {self.repo_name}", leave=False):
                try:
                    # コミット情報取得
                    commit_sha = commit.sha
                    author_name = commit.commit.author.name or "Unknown"
                    author_email = commit.commit.author.email or "unknown@example.com"
                    commit_date = commit.commit.author.date.isoformat()
<<<<<<< HEAD
                    message = commit.commit.message
=======
                    message = commit.commit.message.replace('\n', ' ').replace('\r', '').replace('\u2028', ' ').replace('\u2029', ' ')
>>>>>>> 01feb99 (first commit)
                    
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

<<<<<<< HEAD

=======
@retry_with_network_check
>>>>>>> 01feb99 (first commit)
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
    
<<<<<<< HEAD
    print("=" * 80)
    print("Step1: ファイル追加情報取得")
    print("=" * 80)
    print(f"入力: {input_csv}")
    print(f"出力: {output_csv}")
    print(f"期間: 2025/1/1 ～ 2025/12/31")
    print("=" * 80)
    
=======
>>>>>>> 01feb99 (first commit)
    # リポジトリリスト読み込み
    repo_df = pd.read_csv(input_csv)
    repo_list = repo_df.to_dict('records')
    
<<<<<<< HEAD
=======
    # 処理を開始するリポジトリを設定
    start_repo = "neondatabase/neon"  # 空白の場合は最初から処理
    
    # start_repoが指定されている場合、そのリポジトリ以降のみを処理
    if start_repo and start_repo.strip():
        prepere_csv(1, start_repo)  # step1_all_files.csvから該当リポジトリを削除
        
        # start_repoのインデックスを探す
        start_index = 0
        for idx, repo_info in enumerate(repo_list):
            repo_full_name = f"{repo_info['owner']}/{repo_info['repository_name']}"
            if repo_full_name == start_repo:
                start_index = idx
                print(f"開始リポジトリ: {start_repo} (インデックス: {start_index + 1}/{len(repo_list)})")
                break
        else:
            print(f"警告: 開始リポジトリ '{start_repo}' が見つかりません。最初から処理を開始します。")
            start_index = 0
        
        # start_repo以降のリポジトリのみに絞り込む
        repo_list = repo_list[start_index:]
    
>>>>>>> 01feb99 (first commit)
    print(f"\n総リポジトリ数: {len(repo_list)}件")
    
    # 処理開始
    start_time = datetime.now()
    all_files = []
    
<<<<<<< HEAD
    for idx, repo_info in enumerate(repo_list, 1):
        print(f"\n[{idx}/{len(repo_list)}] {repo_info['owner']}/{repo_info['repository_name']}")
=======
    # CSVが既に存在するかチェック（追記モードの判定用）
    csv_exists = os.path.exists(output_csv)
    
    for idx, repo_info in enumerate(repo_list, 1):
        repo_full_name = f"{repo_info['owner']}/{repo_info['repository_name']}"
        print(f"\n[{idx}/{len(repo_list)}] {repo_full_name}")
>>>>>>> 01feb99 (first commit)
        file_records = process_repository(repo_info, github_token)
        all_files.extend(file_records)
        
        # 1リポジトリごとにCSVに追記保存
        if file_records:
            df_temp = pd.DataFrame(file_records)
<<<<<<< HEAD
            if idx == 1:  # 初回は新規作成
                df_temp.to_csv(output_csv, index=False, encoding='utf-8-sig', mode='w')
            else:  # 2回目以降は追記
=======
            if not csv_exists and idx == 1:  # CSVが存在せず、かつ初回の場合は新規作成
                df_temp.to_csv(output_csv, index=False, encoding='utf-8-sig', mode='w')
                csv_exists = True
            else:  # それ以外は追記
>>>>>>> 01feb99 (first commit)
                df_temp.to_csv(output_csv, index=False, encoding='utf-8-sig', mode='a', header=False)
            print(f"  → CSV更新: {len(file_records)}件追加 (累計: {len(all_files)}件)")
    
    # 最終結果表示
    if all_files:
        print(f"\n✓ 保存完了: {len(all_files)}件のファイル")
        print(f"出力先: {output_csv}")
    else:
        print("\n✗ ファイルが見つかりませんでした")
    
    # 処理時間表示
    elapsed_time = datetime.now() - start_time
    print(f"\n総処理時間: {elapsed_time}")
    print("=" * 80)


if __name__ == "__main__":
    main()
