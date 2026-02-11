"""
Step3: コミット履歴取得
機能: step2で選択されたファイルの全コミット履歴を取得してCSVに保存
"""

import os
import pandas as pd
from datetime import datetime
from github import Github
from dotenv import load_dotenv
from tqdm import tqdm
import time

# componentsフォルダからインポート
from components.AI_check import ai_check
from components.check_network import retry_with_network_check

# .envファイルを読み込む
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path)


class CommitHistoryCollector:
    def __init__(self, repo_name_full, github_token):
        """
        Args:
            repo_name_full: 'owner/repo' 形式のリポジトリ名
            github_token: GitHub Personal Access Token
        """
        self.repo_name_full = repo_name_full
        self.github_token = github_token
        
        # GitHub API初期化
        self.g = Github(self.github_token)
        self.repo = self.g.get_repo(repo_name_full)

    @retry_with_network_check
    def get_file_commits(self, file_path):
        """特定ファイルのコミット履歴取得（2025/10/31まで）
        
        Args:
            file_path: ファイルパス
            
        Returns:
            list: コミット情報のリスト
        """
        try:
            # 2025/10/31までのコミットを取得
            until_date = datetime(2025, 10, 31, 23, 59, 59)
            commits = self.repo.get_commits(path=file_path, until=until_date)
            commit_logs = []
            
            for commit in commits:
                author_name = commit.commit.author.name or "Unknown"
                
                # コミットアカウント取得（author + committer）
                all_authors = [author_name]
                
                # committerも追加（authorと異なる場合）
                if commit.commit.committer and commit.commit.committer.name:
                    committer_name = commit.commit.committer.name
                    if committer_name != author_name and committer_name not in all_authors:
                        all_authors.append(committer_name)
                
                commit_logs.append({
                    'commit_hash': commit.sha,
                    'commit_date': commit.commit.author.date.isoformat(),
                    'author_name': author_name,
                    'all_authors': ', '.join(all_authors),
                    'author_email': commit.commit.author.email or "unknown@example.com",
                    'commit_message': commit.commit.message
                })
                
                time.sleep(0.05)  # API rate limit対策
            
            return commit_logs
            
        except Exception as e:
            print(f"  ファイル履歴取得エラー {file_path}: {e}")
            return []


def process_repository_files(repo_name, file_list, github_token):
    """単一リポジトリの全ファイルのコミット履歴を取得
    
    Args:
        repo_name: リポジトリ名
        file_list: ファイル情報のリスト
        github_token: GitHub token
        
    Returns:
        list: コミット履歴のリスト
    """
    try:
        collector = CommitHistoryCollector(repo_name, github_token)
        all_commits = []
        
        for file_info in tqdm(file_list, desc=f"  {repo_name.split('/')[-1]}", leave=False):
            file_path = file_info['file_path']
            original_author_type = file_info['author_type']
            original_commit_hash = file_info['commit_hash']
            
            # コミット履歴取得
            commit_logs = collector.get_file_commits(file_path)
            
            if commit_logs:
                for log in commit_logs:
                    # AI判定
                    is_ai, ai_type = ai_check(log['all_authors'].split(', '))
                    
                    all_commits.append({
                        'repository_name': repo_name,
                        'file_path': file_path,
                        'original_author_type': original_author_type,
                        'original_commit_hash': original_commit_hash,
                        'commit_hash': log['commit_hash'],
                        'commit_date': log['commit_date'],
                        'author_name': log['author_name'],
                        'all_authors': log['all_authors'],
                        'author_email': log['author_email'],
                        'is_ai_generated': is_ai,
                        'ai_type': ai_type,
                        'commit_message': log['commit_message']
                    })
        
        return all_commits
        
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
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.join(script_dir, "../results/EASE-results/csv/step2_selected_files.csv")
    output_csv = os.path.join(script_dir, "../results/EASE-results/csv/step3_all_commits.csv")
    
    print("=" * 80)
    print("Step3: コミット履歴取得")
    print("=" * 80)
    print(f"入力: {input_csv}")
    print(f"出力: {output_csv}")
    print(f"取得期間: ～ 2025/10/31")
    print("=" * 80)
    
    # step2の結果を読み込み
    if not os.path.exists(input_csv):
        print(f"\nエラー: {input_csv} が見つかりません")
        print("先にstep2_choose_files.pyを実行してください")
        return
    
    df = pd.read_csv(input_csv)
    print(f"\n読み込み: {len(df)}件のファイル")
    print(f"リポジトリ数: {df['repository_name'].nunique()}件")
    
    # 処理開始
    start_time = datetime.now()
    all_commits = []
    
    # リポジトリごとに処理
    for repo_name in df['repository_name'].unique():
        print(f"\n{repo_name}")
        repo_files = df[df['repository_name'] == repo_name].to_dict('records')
        commits = process_repository_files(repo_name, repo_files, github_token)
        all_commits.extend(commits)
    
    # CSV保存
    if all_commits:
        commits_df = pd.DataFrame(all_commits)
        commits_df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        
        print(f"\n✓ 保存完了: {len(commits_df)}件のコミット")
        print(f"  ファイル数: {commits_df['file_path'].nunique()}件")
        print(f"  リポジトリ数: {commits_df['repository_name'].nunique()}件")
        print(f"  AI作成（original）: {len(commits_df[commits_df['original_author_type']=='AI'])}件")
        print(f"  人間作成（original）: {len(commits_df[commits_df['original_author_type']=='Human'])}件")
        print(f"  AI判定: {len(commits_df[commits_df['is_ai_generated']==True])}件")
    else:
        print("\n✗ コミットが見つかりませんでした")
    
    # 処理時間表示
    elapsed_time = datetime.now() - start_time
    print(f"\n総処理時間: {elapsed_time}")
    print("=" * 80)


if __name__ == "__main__":
    main()
