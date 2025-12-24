import pandas as pd
import os

def check_median():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "../results/results_v5.csv")
    
    print(f"Reading {csv_path}")
    df = pd.read_csv(csv_path)
    
    # Date conversion
    df['commit_date'] = pd.to_datetime(df['commit_date']).dt.tz_localize(None)
    df['file_creation_date'] = pd.to_datetime(df['file_creation_date']).dt.tz_localize(None)
    
    # Exclude creation commits
    df = df[df['commit_date'] != df['file_creation_date']].copy()
    
    # Calculate days diff and month num
    df['days_diff'] = (df['commit_date'] - df['file_creation_date']).dt.days
    df['month_num'] = df['days_diff'] // 30
    
    # Filter for Month 1 (month_num = 0)
    df_m1 = df[df['month_num'] == 0]
    
    # Group by repository and creator
    # Note: We need to include repositories that have AI files but NO commits in Month 1 as 0.
    # To do this properly, we need the list of all files.
    
    # All files list
    all_files_df = pd.read_csv(csv_path) # Read again to get all files including creation
    all_files_df['commit_date'] = pd.to_datetime(all_files_df['commit_date']).dt.tz_localize(None)
    all_files_df = all_files_df.sort_values('commit_date', ascending=False).groupby(['repository_name', 'file_name']).first().reset_index()
    all_files_df = all_files_df[['repository_name', 'file_name', 'file_created_by']]
    
    # Identify repositories that have AI files
    ai_repos = all_files_df[all_files_df['file_created_by'] == 'AI']['repository_name'].unique()
    print(f"Number of repositories with AI files: {len(ai_repos)}")
    
    # Calculate commits per repo for AI files in Month 1
    # 1. Filter commits for AI files in Month 1
    ai_commits_m1 = df_m1[df_m1['file_created_by'] == 'AI']
    
    # 2. Count commits per repo
    repo_counts = ai_commits_m1.groupby('repository_name').size()
    
    # 3. Reindex to include all AI repos (fill with 0)
    repo_counts = repo_counts.reindex(ai_repos, fill_value=0)
    
    print("Counts for AI repos in Month 1:")
    print(repo_counts.value_counts().sort_index())
    
    median = repo_counts.median()
    print(f"Median commits per repository for AI files in Month 1: {median}")
    
    # Check Human
    human_repos = all_files_df[all_files_df['file_created_by'] == 'Human']['repository_name'].unique()
    human_commits_m1 = df_m1[df_m1['file_created_by'] == 'Human']
    repo_counts_h = human_commits_m1.groupby('repository_name').size()
    repo_counts_h = repo_counts_h.reindex(human_repos, fill_value=0)
    print(f"Median commits per repository for Human files in Month 1: {repo_counts_h.median()}")

if __name__ == "__main__":
    check_median()
