import os
import pandas as pd
from github import Github
from git import Repo, GitCommandError
from dotenv import load_dotenv
from urllib.parse import urlparse
import re

# グローバル clone 設定
CLONE_DIR = "./cloned_Repository"
GLOBAL_CLONE_PATH = None

"""
GitのURLから所有者とリポジトリ名を抽出
"""
def parse_owner_repo(repo_url):
    if not repo_url:
        return None, None
    u = urlparse(repo_url)
    path_parts = [p for p in u.path.split("/") if p]
    if len(path_parts) >= 2:
        owner = path_parts[-2]
        repo = path_parts[-1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        if not owner or not repo:
            print(f"clone_repo: repo_url から owner/repo を解析できませんでした: {repo_url}")
            return None, None
        return owner, repo
    return None, None

""" 
リポジトリをクローンする

戻り値 : clone_path(クローンしたリポジトリのPath)
"""
def clone_repo(repo_url):
    global GLOBAL_CLONE_PATH
    owner, repo = parse_owner_repo(repo_url)
    if not owner or not repo:
        print(f"Invalid repo_url: {repo_url}")
        return None

    clone_url = f"https://github.com/{owner}/{repo}.git"
    print(clone_url)

    repo_name = repo
    clone_path = os.path.join(CLONE_DIR, repo_name)
    os.makedirs(CLONE_DIR, exist_ok=True)

    if not os.path.exists(clone_path):
        try:
            print(f"Cloning {clone_url} ...")
            Repo.clone_from(clone_url, clone_path)
        except GitCommandError as e:
            print(f"Error cloning {clone_url}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error cloning {clone_url}: {e}")
            return None
    else:
        print(f"クローン済み: {clone_path}")
    GLOBAL_CLONE_PATH = clone_path
    return clone_path

"""
Blame 解析 (--reverse を使う)

引数
clone_path（クローンしたリポジトリのpath）
file_path（リポジトリにある任意のファイルpath）
max_commits（何件のコミットまで遡るか）
"""
def get_blame_reverse(clone_path, file_path, max_commits=10):
    global GLOBAL_CLONE_PATH
    if not clone_path:
        clone_path = GLOBAL_CLONE_PATH
    repo = Repo(clone_path)
    git_cmd = repo.git

    # master/main どちらか存在する方を使う
    branch_name = None
    for candidate in ['master', 'main']:
        if candidate in repo.heads:
            branch_name = candidate
            break
    if not branch_name:
        try:
            branch_name = repo.active_branch.name
        except Exception:
            branch_name = 'HEAD'

    blame_results = []
    for commit in repo.iter_commits(branch_name, max_count=max_commits):
        # ファイルがそのコミットに存在するか確認
        try:
            repo.git.cat_file('-e', f'{commit.hexsha}:{file_path}')
        except GitCommandError:
            print(f"skip: {file_path} not present in commit {commit.hexsha}")
            continue

        # git blame --reverse を実行
        try:
            # ここでは低レベルで git コマンドを呼ぶことで明示的に --reverse を渡す
            # フォーマットは: git blame --reverse <commit> -- <file>
            blame_output = git_cmd.execute(['git', 'blame', '--reverse', commit.hexsha, '--', file_path])
            blame_results.append((commit.hexsha, blame_output.splitlines()))
        except GitCommandError as e:
            print(f"Error in reverse blame for {file_path} at {commit.hexsha}: {e}")
            blame_results.append((commit.hexsha, []))
        except Exception as e:
            print(f"Unexpected error running reverse blame for {file_path} at {commit.hexsha}: {e}")
            blame_results.append((commit.hexsha, []))
    return blame_results

"""
  PR修正情報を取得し，まとめる
"""
def get_pr_changes(pr):
    repo_url = pr.get("repo_url") or pr.get("repository_url")
    print("クローン開始")
    clone_path = clone_repo(repo_url)
    pr_id = pr.get("id")
    agent = pr.get("agent")

    owner, repo_name = parse_owner_repo(repo_url)
    g = Github(os.getenv("AUTH_TOKEN"))
    try:
        print("リポジトリ情報取得開始")
        gh_repo = g.get_repo(f"{owner}/{repo_name}")
    except Exception as e:
        print(f"Error: GitHub でリポジトリ取得失敗 {owner}/{repo_name}: {e}")
        return []
    try:
        print("PR情報取得開始")
        gh_pr = gh_repo.get_pull(int(pr.get("number")))
    except Exception as e:
        print(f"Error fetching PR {pr_id} (number={pr.get('number')}) in {owner}/{repo_name}: {e}")
        return []
    try:
        changed_files = [f.filename for f in gh_pr.get_files()]
    except Exception as e:
        print(f"Error fetching files for PR {pr_id}: {e}")
        changed_files = []
    if not changed_files:
        print(f"No changed files for PR {pr_id} -> スキップ")
        return []

    pr_change_list = []
    for i, file_path in enumerate(changed_files, start=1):
        if i > 10:
            print("10件以上のPRは解析しません")
            break
        print(f"PR情報{i}件目 Reverse-Blame解析: {file_path}")
        blame_output = get_blame_reverse(clone_path, file_path, max_commits=10)
        print(blame_output)
        if not blame_output:
            print(f"blame (--reverse) が空 or エラー: {file_path} (PR {pr_id})")
            continue

        for commit_index, (commit_sha, blame_lines) in enumerate(blame_output, start=1):
            if commit_index > 10:
                print("10件以上のコミットは解析しません")
                break

            for line_idx, line in enumerate(blame_lines, start=1):
                if line_idx > 30:
                    print("30行以上は解析しません")
                    break

                # 解析ロジックは従来の get_blame と同様
                opening = line.find('(')
                if opening == -1:
                    meta = ""
                    code = line.rstrip()
                else:
                    closing = line.find(')', opening)
                    if closing == -1:
                        meta = line[opening:].rstrip()
                        code = ""
                    else:
                        meta = line[opening:closing+1]
                        raw_code = line[closing+1:].rstrip('\n')
                        if raw_code.startswith(' '):
                            code = raw_code[1:]
                        else:
                            code = raw_code

                author = "unknown"
                date_str = None
                time_str = None
                line_number = None
                if meta:
                    try:
                        inside = meta[1:-1].strip()
                        m_lineno = re.search(r'(\d+)\s*$', inside)
                        if m_lineno:
                            line_number = int(m_lineno.group(1))
                            inside_no_lineno = inside[:m_lineno.start()].rstrip()
                        else:
                            inside_no_lineno = inside
                        m_dt = re.search(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})', inside_no_lineno)
                        if m_dt:
                            date_str = m_dt.group(1)
                            time_str = m_dt.group(2)
                            author_part = inside_no_lineno[:m_dt.start()].strip()
                            author = author_part.split()[0] if author_part else "unknown"
                        else:
                            parts = inside_no_lineno.split()
                            author = parts[0] if parts else "unknown"
                    except Exception:
                        author = "unknown"

                pr_change_list.append({
                    "pr_id": pr_id,
                    "file": file_path,
                    "author": author, # その行を後続で変更した人
                    "agent": agent, # PRを作成したエージェント
                    "commit_sha": commit_sha, # 行を編集した時のコミットのハッシュ値
                    "date": date_str,
                    "time": time_str,
                    "line_number": line_number,
                    "code": code # 最初にそのコードを変更した後のコード
                })

    return pr_change_list

""" 
main関数
"""
if __name__ == '__main__':
    load_dotenv()

    df = pd.read_parquet("./all_pull_request_local.parquet")

    merged_prs = df[df["merged_at"].notnull()]

    all_changes = []
    for i, (idx, pr) in enumerate(merged_prs.head(3).iterrows(), start=1):
        if i > 10:
            print("10件以上のPRは解析しません")
            break
        print(f"リポジトリ解析：{i} つ目 (DataFrame index={idx})")
        pr_changes = get_pr_changes(pr)
        all_changes.extend(pr_changes)

    df_changes = pd.DataFrame(all_changes)
    df_changes.to_csv("pr_blame_changes_reverse.csv", index=False)
    print("Finished. Saved to pr_blame_changes_reverse.csv")