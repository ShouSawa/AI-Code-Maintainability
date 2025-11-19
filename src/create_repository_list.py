"""
リポジトリ一覧作成プログラム
dataset/repository.parquetからリポジトリ情報を読み込み、
スター数順にソートしてCSVファイルに出力
各リポジトリのコミット数も取得して表示
"""

import pandas as pd
import os
from github import Github
from dotenv import load_dotenv
import time

import time

# srcフォルダ内の.envファイルを読み込む
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path)


def get_commit_count(repo_full_name, github_token):
    """
    GitHubリポジトリのコミット数を取得
    
    Args:
        repo_full_name: リポジトリのフルネーム (owner/repo)
        github_token: GitHub API トークン
        
    Returns:
        int: コミット数、取得失敗時は-1
    """
    try:
        g = Github(github_token)
        repo = g.get_repo(repo_full_name)
        
        # デフォルトブランチのコミット数を取得
        commits = repo.get_commits()
        commit_count = commits.totalCount
        
        return commit_count
    except Exception as e:
        print(f"  エラー ({repo_full_name}): {e}")
        return -1


def create_repository_list():
    """リポジトリ一覧をCSVで出力"""
    
    # GitHub token取得
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("警告: GITHUB_TOKENが設定されていません。コミット数は取得されません。")
        print("src/.envファイルにGITHUB_TOKEN=your_token_hereを設定してください")
    
    # パス設定
    parquet_file = os.path.join(script_dir, "../dataset/repository.parquet")
    output_csv = os.path.join(script_dir, "../dataset/repository_list.csv")
    
    print("=== リポジトリ一覧作成 ===")
    print(f"入力: {parquet_file}")
    
    try:
        # Parquetファイル読み込み
        df = pd.read_parquet(parquet_file)
        print(f"読み込み完了: {len(df)}件のリポジトリ")
        
        # カラム確認
        print(f"カラム: {list(df.columns)}")
        
        # 必要な情報を抽出
        # owner と name から URL を生成
        if 'owner' in df.columns and 'name' in df.columns:
            df['url'] = df.apply(lambda row: f"https://github.com/{row['owner']}/{row['name']}", axis=1)
            df['full_name'] = df['owner'] + '/' + df['name']
        elif 'full_name' in df.columns:
            # full_name が既にある場合
            df['owner'] = df['full_name'].str.split('/').str[0]
            df['repository_name'] = df['full_name'].str.split('/').str[1]
            df['url'] = 'https://github.com/' + df['full_name']
        else:
            print("エラー: owner/name または full_name カラムが見つかりません")
            return
        
        # スター数でソート（降順）
        if 'stars' in df.columns:
            df_sorted = df.sort_values('stars', ascending=False)
            star_column = 'stars'
        elif 'stargazers_count' in df.columns:
            df_sorted = df.sort_values('stargazers_count', ascending=False)
            star_column = 'stargazers_count'
        else:
            print("警告: スター数カラムが見つかりません。ソートなしで出力します")
            df_sorted = df
            star_column = None
        
        # 出力用データフレーム作成
        output_columns = ['owner', 'repository_name', 'url']
        if star_column:
            output_columns.append(star_column)
        
        # カラム名調整
        if 'name' in df_sorted.columns and 'repository_name' not in df_sorted.columns:
            df_sorted['repository_name'] = df_sorted['name']
        
        # 存在するカラムのみ選択
        available_columns = [col for col in output_columns if col in df_sorted.columns]
        df_output = df_sorted[available_columns].copy()
        
        # コミット数を取得
        if github_token:
            print(f"\n=== コミット数取得中 ===")
            commit_counts = []
            
            for idx, row in df_output.iterrows():
                repo_full_name = f"{row['owner']}/{row['repository_name']}"
                print(f"[{idx+1}/{len(df_output)}] {repo_full_name}...", end=' ')
                
                commit_count = get_commit_count(repo_full_name, github_token)
                commit_counts.append(commit_count)
                
                if commit_count >= 0:
                    print(f"{commit_count:,} commits")
                else:
                    print("取得失敗")
                
                # API rate limit対策
                time.sleep(0.5)
            
            df_output['commit_count'] = commit_counts
            print(f"✓ コミット数取得完了")
        else:
            print("\n✗ GitHub token未設定のためコミット数は取得されませんでした")
        
        # CSV出力
        df_output.to_csv(output_csv, index=False, encoding='utf-8')
        
        print(f"\n=== 出力完了 ===")
        print(f"出力先: {output_csv}")
        print(f"総件数: {len(df_output)}件")
        
        # 上位10件表示
        print(f"\n=== 上位10件 ===")
        print(df_output.head(10).to_string(index=False))
        
        # 統計情報
        if star_column:
            print(f"\n=== スター数統計 ===")
            print(f"最大: {df_output[star_column].max():,}")
            print(f"最小: {df_output[star_column].min():,}")
            print(f"平均: {df_output[star_column].mean():.2f}")
            print(f"中央値: {df_output[star_column].median():.2f}")
        
        # コミット数統計
        if 'commit_count' in df_output.columns:
            valid_commits = df_output[df_output['commit_count'] >= 0]['commit_count']
            if len(valid_commits) > 0:
                print(f"\n=== コミット数統計 ===")
                print(f"最大: {valid_commits.max():,}")
                print(f"最小: {valid_commits.min():,}")
                print(f"平均: {valid_commits.mean():.2f}")
                print(f"中央値: {valid_commits.median():.2f}")
                print(f"取得成功: {len(valid_commits)}/{len(df_output)}件")
        
    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません - {parquet_file}")
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    create_repository_list()
