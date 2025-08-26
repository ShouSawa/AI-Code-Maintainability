import pandas as pd

# # リポジトリデータを取得
# all_repo_df = pd.read_parquet("hf://datasets/hao-li/AIDev/all_repository.parquet")
# all_repo_df.to_parquet("../data_list/all_repository_local.parquet")

# # PRデータを取得
# all_pr_df = pd.read_parquet("hf://datasets/hao-li/AIDev/all_pull_request.parquet")
# all_pr_df.to_parquet("../data_list/all_pull_request_local.parquet")

# コミットデータを取得
# pr_commits_df = pd.read_parquet("hf://datasets/hao-li/AIDev/pr_commits.parquet")
# pr_commits_df.to_parquet("../data_list/pr_commits_local.parquet")

# コミットのデータを取得
pr_commit_details_df = pd.read_parquet("hf://datasets/hao-li/AIDev/pr_commit_details.parquet")
pr_commit_details_df.to_parquet("../data_list/pr_commit_details_local.parquet")