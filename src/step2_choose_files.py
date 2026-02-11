"""
Step2: ファイル選択
機能: step1で取得した全ファイルからAI作成と人間作成を同数ランダムに選択
"""

import os
import pandas as pd
from datetime import datetime


def select_files(df, target_count_per_repo=10):
    """リポジトリごとにAI/人間ファイルを同数選択
    
    Args:
        df: step1の出力DataFrame
        target_count_per_repo: 各リポジトリでの目標選択数
        
    Returns:
        DataFrame: 選択されたファイル
    """
    selected_files = []
    
    # リポジトリごとに処理
    for repo_name in df['repository_name'].unique():
        repo_df = df[df['repository_name'] == repo_name].copy()
        
        # AI作成ファイルと人間作成ファイルを分離
        ai_df = repo_df[repo_df['author_type'] == 'AI'].copy()
        human_df = repo_df[repo_df['author_type'] == 'Human'].copy()
        
        ai_count = len(ai_df)
        human_count = len(human_df)
        
        print(f"\n{repo_name}:")
        print(f"  AI作成: {ai_count}件, 人間作成: {human_count}件")
        
        # AI作成ファイルが0件の場合はスキップ
        if ai_count == 0:
            print(f"  → スキップ（AI作成ファイルなし）")
            continue
        
        # AI作成ファイルをランダムに選択
        num_ai_files = min(target_count_per_repo, ai_count)
        if ai_count > num_ai_files:
            ai_sampled = ai_df.sample(n=num_ai_files, random_state=None)
            print(f"  AI: {ai_count}件から{num_ai_files}件をランダム選択")
        else:
            ai_sampled = ai_df
            print(f"  AI: 全{ai_count}件を使用")
        
        # 人間作成ファイルを同数ランダムに選択
        num_human_files = num_ai_files  # AI作成ファイルと同数
        if human_count >= num_human_files:
            human_sampled = human_df.sample(n=num_human_files, random_state=None)
            print(f"  人間: {human_count}件から{num_human_files}件をランダム選択")
        else:
            human_sampled = human_df
            print(f"  人間: 全{human_count}件を使用（不足）")
        
        # 同数に調整（小さい方に合わせる）
        min_count = min(len(ai_sampled), len(human_sampled))
        ai_sampled = ai_sampled.head(min_count)
        human_sampled = human_sampled.head(min_count)
        
        print(f"  → 最終選択: AI={min_count}件, 人間={min_count}件")
        
        # 結合
        repo_selected = pd.concat([ai_sampled, human_sampled], ignore_index=True)
        selected_files.append(repo_selected)
    
    if selected_files:
        return pd.concat(selected_files, ignore_index=True)
    else:
        return pd.DataFrame()


def main():
    """メイン実行"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.join(script_dir, "../results/EASE-results/csv/step1_all_files.csv")
    output_csv = os.path.join(script_dir, "../results/EASE-results/csv/step2_selected_files.csv")
    
    print("=" * 80)
    print("Step2: ファイル選択")
    print("=" * 80)
    print(f"入力: {input_csv}")
    print(f"出力: {output_csv}")
    print("=" * 80)
    
    # step1の結果を読み込み
    if not os.path.exists(input_csv):
        print(f"\nエラー: {input_csv} が見つかりません")
        print("先にstep1_get_files.pyを実行してください")
        return
    
    df = pd.read_csv(input_csv)
    print(f"\n読み込み: {len(df)}件のファイル")
    print(f"リポジトリ数: {df['repository_name'].nunique()}件")
    
    # ファイル選択
    start_time = datetime.now()
    selected_df = select_files(df, target_count_per_repo=10)
    
    # CSV保存
    if len(selected_df) > 0:
        selected_df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        
        ai_count = len(selected_df[selected_df['author_type'] == 'AI'])
        human_count = len(selected_df[selected_df['author_type'] == 'Human'])
        
        print(f"\n✓ 保存完了: {len(selected_df)}件のファイル")
        print(f"  AI作成: {ai_count}件")
        print(f"  人間作成: {human_count}件")
        print(f"  リポジトリ数: {selected_df['repository_name'].nunique()}件")
    else:
        print("\n✗ 選択されたファイルがありません")
    
    # 処理時間表示
    elapsed_time = datetime.now() - start_time
    print(f"\n総処理時間: {elapsed_time}")
    print("=" * 80)


if __name__ == "__main__":
    main()
