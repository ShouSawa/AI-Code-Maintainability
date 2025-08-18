import pandas as pd

def check_parquet(df):

    # merged_at が null でないPRだけ
    merged_prs = df[df["merged_at"].notnull()]

    # データ確認
    print("PRデータ件数:", len(df))
    print(df.head())

    print("マージされたPR数:", len(merged_prs))
    # 修正したカラム名で表示
    print(merged_prs[["id", "title", "agent", "merged_at"]].head())

    # AIエージェントごとの件数
    print(df["agent"].value_counts())

if __name__ == '__main__':
    # all_pull_request の読み込み（ローカルパス）
    df = pd.read_parquet("./all_pull_request_local.parquet")

    check_parquet(df)

