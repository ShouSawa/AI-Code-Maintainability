import pandas as pd
import re
import os
from datetime import datetime
from urllib.parse import urlparse

def is_ai_commit(author, committer, message):
    """
    コミットがAIによるものかを判断する関数
    """
    ai_indicators = [
        'bot', 'ai', 'copilot', 'assistant', 'github-actions',
        'dependabot', 'renovate', 'automated', 'auto-'
    ]
    
    # author, committer, messageを小文字にして判定
    author_lower = str(author).lower() if author else ''
    committer_lower = str(committer).lower() if committer else ''
    message_lower = str(message).lower() if message else ''
    
    # AIの指標がいずれかに含まれているかチェック
    for indicator in ai_indicators:
        if (indicator in author_lower or 
            indicator in committer_lower or 
            indicator in message_lower):
            return True
    
    return False

def extract_repo_from_various_sources(pr_id, sha, filename):
    """
    pr_id、sha、filenameの全てから可能な限りリポジトリ情報を抽出
    """
    repo_candidates = []
    
    # 1. pr_idからの抽出
    if pd.notna(pr_id) and str(pr_id).strip():
        pr_str = str(pr_id).strip()
        
        # GitHub URL形式のパターン
        github_patterns = [
            r'github\.com[/:]([^/\s]+)/([^/\s#?]+)',  # https://github.com/owner/repo
            r'github\.com/([^/\s]+)/([^/\s#?]+)/pull/\d+',  # PR URL
            r'github\.com/([^/\s]+)/([^/\s#?]+)/issues/\d+',  # Issue URL
        ]
        
        for pattern in github_patterns:
            match = re.search(pattern, pr_str, re.IGNORECASE)
            if match:
                owner, repo = match.groups()
                # .gitを除去
                repo = repo.replace('.git', '')
                repo_candidates.append((owner, repo, 'pr_id'))
        
        # owner/repo#123 形式
        simple_pattern = re.match(r'^([^/\s]+)/([^/\s#]+)(?:#\d+)?$', pr_str)
        if simple_pattern:
            owner, repo = simple_pattern.groups()
            repo_candidates.append((owner, repo, 'pr_id'))
        
        # 数値のみの場合（PR番号のみ）は後でfilenameと組み合わせる
        if re.match(r'^\d+$', pr_str):
            repo_candidates.append(('pr_only', pr_str, 'pr_id'))
    
    # 2. filenameからの抽出
    if pd.notna(filename) and str(filename).strip():
        filename_str = str(filename).strip()
        
        # パスの最初の部分がowner/repo形式かチェック
        path_parts = filename_str.split('/')
        if len(path_parts) >= 2:
            potential_owner = path_parts[0]
            potential_repo = path_parts[1]
            
            # GitHubの命名規則に合致するかチェック
            if (re.match(r'^[a-zA-Z0-9._-]+$', potential_owner) and 
                re.match(r'^[a-zA-Z0-9._-]+$', potential_repo) and
                len(potential_owner) > 0 and len(potential_repo) > 0):
                repo_candidates.append((potential_owner, potential_repo, 'filename'))
        
        # filenameにgithub.comが含まれている場合
        github_in_filename = re.search(r'github\.com[/:]([^/\s]+)/([^/\s]+)', filename_str, re.IGNORECASE)
        if github_in_filename:
            owner, repo = github_in_filename.groups()
            repo = repo.split('/')[0]  # パスの最初の部分のみ
            repo = repo.replace('.git', '')
            repo_candidates.append((owner, repo, 'filename'))
    
    # 3. shaからの抽出
    if pd.notna(sha) and str(sha).strip():
        sha_str = str(sha).strip()
        
        # SHA文字列にリポジトリ情報が埋め込まれている場合
        sha_patterns = [
            r'([^/\s]+)/([^/\s@]+)@[a-f0-9]+',  # owner/repo@sha
            r'github\.com[/:]([^/\s]+)/([^/\s]+)',  # GitHub URL in SHA
        ]
        
        for pattern in sha_patterns:
            match = re.search(pattern, sha_str, re.IGNORECASE)
            if match:
                owner, repo = match.groups()
                repo = repo.replace('.git', '')
                repo_candidates.append((owner, repo, 'sha'))
    
    # 候補から最も信頼できるものを選択
    if not repo_candidates:
        return 'unknown', 'unknown', 'none'
    
    # 優先順位: pr_id > filename > sha
    # 同じソースから複数ある場合は最初のものを使用
    priority_order = ['pr_id', 'filename', 'sha']
    
    for source in priority_order:
        for owner, repo, src in repo_candidates:
            if src == source and owner != 'pr_only':
                return owner, repo, src
    
    # pr_onlyの場合はfilenameと組み合わせる
    pr_only = next((item for item in repo_candidates if item[0] == 'pr_only'), None)
    filename_repo = next((item for item in repo_candidates if item[2] == 'filename'), None)
    
    if pr_only and filename_repo:
        return filename_repo[0], filename_repo[1], 'pr_id+filename'
    
    # 最初の候補を返す
    return repo_candidates[0][0], repo_candidates[0][1], repo_candidates[0][2]

def analyze_data_patterns(df):
    """
    データのパターンを詳しく分析
    """
    print("\n=== 詳細データパターン分析 ===")
    
    # 各フィールドのユニークパターンを分析
    print("PR ID パターン分析:")
    pr_patterns = {}
    for pr_id in df['pr_id'].dropna().head(50):
        pr_str = str(pr_id)
        if '/' in pr_str:
            pr_patterns['contains_slash'] = pr_patterns.get('contains_slash', 0) + 1
        elif pr_str.isdigit():
            pr_patterns['numeric_only'] = pr_patterns.get('numeric_only', 0) + 1
        elif 'github.com' in pr_str.lower():
            pr_patterns['github_url'] = pr_patterns.get('github_url', 0) + 1
        else:
            pr_patterns['other'] = pr_patterns.get('other', 0) + 1
    
    for pattern, count in pr_patterns.items():
        print(f"  {pattern}: {count}件")
    
    print("\nFilename パターン分析:")
    filename_patterns = {}
    for filename in df['filename'].dropna().head(50):
        filename_str = str(filename)
        parts = filename_str.split('/')
        if len(parts) >= 2:
            filename_patterns['path_format'] = filename_patterns.get('path_format', 0) + 1
        elif 'github.com' in filename_str.lower():
            filename_patterns['github_url'] = filename_patterns.get('github_url', 0) + 1
        else:
            filename_patterns['simple_name'] = filename_patterns.get('simple_name', 0) + 1
    
    for pattern, count in filename_patterns.items():
        print(f"  {pattern}: {count}件")
    
    # サンプルデータを表示
    print(f"\nPR ID サンプル (最初の10件):")
    for i, sample in enumerate(df['pr_id'].dropna().head(10)):
        print(f"  {i+1}: '{sample}'")
    
    print(f"\nFilename サンプル (最初の10件):")
    for i, sample in enumerate(df['filename'].dropna().head(10)):
        print(f"  {i+1}: '{sample}'")
    
    print(f"\nSHA サンプル (最初の5件):")
    for i, sample in enumerate(df['sha'].dropna().head(5)):
        print(f"  {i+1}: '{sample}'")

def analyze_ai_commits(parquet_file_path):
    """
    メイン処理関数
    """
    print("Parquetファイルを読み込み中...")
    try:
        df = pd.read_parquet(parquet_file_path)
    except Exception as e:
        print(f"ファイルの読み込みエラー: {e}")
        return
    
    print(f"データ件数: {len(df)}")
    print(f"列名: {df.columns.tolist()}")
    
    # データパターンを詳細分析
    analyze_data_patterns(df)
    
    # statusが'added'のレコードのみを抽出
    added_files = df[df['status'] == 'added'].copy()
    print(f"\n追加されたファイルの件数: {len(added_files)}")
    
    if len(added_files) == 0:
        print("追加されたファイルが見つかりませんでした。")
        return
    
    # AIか人間かを判定
    added_files['is_ai'] = added_files.apply(
        lambda row: is_ai_commit(row['author'], row['committer'], row['message']), 
        axis=1
    )
    
    # リポジトリ情報を抽出
    print("リポジトリ情報を抽出中...")
    repo_info = added_files.apply(
        lambda row: extract_repo_from_various_sources(row['pr_id'], row['sha'], row['filename']), 
        axis=1
    )
    added_files['repo_owner'] = repo_info.apply(lambda x: x[0])
    added_files['repo_name'] = repo_info.apply(lambda x: x[1])
    added_files['repo_source'] = repo_info.apply(lambda x: x[2])
    
    # リポジトリ抽出結果の統計
    print("\n=== リポジトリ抽出結果統計 ===")
    unknown_count = len(added_files[added_files['repo_owner'] == 'unknown'])
    known_count = len(added_files) - unknown_count
    print(f"リポジトリ情報取得成功: {known_count}件 ({known_count/len(added_files)*100:.1f}%)")
    print(f"リポジトリ情報取得失敗: {unknown_count}件 ({unknown_count/len(added_files)*100:.1f}%)")
    
    # 抽出ソース別統計
    source_stats = added_files['repo_source'].value_counts()
    print("\n抽出ソース別統計:")
    for source, count in source_stats.items():
        print(f"  {source}: {count}件")
    
    # 取得できたリポジトリの上位を表示
    if known_count > 0:
        repo_counts = added_files[added_files['repo_owner'] != 'unknown'].groupby(['repo_owner', 'repo_name']).size().sort_values(ascending=False)
        print(f"\n上位リポジトリ（上位15件）:")
        for (owner, repo), count in repo_counts.head(15).items():
            print(f"  {owner}/{repo}: {count}件")
    
    # 出力用のデータフレームを作成
    output_columns = [
        'author',           # コミットした人の名前
        'sha',             # コミットハッシュ値
        'filename',        # ファイル名
        'repo_name',       # リポジトリ名
        'repo_owner',      # リポジトリ製作者名
        'pr_id',           # プルリクエストID
        'repo_source',     # リポジトリ情報の抽出元
        'commit_date'      # コミット日時（現在のデータにない場合はNaN）
    ]
    
    # コミット日時の列がない場合は空の列を追加
    if 'commit_date' not in added_files.columns:
        added_files['commit_date'] = pd.NaT
    
    # AIが追加したファイル
    ai_commits = added_files[added_files['is_ai'] == True][output_columns].copy()
    
    # 人間が追加したファイル
    human_commits = added_files[added_files['is_ai'] == False][output_columns].copy()
    
    # CSVファイルに出力
    ai_output_file = '../data_list/ai_added_files.csv'
    human_output_file = '../data_list/human_added_files.csv'
    
    try:
        os.makedirs('../data_list', exist_ok=True)
        
        ai_commits.to_csv(ai_output_file, index=False, encoding='utf-8-sig')
        print(f"\nAIが追加したファイル ({len(ai_commits)}件) を {ai_output_file} に保存しました。")
        
        human_commits.to_csv(human_output_file, index=False, encoding='utf-8-sig')
        print(f"人間が追加したファイル ({len(human_commits)}件) を {human_output_file} に保存しました。")
        
        # 統計情報を表示
        print("\n=== 最終統計情報 ===")
        print(f"総追加ファイル数: {len(added_files)}")
        print(f"AI追加ファイル数: {len(ai_commits)}")
        print(f"人間追加ファイル数: {len(human_commits)}")
        if len(added_files) > 0:
            print(f"AI追加率: {len(ai_commits)/len(added_files)*100:.1f}%")
        
    except Exception as e:
        print(f"CSV出力エラー: {e}")

if __name__ == "__main__":
    # parquetファイルのパスを指定してください
    parquet_file_path = '../data_list/pr_commit_details_local.parquet' 

    if not os.path.exists(parquet_file_path):
        print("指定されたファイルが見つかりません。")
    else:
        analyze_ai_commits(parquet_file_path)