import pandas as pd
all_repo_df = pd.read_parquet("hf://datasets/hao-li/AIDev/all_repository.parquet")
all_pr_df = pd.read_parquet("hf://datasets/hao-li/AIDev/all_pull_request.parquet")

# リポジトリ直下にparquetを保存
all_repo_df.to_parquet("all_repository_local.parquet")
all_pr_df.to_parquet("all_pull_request_local.parquet")

