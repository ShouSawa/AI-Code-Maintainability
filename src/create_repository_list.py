"""
リポジトリ一覧作成プログラム
dataset/repository.parquetからリポジトリ情報を読み込み、
スター数順にソートしてCSVファイルに出力
"""

import pandas as pd
import os

def create_repository_list():
    """リポジトリ一覧をCSVで出力"""
    
    # パス設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
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
            print(f"最大: {df_output[star_column].max()}")
            print(f"最小: {df_output[star_column].min()}")
            print(f"平均: {df_output[star_column].mean():.2f}")
            print(f"中央値: {df_output[star_column].median():.2f}")
        
    except FileNotFoundError:
        print(f"エラー: ファイルが見つかりません - {parquet_file}")
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    create_repository_list()
