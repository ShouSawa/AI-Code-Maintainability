import pandas as pd
import os

def check_repository_balance():
    """
    results_v4.csvを読み込み、各リポジトリのAI作成ファイル数とHuman作成ファイル数をカウントし、
    バランスが取れていない（数が異なる）リポジトリを特定して表示する。
    """
    # パス設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "../data_list/RQ1/final_result/results_v4.csv")
    
    if not os.path.exists(csv_path):
        print(f"エラー: ファイルが見つかりません: {csv_path}")
        return

    print(f"読み込み中: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"CSV読み込みエラー: {e}")
        return

    # 必要なカラムの確認
    required_columns = ['repository_name', 'file_name', 'file_created_by']
    for col in required_columns:
        if col not in df.columns:
            print(f"エラー: 必要なカラム '{col}' がCSVに含まれていません。")
            print(f"存在するカラム: {df.columns.tolist()}")
            return

    # リポジトリごとに集計
    # ファイル単位でユニークにする（1つのファイルが複数のコミット行を持つため）
    # file_nameとfile_created_byの組み合わせでユニーク化
    unique_files = df[['repository_name', 'file_name', 'file_created_by']].drop_duplicates()

    # 集計
    # groupbyでリポジトリと作成者タイプごとにカウント
    repo_stats = unique_files.groupby(['repository_name', 'file_created_by']).size().unstack(fill_value=0)
    
    # カラムが存在しない場合の対応（AIのみ、Humanのみのリポジトリがある場合）
    if 'AI' not in repo_stats.columns:
        repo_stats['AI'] = 0
    if 'Human' not in repo_stats.columns:
        repo_stats['Human'] = 0

    # バランスチェック
    repo_stats['is_balanced'] = repo_stats['AI'] == repo_stats['Human']
    repo_stats['diff'] = repo_stats['AI'] - repo_stats['Human']

    # 結果表示
    print("\n" + "="*90)
    print(f"{'Repository Name':<45} | {'AI Files':<10} | {'Human Files':<12} | {'Diff':<5} | {'Status'}")
    print("-" * 90)

    unbalanced_count = 0
    # 全リポジトリを表示するのではなく、アンバランスなものだけを目立たせるか、全て表示するか。
    # ここでは全て表示しつつ、アンバランスなものを強調する形にする。
    
    for repo_name, row in repo_stats.iterrows():
        ai_count = row['AI']
        human_count = row['Human']
        diff = row['diff']
        is_balanced = row['is_balanced']
        
        status = "OK" if is_balanced else "UNBALANCED"
        
        # アンバランスなものだけ表示する場合は以下のif文を有効にする
        if not is_balanced:
            unbalanced_count += 1
            print(f"{repo_name:<45} | {ai_count:<10} | {human_count:<12} | {diff:<5} | {status}")

    print("-" * 90)
    print(f"分析対象リポジトリ総数: {len(repo_stats)}")
    print(f"バランスが取れていないリポジトリ数: {unbalanced_count}")
    print("="*90)

    # バランスが取れていないリポジトリの詳細リスト
    if unbalanced_count > 0:
        print("\n【バランス調整が必要なリポジトリ一覧】")
        unbalanced_repos = repo_stats[~repo_stats['is_balanced']].index.tolist()
        for repo in unbalanced_repos:
            row = repo_stats.loc[repo]
            print(f"- {repo} (AI: {row['AI']}, Human: {row['Human']})")
    else:
        print("\n全てのリポジトリでAIファイル数とHumanファイル数が一致しています。")

if __name__ == "__main__":
    check_repository_balance()
