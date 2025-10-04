import requests
import pandas as pd
import json
import time
from datetime import datetime
import re
import os

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
                'pr_number': pr_number,
                'sha': commit['sha'],
                'message': commit['commit']['message'],
                'author_name': commit['commit']['author']['name'],
                'author_email': commit['commit']['author']['email'],
                'author_date': commit['commit']['author']['date'],
                'committer_name': commit['commit']['committer']['name'],
                'committer_email': commit['commit']['committer']['email'],
                'committer_date': commit['commit']['committer']['date'],
                'url': commit['html_url']
            }
            commit_data.append(commit_info)
        
        return commit_data
    else:
        print(f"Error for PR {pr_number}: {response.status_code}")
        if response.status_code == 404:
            return []  # PR not found
        return None

def is_ai_commit(author_name, author_email):
    """
    authorがAIかどうかを判定
    """
    ai_indicators = [
        'github-actions', 'dependabot', 'renovate', 'greenkeeper',
        'codecov', 'stale', 'mergify', 'semantic-release',
        'bot', 'automated', 'copilot', 'assistant', 'ai-',
        'noreply@github.com', 'users.noreply.github.com'
    ]
    
    # 名前とメールアドレスをチェック
    text_to_check = f"{author_name} {author_email}".lower()
    
    for indicator in ai_indicators:
        if indicator in text_to_check:
            return True
    
    return False

def analyze_pr_commits(pr_numbers, owner='Metta-AI', repo='metta', token=None):
    """
    複数のPRのコミット情報を分析
    """
    all_commits = []
    pr_stats = {}
    
    for i, pr_number in enumerate(pr_numbers):
        print(f"Processing PR {pr_number} ({i+1}/{len(pr_numbers)})...")
        
        commits = get_pr_commits(owner, repo, pr_number, token)
        
        if commits is None:
            print(f"Failed to get commits for PR {pr_number}")
            continue
        elif len(commits) == 0:
            print(f"No commits found for PR {pr_number}")
            pr_stats[pr_number] = {
                'total_commits': 0,
                'human_commits': 0,
                'ai_commits': 0,
                'human_percentage': 0.0,
                'ai_percentage': 0.0
            }
            continue
        
        # 各コミットにAI判定を追加
        human_count = 0
        ai_count = 0
        
        for commit in commits:
            is_ai = is_ai_commit(
                commit['author_name'],
                commit['author_email']
            )
            commit['is_ai_commit'] = is_ai
            
            if is_ai:
                ai_count += 1
            else:
                human_count += 1
        
        # PR統計を計算
        total_commits = len(commits)
        pr_stats[pr_number] = {
            'total_commits': total_commits,
            'human_commits': human_count,
            'ai_commits': ai_count,
            'human_percentage': (human_count / total_commits) * 100 if total_commits > 0 else 0,
            'ai_percentage': (ai_count / total_commits) * 100 if total_commits > 0 else 0
        }
        
        all_commits.extend(commits)
        
        # API制限を避けるため少し待機
        time.sleep(0.1)
    
    return all_commits, pr_stats

def generate_report(pr_stats, output_path):
    """
    統計レポートをテキストファイルに出力
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=== Metta-AI PR Commit Analysis Report ===\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # 全体統計
        total_prs = len(pr_stats)
        total_commits = sum(stats['total_commits'] for stats in pr_stats.values())
        total_human_commits = sum(stats['human_commits'] for stats in pr_stats.values())
        total_ai_commits = sum(stats['ai_commits'] for stats in pr_stats.values())
        
        f.write("=== Overall Statistics ===\n")
        f.write(f"Total PRs analyzed: {total_prs}\n")
        f.write(f"Total commits: {total_commits}\n")
        if total_commits == 0:
            print("total commits が 0 です")
        else:
            f.write(f"Human commits: {total_human_commits} ({(total_human_commits/total_commits)*100:.1f}%)\n")
            f.write(f"AI commits: {total_ai_commits} ({(total_ai_commits/total_commits)*100:.1f}%)\n\n")
        
        # コミット頻度統計
        commit_counts = [stats['total_commits'] for stats in pr_stats.values() if stats['total_commits'] > 0]
        if commit_counts:
            avg_commits = sum(commit_counts) / len(commit_counts)
            max_commits = max(commit_counts)
            min_commits = min(commit_counts)
            
            f.write("=== Commit Frequency Statistics ===\n")
            f.write(f"Average commits per PR: {avg_commits:.2f}\n")
            f.write(f"Maximum commits in a PR: {max_commits}\n")
            f.write(f"Minimum commits in a PR: {min_commits}\n\n")
        
        # 各PR詳細
        f.write("=== Per-PR Analysis ===\n")
        for pr_number in sorted(pr_stats.keys()):
            stats = pr_stats[pr_number]
            f.write(f"PR #{pr_number}:\n")
            f.write(f"  Total commits: {stats['total_commits']}\n")
            f.write(f"  Human commits: {stats['human_commits']} ({stats['human_percentage']:.1f}%)\n")
            f.write(f"  AI commits: {stats['ai_commits']} ({stats['ai_percentage']:.1f}%)\n\n")

if __name__ == '__main__':
    # GitHub Personal Access Token
    TOKEN = None  # 必要に応じて設定
    
    # CSVファイルからPR番号を読み込み
    csv_path = '../data_list/RQ1/metta_ai_PR_numbers.csv'
    pr_df = pd.read_csv(csv_path)
    pr_numbers = pr_df['PR_number'].tolist()
    
    print(f"Found {len(pr_numbers)} PRs to analyze")
    
    # コミット情報を取得・分析
    all_commits, pr_stats = analyze_pr_commits(pr_numbers, token=TOKEN)
    
    # 統計レポートをテキストファイルに保存
    report_output = '../data_list/RQ1/pr_commit_analysis_report.txt'
    generate_report(pr_stats, report_output)
    print(f"Analysis report saved to: {report_output}")
    
    print(f"\nAnalysis completed:")
    print(f"- Total PRs processed: {len(pr_stats)}")
    print(f"- Total commits analyzed: {len(all_commits)}")