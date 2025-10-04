import pandas as pd
import os
from pathlib import Path

def extract_repo_info_from_parquet(parquet_file_path, output_csv_path, max_repos=500):
    """
    .parquetファイルからリポジトリ情報を抽出してCSVに出力
    
    Args:
        parquet_file_path (str): 入力.parquetファイルのパス
        output_csv_path (str): 出力CSVファイルのパス
        max_repos (int): 最大抽出数（デフォルト: 500）
    """
    try:
        # .parquetファイルを読み込み
        print(f"Loading parquet file: {parquet_file_path}")
        df = pd.read_parquet(parquet_file_path)
        
        print(f"Total records in parquet: {len(df)}")
        print("Columns available:", df.columns.tolist())
        
        # repo_urlからリポジトリ情報を抽出
        def extract_repo_info(repo_url):
            """
            repo_urlからowner/repo名を抽出
            例: "https://api.github.com/repos/microsoft/vscode" -> ("microsoft", "vscode")
            """
            if pd.isna(repo_url) or not isinstance(repo_url, str):
                return "Unknown", "Unknown"
            
            try:
                # GitHub API URLの形式: https://api.github.com/repos/owner/repo
                if "/repos/" in repo_url:
                    parts = repo_url.split("/repos/")[1].split("/")
                    if len(parts) >= 2:
                        return parts[0], parts[1]
                
                # 通常のGitHub URLの形式: https://github.com/owner/repo
                if "github.com/" in repo_url:
                    parts = repo_url.split("github.com/")[1].split("/")
                    if len(parts) >= 2:
                        return parts[0], parts[1]
                
                return "Unknown", "Unknown"
            except:
                return "Unknown", "Unknown"
        
        # リポジトリごとのPR数をカウント
        print("Extracting repository information from repo_url...")
        
        # repo_urlから所有者とリポジトリ名を抽出
        repo_info = df['repo_url'].apply(extract_repo_info)
        df['repository_owner'] = repo_info.apply(lambda x: x[0])
        df['repository_name'] = repo_info.apply(lambda x: x[1])
        df['full_name'] = df['repository_owner'] + '/' + df['repository_name']
        
        # Unknown を除外
        df_clean = df[
            (df['repository_owner'] != 'Unknown') & 
            (df['repository_name'] != 'Unknown')
        ].copy()
        
        print(f"Records after cleaning: {len(df_clean)}")
        
        # リポジトリごとのPR数を集計
        repo_stats = df_clean.groupby(['repository_owner', 'repository_name', 'full_name']).agg({
            'id': 'count',  # PR数をカウント
            'user': 'nunique'  # ユニークなコントリビューター数
        }).reset_index()
        
        # カラム名を変更
        repo_stats.columns = ['repository_owner', 'repository_name', 'full_name', 'pr_count', 'contributor_count']
        
        # PR数で降順ソート
        repo_stats = repo_stats.sort_values('pr_count', ascending=False)
        
        # 最大件数に制限
        repo_stats = repo_stats.head(max_repos)
        
        # CSVに保存
        os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
        repo_stats.to_csv(output_csv_path, index=False, encoding='utf-8')
        
        print(f"Successfully extracted {len(repo_stats)} repositories")
        print(f"Output saved to: {output_csv_path}")
        print("\nTop 10 repositories by PR count:")
        print(repo_stats.head(10).to_string(index=False))
        
        # 統計情報を表示
        print(f"\nStatistics:")
        print(f"Total PR count in dataset: {df_clean['id'].count()}")
        print(f"Average PRs per repo: {repo_stats['pr_count'].mean():.1f}")
        print(f"Max PRs in a repo: {repo_stats['pr_count'].max()}")
        print(f"Min PRs in a repo: {repo_stats['pr_count'].min()}")
        
        return repo_stats
        
    except Exception as e:
        print(f"Error processing file: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """メイン実行関数"""
    # ファイルパスの設定
    parquet_file = "../data_list/all_pull_request_local.parquet"
    output_csv = "../data_list/repo_info.csv"

    # .parquetファイルの存在確認
    if not os.path.exists(parquet_file):
        print(f"Error: Parquet file not found: {parquet_file}")
        print("Please specify the correct path to your .parquet file")
        return
    
    # 抽出実行
    extract_repo_info_from_parquet(
        parquet_file_path=parquet_file,
        output_csv_path=output_csv,
        max_repos=500
    )

if __name__ == "__main__":
    main()