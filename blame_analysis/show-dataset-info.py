import pandas as pd

def check_parquet(df):

    print("\n=== 列名一覧 ===")
    print(df.columns.tolist())

    # データ確認
    print("PRデータ件数:", len(df))

    print("\n=== 内容表示 ===")
    print(df[["id","number","repo_url"]])

if __name__ == '__main__':
    # all_pull_request の読み込み（ローカルパス）
    df = pd.read_parquet("./all_pull_request_local.parquet")

    check_parquet(df)

