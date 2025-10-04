import pandas as pd
import os

def get_PR_number(df):
    """
    Metta-AI/mettaリポジトリのPRナンバーを取得する関数
    """
    # repo_urlでMetta-AI/mettaリポジトリのPRのみをフィルタリング
    if 'repo_url' in df.columns:
        metta_df = df[df['repo_url'] == 'https://api.github.com/repos/Metta-AI/metta']
        print(f"Filtered to Metta-AI/metta repository: {len(metta_df)} PRs")
    else:
        print("Error: 'repo_url' column not found in DataFrame")
        print("Available columns:", df.columns.tolist())
        return []
    
    if 'number' in metta_df.columns:
        pr_numbers = metta_df['number'].tolist()
        print(f"Found {len(pr_numbers)} Metta-AI/metta PR numbers:")
        for pr_num in pr_numbers:
            print(f"PR #{pr_num}")
        
        # CSV出力用のDataFrameを作成
        output_df = pd.DataFrame({'PR_number': pr_numbers})
        
        # 出力ディレクトリの作成
        output_dir = "../data_list/RQ1"
        os.makedirs(output_dir, exist_ok=True)
        
        # CSVファイルに保存
        output_path = os.path.join(output_dir, "metta_ai_PR_numbers.csv")
        output_df.to_csv(output_path, index=False)
        print(f"PR numbers saved to: {output_path}")
        
        return pr_numbers
    else:
        print("Error: 'number' column not found in DataFrame")
        print("Available columns:", metta_df.columns.tolist())
        return []

if __name__ == '__main__':
    df = pd.read_parquet("../data_list/all_pull_request_local.parquet")
    
    # DataFrameの構造を確認
    print("DataFrame columns:", df.columns.tolist())
    print("DataFrame shape:", df.shape)
    
    get_PR_number(df)

