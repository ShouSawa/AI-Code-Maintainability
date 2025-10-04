import requests
import pandas as pd
import json
from datetime import datetime

def get_pr_commits(owner, repo, pr_number, token=None):
    """
    指定されたPRのコミット情報を取得
    """
    headers = {}
    if token:
        headers['Authorization'] = f'token {token}'
    
    # PRのコミット一覧を取得
    url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/commits'
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        commits = response.json()
        
        # コミット情報を整理
        commit_data = []
        for commit in commits:
            commit_info = {
                'sha': commit['sha'],
                'message': commit['commit']['message'],
                'author_name': commit['commit']['author']['name'],
                'author_email': commit['commit']['author']['email'],
                'author_date': commit['commit']['author']['date'],
                'committer_name': commit['commit']['committer']['name'],
                'committer_email': commit['commit']['committer']['email'],
                'committer_date': commit['commit']['committer']['date'],
                'url': commit['html_url'],
                'additions': commit['stats']['additions'] if 'stats' in commit else None,
                'deletions': commit['stats']['deletions'] if 'stats' in commit else None,
                'total_changes': commit['stats']['total'] if 'stats' in commit else None
            }
            commit_data.append(commit_info)
        
        return commit_data
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

if __name__ == '__main__':
    # GitHub Personal Access Token (必要に応じて設定)
    # TOKEN = 'your_github_token_here'  # より多くのAPIリクエストが可能
    TOKEN = None  # 認証なしの場合
    
    # PR情報
    OWNER = 'Metta-AI'
    REPO = 'metta'
    PR_NUMBER = 1688
    
    print("PRのコミット情報を取得中...")
    commits = get_pr_commits(OWNER, REPO, PR_NUMBER, TOKEN)
    
    if commits:
        # コミット基本情報をCSVに保存
        df_commits = pd.DataFrame(commits)
        csv_filename = f'../data_list/RQ1/pr_{PR_NUMBER}_commits.csv'
        df_commits.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"コミット基本情報を {csv_filename} に保存しました")
        
        print(f"\n取得完了:")
        print(f"- コミット数: {len(commits)}")
    
    else:
        print("コミット情報の取得に失敗しました")