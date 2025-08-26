import pandas as pd

def check_parquet(df):

    print("\n=== 列名一覧 ===")
    print(df.columns.tolist())

    # データ確認
    print("PRデータ件数:", len(df))

    # # mettaリポジトリのデータのみフィルタリング
    # if 'repo_url' in df.columns:
    #     target_url = 'https://api.github.com/repos/Metta-AI/metta'
    #     df_filtered = df[df['repo_url'] == target_url]
    #     print(f"フィルタ後データ件数: {len(df_filtered)}")
        
    #     print("\n=== 内容表示 ===")
    #     print(df_filtered)

    #     print(df_filtered[["id"]])
    # else:
    #     print("repo_url列が見つかりません。")
    #     print("\n=== 内容表示 ===")
    #     print(df)
    
    # print(df[["repo_url"]])
    # print(status_counts)
    # print("\n=== 内容表示 ===")
    # author_counts = df['author'].value_counts()
    # commiter_counts = df['committer'].value_counts()
    # print(author_counts)
    # print("\n=== 内容表示 ===")
    # print(commiter_counts)

if __name__ == '__main__':
    df = pd.read_parquet("../data_list/all_pull_request_local.parquet")
    # df = pd.read_parquet("../data_list/all_repository_local.parquet")
    # df = pd.read_parquet("../data_list/pr_commits_local.parquet")
    # df = pd.read_parquet("../data_list/pr_commit_details_local.parquet")


    check_parquet(df)

