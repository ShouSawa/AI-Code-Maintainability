import os
import git
import json
import re
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

def process_metta_repository(repo_name) -> List[Dict]:
    """
    AutoGPTリポジトリのみを処理
    """
    # -----------入力--------------------
    metta_repo_path = Path(f"../cloned_Repository/{repo_name}")
    
    if not metta_repo_path.exists():
        print(f"Directory {metta_repo_path} does not exist!")
        return []
    
    if not (metta_repo_path / ".git").exists():
        print(f"{metta_repo_path} is not a git repository!")
        return []
    
    print(f"Processing metta repository: {metta_repo_path}")
    
    bug_fixes = extract_bug_fix_commits(str(metta_repo_path))
    print(f"Found {len(bug_fixes)} bug-fix commits in metta repository")
    
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
    print(f"Total bug-fix commits found: {len(bug_fixes)}")

def main():
    """
    メイン処理
    """
    print("Starting bug-fix commit detection for metta repository...")

    #-----------入力--------------------
    repo_name = "ai"

    # mettaリポジトリのみを処理
    bug_fixes = process_metta_repository(repo_name)
    
    if not bug_fixes:
        print("No bug-fix commits found in metta repository!")
        return
    
    # 結果を表示
    print(f"\nTotal bug-fix commits found in metta: {len(bug_fixes)}")
    
    # -----------出力--------------------
    # JSONファイルに保存
    output_path = f"../data_list/RQ2/{repo_name}-bug-fixes.json"
    save_bug_fixes_json(bug_fixes, output_path)
    
    # 最初の数個のコミットを表示（デバッグ用）
    print(f"\nFirst few bug-fix commits:")
    for i, fix in enumerate(bug_fixes[:5]):
        print(f"  {i+1}. {fix['fix_commit_hash']}")

if __name__ == "__main__":
    main()