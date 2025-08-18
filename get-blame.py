import os
import pandas as pd
from github import Github
from git import Repo , GitCommandError
from dotenv import load_dotenv
from urllib.parse import urlparse

from numpy.testing.print_coercion_tables import print_new_cast_table


# -----------------------------
# GitのURLから所有者とリポジトリ名を抽出
# -----------------------------
def parse_owner_repo(repo_url):
    if not repo_url:
        return None, None
    u = urlparse(repo_url)
    path_parts = [p for p in u.path.split("/") if p]
    # path_parts の最後の2つが owner, repo になるはず
    if len(path_parts) >= 2:
        owner = path_parts[-2]
        repo = path_parts[-1]
        if repo.endswith(".git"):
            repo = repo[:-4] # .gitの文字列を削除
        if not owner or not repo:
            print(f"clone_repo: repo_url から owner/repo を解析できませんでした: {repo_url}")
            return None, None
        return owner, repo
    return None, None

""" 
リポジトリをクローンする

戻り値 : clone_path(クローンしたリポジトリのPath)
"""
# -----------------------------
# リポジトリクローン
# -----------------------------
def clone_repo(repo_url):
    CLONE_DIR = "./cloned_Repository"

    owner, repo = parse_owner_repo(repo_url)
    # URLから所有者とリポジトリ名を取得できなかったとき

    clone_url = f"https://github.com/{owner}/{repo}.git"
    print(clone_url)

    repo_name = repo
    clone_path = os.path.join(CLONE_DIR, repo_name)
    os.makedirs(CLONE_DIR, exist_ok=True)

    if not os.path.exists(clone_path): # 既にクローンしてる場合はクローンしない
        try:
            # クローンできたとき
            print(f"Cloning {clone_url} ...")
            Repo.clone_from(clone_url, clone_path)
        except GitCommandError as e:
            # 何らかの理由でクローン失敗したとき
            print(f"Error cloning {clone_url}: {e}")
            return None
        except Exception as e:
            # GitCommandError以外の例外
            print(f"Unexpected error cloning {clone_url}: {e}")
            return None
    else:
        print(f"クローン済み: {clone_path}")
    return clone_path

"""
Blame 解析

引数：clone_path（クローンしたリポジトリのpath）
    file_path（リポジトリにある，任意のファイルpath）
"""
def get_blame(clone_path, file_path, commit_sha=None):
    if not commit_sha:
        print("commit_shaが存在してません")

    repo = Repo(clone_path)
    git_cmd = repo.git # git コマンドを打てるようなインターフェースを返してる

    for commit in repo.iter_commits('master', max_count=10):
        print(commit.hexsha)

    try:
        if commit_sha:
            blame_output = git_cmd.blame(commit_sha, file_path) # GitPythonを使ってGit Blameを実行
        else:
            blame_output = git_cmd.blame(file_path)
        return blame_output.split("\n")
    except GitCommandError as e:
        print(f"Error in blame for {file_path}: {e}")
        return []

# -----------------------------
# PR修正情報取得（存在しなければスキップ）
# -----------------------------
def get_pr_changes(pr):
    repo_url = pr.get("repo_url") or pr.get("repository_url")  # 念のためキーの両対応
    print("クローン開始")
    clone_path = clone_repo(repo_url)  # リポジトリをクローン
    pr_id = pr.get("id")
    agent = pr.get("agent")

    # owner/repo を取得して GitHub API を呼ぶ
    owner, repo_name = parse_owner_repo(repo_url)

    # GitHub アクセストークンを設定
    g = Github(os.getenv("AUTH_TOKEN"))

    # Github API でリポジトリ情報を取得
    try:
        print("リポジトリ情報取得開始")
        gh_repo = g.get_repo(f"{owner}/{repo_name}")
    except Exception as e:
        print(f"Error: GitHub でリポジトリ取得失敗 {owner}/{repo_name}: {e}")
        return []

    # PR情報を取得
    try:
        print("PR情報取得開始")
        gh_pr = gh_repo.get_pull(int(pr.get("number")))
    except Exception as e:
        print(f"Error fetching PR {pr_id} (number={pr.get('number')}) in {owner}/{repo_name}: {e}")
        return []  # PRが見つからない／権限不足ならスキップ

    # ファイルの名前をリストにまとめる
    try:
        changed_files = [f.filename for f in gh_pr.get_files()]
    except Exception as e:
        print(f"Error fetching files for PR {pr_id}: {e}")
        changed_files = []

    # PR情報がなかった場合，スキップする
    if not changed_files:
        print(f"No changed files for PR {pr_id} -> スキップ")
        return []

    pr_change_list = []

    # PRごとに以下を繰り返す
    for i, file_path in enumerate(changed_files):
        print(f"PR情報{i}件目 Blame解析")
        blame_output = get_blame(clone_path, file_path, commit_sha=pr.get("merge_commit_sha")) # Blame解析
        if not blame_output:
            print(f"blame が空 or エラー: {file_path} (PR {pr_id})")
            continue
        for line_number, line in enumerate(blame_output, start=1):
            # Blame出力例: <SHA> (<Author> <Date> <Time> <Timezone> <LineNum>) <Code>
            parts = line.split(")")
            if len(parts) < 2:
                continue
            meta, code = parts[0], parts[1].strip()
            # メタ部分から author を抽出（安全に）
            author = "unknown"
            if "(" in meta:
                meta_inside = meta.split("(", 1)[1]
                author = meta_inside.split()[0] if meta_inside.split() else "unknown"
            pr_change_list.append({
                "pr_id": pr_id,
                "file": file_path,
                "line_number": line_number,
                "author": author,
                "agent": agent,
                "code": code
            })

    return pr_change_list

if __name__ == '__main__':
    # .envファイルを読み込む
    load_dotenv()

    # データセットの読み込み
    df = pd.read_parquet("./all_pull_request_local.parquet")

    # マージされた PR のみを抽出
    merged_prs = df[df["merged_at"].notnull()]

    # -----------------------------
    # 全PR解析
    # -----------------------------
    all_changes = []
    for i,(idx, pr) in enumerate(merged_prs.head(3).iterrows(),start=1):  # まずは10件でテスト
        print(f"リポジトリ解析：{i} つ目 (DataFrame index={idx})")
        pr_changes = get_pr_changes(pr)
        all_changes.extend(pr_changes)

    # DataFrame化
    df_changes = pd.DataFrame(all_changes)
    df_changes.to_csv("pr_blame_changes.csv", index=False)
    print("Finished. Saved to pr_blame_changes.csv")
