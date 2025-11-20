import os
import git
import json
import random
from typing import List, Dict
from pathlib import Path

def is_bug_fix_commit(commit_message: str) -> bool:
    """
    コミットメッセージにバグ修正を示すキーワードが含まれているかチェック
    """
    # バグ修正を示すキーワード（大文字小文字区別なし）
    bug_keywords = [
        'fix', 'bug', 'patch', 'error', 'issue', 'resolve', 'solve',
        'correct', 'repair', 'hotfix', 'bugfix', 'defect', 'fault'
    ]
    
    commit_message_lower = commit_message.lower()
    
    # キーワードが含まれているかチェック
    for keyword in bug_keywords:
        if keyword in commit_message_lower:
            return True
    
    return False

def extract_bug_fix_commits(repo_path: str) -> List[Dict]:
    """
    指定されたリポジトリからバグ修正コミットを抽出
    """
    try:
        repo = git.Repo(repo_path)
        repo_name = os.path.basename(repo_path)
        
        bug_fix_commits = []
        
        # 全てのコミットを取得
        for commit in repo.iter_commits():
            commit_message = commit.message.strip()
            
            # バグ修正コミットかどうかチェック
            if is_bug_fix_commit(commit_message):
                bug_fix_info = {
                    "repo_name": repo_name,
                    "fix_commit_hash": str(commit.hexsha)
                }
                bug_fix_commits.append(bug_fix_info)
        
        return bug_fix_commits
    
    except Exception as e:
        print(f"Error processing repository {repo_path}: {str(e)}")
        return []

def process_repository(repo_name: str) -> List[Dict]:
    """
    リポジトリを処理してバグ修正コミットを抽出
    """
    # -----------入力--------------------
    repo_path = Path(f"../cloned_Repository/{repo_name}")
    
    if not repo_path.exists():
        print(f"Directory {repo_path} does not exist!")
        return []
    
    if not (repo_path / ".git").exists():
        print(f"{repo_path} is not a git repository!")
        return []
    
    print(f"Processing repository: {repo_path}")
    
    bug_fixes = extract_bug_fix_commits(str(repo_path))
    print(f"Found {len(bug_fixes)} bug-fix commits in {repo_name} repository")
    
    return bug_fixes

def save_bug_fixes_json(bug_fixes: List[Dict], output_path: str):
    """
    バグ修正コミット情報をJSONファイルに保存
    """
    # 出力ディレクトリを作成
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # JSONファイルに保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(bug_fixes, f, indent=2, ensure_ascii=False)
    
    print(f"Bug-fix commits saved to: {output_path}")
    print(f"Total bug-fix commits: {len(bug_fixes)}")

def reduce_json_randomly(data: List[Dict], output_count: int = 100) -> List[Dict]:
    """
    JSONデータからランダムに指定数を選択
    """
    # データが指定数未満の場合は警告
    if len(data) < output_count:
        print(f"Warning: データが{len(data)}個しかありません。全てのデータを使用します。")
        output_count = len(data)
    
    # ランダムに選択
    selected_data = random.sample(data, output_count)
    
    print(f"元のデータ数: {len(data)}個")
    print(f"選択されたデータ数: {len(selected_data)}個")
    
    return selected_data

def main():
    """
    メイン処理：バグ修正コミットの検出 → ランダムサンプリング
    """
    print("=" * 70)
    print("RQ2-bc: Bug-fix Commit Detection and Random Sampling")
    print("=" * 70)
    
    # -----------入力--------------------
    repo_name = "ai"
    sample_count = 100  # サンプリング数
    
    # Step 1: バグ修正コミットを抽出
    print("\n[Step 1/3] Extracting bug-fix commits...")
    bug_fixes = process_repository(repo_name)
    
    if not bug_fixes:
        print("No bug-fix commits found!")
        return
    
    # Step 2: 全バグ修正コミットを保存
    print("\n[Step 2/3] Saving all bug-fix commits...")
    all_output_path = f"../data_list/RQ2/{repo_name}-bug-fixes.json"
    save_bug_fixes_json(bug_fixes, all_output_path)
    
    # Step 3: ランダムサンプリング
    print(f"\n[Step 3/3] Random sampling ({sample_count} commits)...")
    sampled_bug_fixes = reduce_json_randomly(bug_fixes, sample_count)
    
    # サンプリング結果を保存
    sampled_output_path = f"../data_list/RQ2/{repo_name}-bug-fixes-100.json"
    save_bug_fixes_json(sampled_bug_fixes, sampled_output_path)
    
    # 結果サマリー
    print("\n" + "=" * 70)
    print("Summary:")
    print("=" * 70)
    print(f"Repository: {repo_name}")
    print(f"Total bug-fix commits found: {len(bug_fixes)}")
    print(f"Sampled commits: {len(sampled_bug_fixes)}")
    print(f"\nOutput files:")
    print(f"  - All commits: {all_output_path}")
    print(f"  - Sampled (100): {sampled_output_path}")
    
    # 最初の5個のサンプルを表示
    print(f"\nFirst 5 sampled bug-fix commits:")
    for i, fix in enumerate(sampled_bug_fixes[:5]):
        print(f"  {i+1}. {fix['fix_commit_hash']}")
    
    print("\n✓ Processing completed successfully!")

if __name__ == "__main__":
    main()
