import pandas as pd
from github import Github
import os
from tqdm import tqdm
import time
from dotenv import load_dotenv

def update_dataset():
    """
    results_v4.csvを読み込み、GitHub APIを使用して各コミットにおける
    特定ファイルの変更行数（additions + deletions）を取得し、
    results_v5.csvとして保存するスクリプト。
    
    実行には環境変数 GITHUB_TOKEN が必要です。
    """
    
    # パス設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.join(script_dir, "../results/results_v4.csv")
    output_csv = os.path.join(script_dir, "../results/results_v5.csv")
    
    if not os.path.exists(input_csv):
        print(f"エラー: {input_csv} が見つかりません。")
        return

    print(f"読み込み中: {input_csv}")
    df = pd.read_csv(input_csv)
    
    # 新しいカラムを追加（未計算は-1）
    if 'file_specific_changed_lines' not in df.columns:
        df['file_specific_changed_lines'] = -1

    # .envファイルを読み込む
    load_dotenv()

    # GitHub認証
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("エラー: 環境変数 GITHUB_TOKEN が設定されていません。")
        print("export GITHUB_TOKEN='your_token' (Linux/Mac) または $env:GITHUB_TOKEN='your_token' (PowerShell) で設定してください。")
        return
    
    try:
        g = Github(token)
        # トークン確認
        user = g.get_user()
        print(f"GitHub API認証成功: {user.login}")
    except Exception as e:
        print(f"GitHub API認証エラー: {e}")
        return
    
    # リポジトリオブジェクトのキャッシュ
    repos = {}
    
    print(f"データセットの更新を開始します（全 {len(df)} 行）...")
    
    # 変更が必要な行のみ抽出
    target_indices = df[df['file_specific_changed_lines'] == -1].index
    
    for i, index in enumerate(tqdm(target_indices)):
        row = df.loc[index]
        
        repo_name = row['repository_name']
        commit_hash = row['commit_hash']
        file_name = row['file_name']
        
        try:
            # リポジトリ取得（キャッシュ利用）
            if repo_name not in repos:
                repos[repo_name] = g.get_repo(repo_name)
            
            repo = repos[repo_name]
            
            # コミット取得
            commit = repo.get_commit(commit_hash)
            
            # コミット内のファイルから対象ファイルを探す
            file_changes = 0
            found = False
            
            # ファイル数が多いコミットの場合、API制限や時間がかかる可能性があるため注意
            # PyGithubのfilesはPaginatedListなのでイテレートで取得
            for f in commit.files:
                if f.filename == file_name:
                    file_changes = f.additions + f.deletions
                    found = True
                    break
            
            if found:
                df.at[index, 'file_specific_changed_lines'] = file_changes
            else:
                # ファイル名が一致しない場合（リネームなど）
                # とりあえず0にしておくか、別途調査が必要
                # ここでは0として記録
                df.at[index, 'file_specific_changed_lines'] = 0
                
        except Exception as e:
            print(f"\nエラー発生 ({repo_name} - {commit_hash}): {e}")
            # レート制限などの場合少し待機
            time.sleep(1)
        
        # 100件ごとに保存
        if (i + 1) % 100 == 0:
            df.to_csv(output_csv, index=False)
            
    # 最終保存
    df.to_csv(output_csv, index=False)
    print(f"完了しました。結果を保存しました: {output_csv}")

if __name__ == "__main__":
    update_dataset()
