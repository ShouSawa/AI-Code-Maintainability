import pandas as pd
import os
import random
from datetime import datetime

def update_dataset():
    """
    results_v4.csvを読み込み、以下の処理を行ってresults_v6.csvとして保存する。
    1. ファイル作成日が2025/6/23以降のデータを除外（2025/6/22までを保持）
    2. リポジトリごとにAI作成ファイルと人間作成ファイルの数を同数にする（多い方からランダムに削除）
    3. results_v5.csvからfile_specific_changed_lines情報を取得して付与
    """
    
    # パス設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.join(script_dir, "../results/results_v4.csv")
    output_csv = os.path.join(script_dir, "../results/results_v6.csv")
    v5_csv = os.path.join(script_dir, "../results/results_v5.csv")
    
    if not os.path.exists(input_csv):
        print(f"エラー: {input_csv} が見つかりません。")
        return

    print(f"読み込み中: {input_csv}")
    df = pd.read_csv(input_csv)
    
    # 日付変換
    # タイムゾーン情報がある場合は削除して比較できるようにする
    df['file_creation_date'] = pd.to_datetime(df['file_creation_date']).dt.tz_localize(None)
    
    # 1. 日付フィルタリング (2025/6/22まで)
    filter_date = pd.to_datetime("2025-06-22")
    print(f"フィルタリング前: {len(df)} 行")
    df = df[df['file_creation_date'] <= filter_date].copy()
    print(f"日付フィルタリング後 (<= 2025-06-22): {len(df)} 行")
    
    # 2. リポジトリごとのファイル数バランス調整
    print("リポジトリごとのファイル数バランス調整を開始します...")
    
    # 全ファイルの一覧を取得 (repository_name, file_name, file_created_by)
    unique_files = df[['repository_name', 'file_name', 'file_created_by']].drop_duplicates()
    
    # 保持するファイルのリスト ( (repo_name, file_name) のタプル )
    files_to_keep = set()
    
    # リポジトリごとに処理
    repositories = unique_files['repository_name'].unique()
    
    for repo in repositories:
        repo_files = unique_files[unique_files['repository_name'] == repo]
        
        ai_files = repo_files[repo_files['file_created_by'] == 'AI']['file_name'].tolist()
        human_files = repo_files[repo_files['file_created_by'] == 'Human']['file_name'].tolist()
        
        count_ai = len(ai_files)
        count_human = len(human_files)
        
        target_count = min(count_ai, count_human)
        
        # ランダムに選択
        selected_ai = random.sample(ai_files, target_count)
        selected_human = random.sample(human_files, target_count)
        
        for f in selected_ai:
            files_to_keep.add((repo, f))
        for f in selected_human:
            files_to_keep.add((repo, f))
            
        # print(f"Repo: {repo}, AI: {count_ai}->{target_count}, Human: {count_human}->{target_count}")

    # データフレームをフィルタリング
    # 保持するファイルのDataFrameを作成
    keep_df = pd.DataFrame(list(files_to_keep), columns=['repository_name', 'file_name'])
    keep_df['keep'] = True
    
    # 元のデータフレームとマージ
    merged_df = pd.merge(df, keep_df, on=['repository_name', 'file_name'], how='left')
    
    # keepがTrueのものだけ残す
    final_df = merged_df[merged_df['keep'] == True].drop(columns=['keep'])
    
    print(f"バランス調整後: {len(final_df)} 行")

    # 3. results_v5.csv から file_specific_changed_lines を結合
    if os.path.exists(v5_csv):
        print(f"results_v5.csv から変更行数データを結合します: {v5_csv}")
        try:
            df_v5 = pd.read_csv(v5_csv)
            
            # 必要なカラムのみ抽出 (キー + 追加したいカラム)
            if 'file_specific_changed_lines' in df_v5.columns:
                # キーで重複がある場合は最初のものを採用（通常はユニークなはず）
                v5_subset = df_v5[['repository_name', 'commit_hash', 'file_name', 'file_specific_changed_lines']].drop_duplicates(subset=['repository_name', 'commit_hash', 'file_name'])
                
                # マージ
                final_df = pd.merge(final_df, v5_subset, on=['repository_name', 'commit_hash', 'file_name'], how='left')
                
                # マージされなかった(NaN)場合は -1 を入れる
                final_df['file_specific_changed_lines'] = final_df['file_specific_changed_lines'].fillna(-1)
                print("変更行数データの結合完了")
            else:
                print("警告: results_v5.csv に 'file_specific_changed_lines' カラムがありません。")
        except Exception as e:
            print(f"results_v5.csv の読み込みまたは結合中にエラーが発生しました: {e}")
    else:
        print("警告: results_v5.csv が見つかりません。変更行数は追加されません。")
    
    # 保存
    final_df.to_csv(output_csv, index=False)
    print(f"完了しました。結果を保存しました: {output_csv}")

if __name__ == "__main__":
    # ランダムシードを固定（再現性のため）
    random.seed(42)
    update_dataset()
