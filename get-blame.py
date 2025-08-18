import os
import pandas as pd
from github import Github
from git import Repo , GitCommandError
from dotenv import load_dotenv
from urllib.parse import urlparse
from numpy.testing.print_coercion_tables import print_new_cast_table
import re

# グローバル clone 設定
CLONE_DIR = "./cloned_Repository"
GLOBAL_CLONE_PATH = None

"""
  GitのURLから所有者とリポジトリ名を抽出
"""
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
def clone_repo(repo_url):
  #  CLONE_DIR = "./cloned_Repository"
  
  global GLOBAL_CLONE_PATH
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
  # グローバルに保持
  GLOBAL_CLONE_PATH = clone_path
  return clone_path

"""
Blame 解析

引数
clone_path（クローンしたリポジトリのpath）
file_path（リポジトリにある任意のファイルpath）
"""
def get_blame(clone_path, file_path):
  # clone_path が None の場合はグローバルを使う
  global GLOBAL_CLONE_PATH
  if not clone_path:
    clone_path = GLOBAL_CLONE_PATH
  repo = Repo(clone_path)
  git_cmd = repo.git # git コマンドを打てるようなインターフェースを返してる

  # master/main どちらか存在する方を使う
  branch_name = None
  for candidate in ['master', 'main']:
    if candidate in repo.heads:
      branch_name = candidate
      break
  if not branch_name:
    branch_name = repo.active_branch.name  # fallback

  # コミットごとに Blame を取得
  blame_results = []
  for commit in repo.iter_commits(branch_name, max_count=10):
    # ファイルがそのコミットに存在するか確認
    try:
      repo.git.cat_file('-e', f'{commit.hexsha}:{file_path}')
    except GitCommandError:
      print(f"skip: {file_path} not present in commit {commit.hexsha}")
      continue

    # Blame を取得
    try:
      blame_output = git_cmd.blame(commit.hexsha, file_path)
      blame_results.append((commit.hexsha, blame_output.split("\n")))
    except GitCommandError as e:
      print(f"Error in blame for {file_path} at {commit.hexsha}: {e}")
      blame_results.append((commit.hexsha, []))
  return blame_results

"""
  PR修正情報を取得し，まとめる
"""
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

  # PRごとに以下を繰り返す
  pr_change_list = []
  for i, file_path in enumerate(changed_files,start=1):
    if i > 10:
      print("10件以上のPRは解析しません")
      break
    print(f"PR情報{i}件目 Blame解析")
    blame_output = get_blame(clone_path, file_path) # Blame解析
    if not blame_output:
      print(f"blame が空 or エラー: {file_path} (PR {pr_id})")
      continue

    # コミットごとに Blame 出力を処理
    for commit_index, (commit_sha, blame_lines) in enumerate(blame_output, start=1):
      # コミット上限を設定
      if commit_index > 10:
        print("10件以上のコミットは解析しません")
        break

      # 各行を処理
      for i, line in enumerate(blame_lines, start=1):
        # 行上限を設定
        if i > 30:
          print("30行以上は解析しません")
          break
          
        print(line)

        # - 最初の '(' から最初に対応する ')' から著者・日付・時刻・行番号・codeを抽出
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
            # 先頭スペース（インデント）は保持する
            raw_code = line[closing+1:].rstrip('\n')
            if raw_code.startswith(' '):
              code = raw_code[1:]
            else:
              code = raw_code

        # meta から author, date, time, 行番号を取り出す
        author = "unknown"
        date_str = None
        time_str = None
        blame_line_no = None
        if meta:
          try:
            inside = meta[1:-1].strip()  # 括弧の内側
            # 行番号は末尾の数値
            m_lineno = re.search(r'(\d+)\s*$', inside)
            if m_lineno:
              blame_line_no = int(m_lineno.group(1))
              inside_no_lineno = inside[:m_lineno.start()].rstrip()
            else:
              inside_no_lineno = inside
            # 日付と時刻を抽出（例: 2025-07-24 23:09:45）
            m_dt = re.search(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})', inside_no_lineno)
            if m_dt:
              date_str = m_dt.group(1)
              time_str = m_dt.group(2)
              # 日時の前のテキストを著者とみなす（先頭トークン）
              author_part = inside_no_lineno[:m_dt.start()].strip()
              author = author_part.split()[0] if author_part else "unknown"
            else:
              # 日時が見つからなければ先頭トークンを著者とする
              parts = inside_no_lineno.split()
              author = parts[0] if parts else "unknown"
          except Exception:
            author = "unknown"

        pr_change_list.append({
          "pr_id": pr_id,
          "file": file_path,
          "author": author,
          "agent": agent,
          "commit_sha": commit_sha,
          "date": date_str,
          "time": time_str,
          "blame_line_no": blame_line_no, # 行番号
          "code": code
        })

  return pr_change_list

""" 
main関数
"""
if __name__ == '__main__':
  # .envファイルを読み込む
  load_dotenv()

  # データセットの読み込み
  df = pd.read_parquet("./all_pull_request_local.parquet")

  # マージされた PR のみを抽出
  merged_prs = df[df["merged_at"].notnull()]

  # 全PR解析
  all_changes = []
  for i,(idx, pr) in enumerate(merged_prs.head(3).iterrows(),start=1):  # head(件数)で件数制限
    # 上限を追加
    if i > 10:
      print("10件以上のPRは解析しません")
      break
    print(f"リポジトリ解析：{i} つ目 (DataFrame index={idx})")
    pr_changes = get_pr_changes(pr)
    all_changes.extend(pr_changes)

  # DataFrame化
  df_changes = pd.DataFrame(all_changes)
  df_changes.to_csv("pr_blame_changes.csv", index=False)
  print("Finished. Saved to pr_blame_changes.csv")
