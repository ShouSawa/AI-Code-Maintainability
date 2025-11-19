"""
RQ1統合プログラム: AIコミット分析システム（GitHub API版）
機能: リポジトリをクローンせずにGitHub APIで分析
"""

import os # ファイルパスを扱うためのライブラリ
import pandas as pd # データフレームを扱うためのライブラリ
from datetime import datetime, timedelta # 日付取得や時間の計算のためのライブラリ
import re # 正規表現を扱うためのライブラリ
import numpy as np # 数値計算を行うためのライブラリ
from transformers import pipeline # 事前学習したモデルを扱うためのライブラリ
import requests # HTTPリクエストを扱うためのライブラリ
from github import Github # Github APIを扱うためのライブラリ
from dotenv import load_dotenv # .envファイルを読み込むためのライブラリ
import time
import socket

# srcフォルダ内の.envファイルを読み込む
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path)

pipe = pipeline("text-generation", model="0x404/ccs-code-llama-7b", device_map="auto")
tokenizer = pipe.tokenizer

# ネットワーク再接続機能
def check_network_connectivity(host="api.github.com", port=443, timeout=5):
    """
    ネットワーク接続を確認する
    
    Args:
        host: 接続先ホスト
        port: 接続ポート
        timeout: タイムアウト（秒）
    
    Returns:
        bool: 接続可能ならTrue
    """
    try:
        socket.create_connection((host, port), timeout=timeout)
        return True
    except (socket.gaierror, socket.timeout, OSError):
        return False

def retry_with_network_check(func):
    """
    ネットワークエラー時に自動的に再接続を試みるデコレータ
    
    Args:
        func: ラップする関数
    
    Returns:
        ラップされた関数
    """
    def wrapper(*args, **kwargs):
        max_wait = 60  # 最大待機時間（秒）
        wait_time = 10  # 初期待機時間（秒）
        
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e).lower()
                # DNS解決エラーやConnectionErrorを検出
                if 'nameresolutionerror' in error_str or 'failed to resolve' in error_str or \
                   'connectionerror' in error_str or 'connection error' in error_str or \
                   'getaddrinfo failed' in error_str:
                    
                    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ネットワークエラーを検出しました: {e}")
                    print(f"ネットワーク接続を確認中...")
                    
                    # ネットワークが復旧するまで待機
                    while not check_network_connectivity():
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ネットワークに接続できません。{wait_time}秒後に再試行します...")
                        time.sleep(wait_time)
                        # 指数バックオフ（最大60秒まで）
                        wait_time = min(wait_time * 2, max_wait)
                    
                    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ネットワーク接続が復旧しました。処理を再開します...")
                    wait_time = 10  # 待機時間をリセット
                    continue  # 関数を再実行
                else:
                    # ネットワーク以外のエラーはそのまま送出
                    raise
    
    return wrapper

class RQ1AnalyzerAPI:
    # AIボットアカウント定義（作成者名で判定）
    AI_BOT_ACCOUNTS = {
        'copilot': ['copilot'],  # GitHub Copilot
        'cursor': ['cursor'],  # Cursor
        'devin': ['devin-ai-integration'],  # Devin
        'claude': ['claude']  # Claude
    }
    
    def __init__(self, repo_name_full, github_token=None):
        """
        repo_name_full: 'owner/repo' 形式のリポジトリ名
        github_token: GitHub Personal Access Token
        """
        self.repo_name_full = repo_name_full
        self.repo_name = repo_name_full.split('/')[-1]
        self.github_token = github_token
        
        if not self.github_token:
            raise ValueError("GitHub tokenが必要です。.envファイルにGITHUB_TOKENを設定してください。")
        
        # GitHub API初期化
        self.g = Github(self.github_token)
        self.repo = self.g.get_repo(repo_name_full)
        
        # 出力ディレクトリ
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.final_output_dir = os.path.join(script_dir, "../data_list/RQ1/final_result")
        os.makedirs(self.final_output_dir, exist_ok=True)
        
        print(f"リポジトリ接続成功: {repo_name_full}")
        print(f"スター数: {self.repo.stargazers_count}, フォーク数: {self.repo.forks_count}")

    def is_ai_generated_commit(self, all_authors):
        """
        AIコミット判定（全アカウントをチェック）
        
        Args:
            all_authors: コミットに関与した全アカウント名（文字列またはリスト）
            
        Returns:
            tuple: (bool, str) - AIかどうか, AIの種類またはhuman
        """
        # 文字列の場合はリストに変換
        if isinstance(all_authors, str):
            all_authors = [all_authors]
        
        # 全アカウントをチェック
        for author_name in all_authors:
            author_lower = author_name.lower()
            for ai_type, bot_names in self.AI_BOT_ACCOUNTS.items():
                if any(bot_name.lower() in author_lower for bot_name in bot_names):
                    return True, ai_type
        
        return False, "human"

    def detect_specific_ai_tool(self, all_authors):
        """
        AIツール特定（全アカウントをチェック）
        
        Args:
            all_authors: コミットに関与した全アカウント名（文字列またはリスト）
            
        Returns:
            str: AIツール名、または'N/A'
        """
        # 文字列の場合はリストに変換
        if isinstance(all_authors, str):
            all_authors = [all_authors]
        
        tool_map = {
            'copilot': 'Copilot',
            'cursor': 'Cursor',
            'devin': 'Devin',
            'claude': 'Claude'
        }
        
        # 全アカウントをチェック
        for author_name in all_authors:
            author_lower = author_name.lower()
            for ai_type, bot_names in self.AI_BOT_ACCOUNTS.items():
                if any(bot_name.lower() in author_lower for bot_name in bot_names):
                    return tool_map.get(ai_type, 'N/A')
        
        return 'N/A'

    @retry_with_network_check
    def get_commits_with_file_additions_api(self, max_commits=500, skip_commits=0):
        """GitHub APIで90日以前のファイル追加コミット取得（ランダムサンプリング版）
        
        Args:
            max_commits: 取得する最大コミット数
            skip_commits: スキップするコミット数（オフセット）
        """
        print(f"=== GitHub APIでコミット取得中 (skip={skip_commits}, max={max_commits}, ランダムサンプリング) ===")
        
        commits_data = []
        total_commits_count = 0  # 90日以前のコミット総数
        
        try:
            # 90日以前のコミットを取得
            cutoff_date_90 = datetime.now() - timedelta(days=90)
            print(f"90日以前のコミットを取得中 (until: {cutoff_date_90.date()})...")
            commits_90 = self.repo.get_commits(until=cutoff_date_90)
            
            # 初回呼び出し時のみ全コミットをリストに変換してランダム順序を生成
            if not hasattr(self, '_all_commits_cache'):
                print("全コミットをリストに変換中...")
                self._all_commits_cache = list(commits_90)
                total_commits_count = len(self._all_commits_cache)
                print(f"総コミット数: {total_commits_count}件")
                
                # ランダムインデックスを生成（重複なし）
                import random
                self._random_indices = list(range(total_commits_count))
                random.shuffle(self._random_indices)
                print("ランダム順序を生成しました")
            else:
                total_commits_count = len(self._all_commits_cache)
            
            # ランダムインデックスに基づいてコミットを取得
            end_index = min(skip_commits + max_commits, len(self._random_indices))
            selected_indices = self._random_indices[skip_commits:end_index]
            
            if not selected_indices:
                print(f"取得可能なコミットがありません（skip={skip_commits}, total={total_commits_count}）")
                return commits_data, total_commits_count
            
            print(f"インデックス {skip_commits}～{end_index-1} からランダムに取得")
            
            count = 0
            for idx in selected_indices:
                commit = self._all_commits_cache[idx]
                count += 1
                
                if count >= max_commits:
                    print(f"最大コミット数({max_commits})に達しました")
                    break
                
                count += 1
                if count % 50 == 0:
                    print(f"処理中: {count}件...")
                
                try:
                    # コミット情報取得
                    commit_sha = commit.sha
                    author_name = commit.commit.author.name or "Unknown"
                    author_email = commit.commit.author.email or "unknown@example.com"
                    commit_date = commit.commit.author.date.isoformat()
                    message = commit.commit.message
                    
                    # コミットアカウントのみ取得（author + committer）
                    all_authors = [author_name]
                    
                    # committerも追加（authorと異なる場合）
                    if commit.commit.committer and commit.commit.committer.name:
                        committer_name = commit.commit.committer.name
                        if committer_name != author_name and committer_name not in all_authors:
                            all_authors.append(committer_name)
                    
                    # 追加されたファイルを検索
                    added_files = []
                    for file in commit.files:
                        if file.status == 'added':
                            added_files.append(file.filename)
                    
                    if added_files:
                        commits_data.append({
                            'hash': commit_sha,
                            'author_name': author_name,
                            'author_email': author_email,
                            'all_authors': all_authors,  # 全作成者リスト
                            'date': commit_date,
                            'message': message,
                            'added_files': added_files
                        })
                    
                    # API rate limit対策
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"コミット処理エラー {commit.sha[:8]}: {e}")
                    continue
            
            print(f"コミット取得完了: 90日以前の総コミット数={total_commits_count}件, ファイル追加コミット={len(commits_data)}件")
            return commits_data, total_commits_count
            
        except Exception as e:
            print(f"GitHub API エラー: {e}")
            return [], 0

    def step1_find_added_files(self, target_ai_files=10, target_human_files=10):
        """ステップ1: ファイル追加分析（API版・ランダムサンプリング・段階的取得）
        
        Args:
            target_ai_files: 目標AI作成ファイル数
            target_human_files: 目標Human作成ファイル数
        """
        print("\n=== ステップ1: ファイル追加分析 (API版・ランダムサンプリング・段階的取得) ===")
        print(f"目標: AI={target_ai_files}件, Human={target_human_files}件")
        print("※ 90日以前のコミットをランダム順序で重複なく取得します")

        # 段階的にコミット取得
        initial_batch = 500  # 最初の取得数
        additional_batch = 100  # 追加取得数
        skip_commits = 0
        all_csv_data = []
        total_commits_checked = 0
        
        # 最初の500件取得
        print(f"\n--- 第1回: {initial_batch}件のコミット取得 ---")
        commits_data, total_commits = self.get_commits_with_file_additions_api(
            max_commits=initial_batch, 
            skip_commits=skip_commits
        )
        
        if total_commits == 0:
            print("90日以前のコミットが存在しません")
            return None, 'no_commits_90days'
        
        total_commits_checked += len(commits_data)
        
        # データ作成
        for commit in commits_data:
            is_ai, ai_type = self.is_ai_generated_commit(commit['all_authors'])
            author_type = "AI" if is_ai else "Human"
            ai_tool = self.detect_specific_ai_tool(commit['all_authors']) if is_ai else "N/A"
            
            for file_path in commit['added_files']:
                all_csv_data.append({
                    'commit_hash': commit['hash'],
                    'commit_date': commit['date'],
                    'added_file': file_path,
                    'author_type': author_type,
                    'ai_type': ai_type,
                    'ai_tool': ai_tool,
                    'author_name': commit['author_name'],
                    'author_email': commit['author_email'],
                    'commit_message': commit['message']
                })
        
        # 現在の状況確認
        df = pd.DataFrame(all_csv_data)
        ai_count = len(df[df['author_type']=='AI']) if len(df) > 0 else 0
        human_count = len(df[df['author_type']=='Human']) if len(df) > 0 else 0
        print(f"現在の状況 - 総計:{len(df)} AI:{ai_count} Human:{human_count}")
        
        # 追加取得が必要かチェック
        skip_commits = initial_batch
        round_count = 2
        
        while (ai_count < target_ai_files or human_count < target_human_files) and skip_commits < total_commits:
            print(f"\n--- 第{round_count}回: さらに{additional_batch}件のコミット取得 (offset={skip_commits}) ---")
            
            additional_commits, _ = self.get_commits_with_file_additions_api(
                max_commits=additional_batch,
                skip_commits=skip_commits
            )
            
            if not additional_commits:
                print("これ以上コミットが取得できません")
                break
            
            # 追加データ作成
            for commit in additional_commits:
                is_ai, ai_type = self.is_ai_generated_commit(commit['all_authors'])
                author_type = "AI" if is_ai else "Human"
                ai_tool = self.detect_specific_ai_tool(commit['all_authors']) if is_ai else "N/A"
                
                for file_path in commit['added_files']:
                    all_csv_data.append({
                        'commit_hash': commit['hash'],
                        'commit_date': commit['date'],
                        'added_file': file_path,
                        'author_type': author_type,
                        'ai_type': ai_type,
                        'ai_tool': ai_tool,
                        'author_name': commit['author_name'],
                        'author_email': commit['author_email'],
                        'commit_message': commit['message']
                    })
            
            # 更新後の状況確認
            df = pd.DataFrame(all_csv_data)
            ai_count = len(df[df['author_type']=='AI'])
            human_count = len(df[df['author_type']=='Human'])
            print(f"現在の状況 - 総計:{len(df)} AI:{ai_count} Human:{human_count}")
            
            skip_commits += additional_batch
            round_count += 1
        
        # 最終結果
        print(f"\n--- 最終結果 ---")
        print(f"分析完了 - 総計:{len(df)} AI:{ai_count} Human:{human_count}")
        print(f"調査したコミット範囲: {skip_commits}件")
        
        if len(df) == 0:
            print(f"ファイル追加コミット未発見（90日以前のコミット総数: {total_commits}件）")
            return None, 'no_file_additions'
        
        # AI作成ファイルが見つからなかった場合
        if ai_count == 0:
            print("警告: AI作成ファイルが見つかりませんでした")
            return df, 'no_ai_files'
        
        # 目標数に達しなかった場合の警告
        if ai_count < target_ai_files or human_count < target_human_files:
            print(f"警告: 目標数に達しませんでした（AI: {ai_count}/{target_ai_files}, Human: {human_count}/{target_human_files}）")
            print(f"見つかった数で分析を続行します")
        
        return df, 'success'

    @retry_with_network_check
    def get_file_commits_api(self, file_path):
        """GitHub APIで特定ファイルのコミット履歴取得"""
        try:
            commits = self.repo.get_commits(path=file_path)
            commit_logs = []
            
            for commit in commits:
                author_name = commit.commit.author.name or "Unknown"
                
                # コミットアカウントのみ取得（author + committer）
                all_authors = [author_name]
                
                # committerも追加（authorと異なる場合）
                if commit.commit.committer and commit.commit.committer.name:
                    committer_name = commit.commit.committer.name
                    if committer_name != author_name and committer_name not in all_authors:
                        all_authors.append(committer_name)
                
                commit_logs.append({
                    'hash': commit.sha,
                    'date': commit.commit.author.date.isoformat(),
                    'author': author_name,
                    'all_authors': all_authors,  # 全作成者リスト
                    'email': commit.commit.author.email or "unknown@example.com",
                    'message': commit.commit.message
                })
                
                # 最大100件まで
                if len(commit_logs) >= 100:
                    break
                
                time.sleep(0.05)  # API rate limit対策
            
            return commit_logs
            
        except Exception as e:
            print(f"ファイル履歴取得エラー {file_path}: {e}")
            return []

    def get_file_line_count(self, file_path, commit_sha):
        """ファイルの行数を取得"""
        try:
            # 特定のコミットでのファイル内容を取得
            content = self.repo.get_contents(file_path, ref=commit_sha)
            if content.encoding == 'base64':
                import base64
                decoded_content = base64.b64decode(content.content).decode('utf-8', errors='ignore')
                return len(decoded_content.splitlines())
            return 0
        except Exception as e:
            print(f"ファイル行数取得エラー {file_path}: {e}")
            return 0

    @retry_with_network_check
    def get_file_creation_info(self, file_path):
        """ファイルの作成情報を取得（最初のコミット）"""
        try:
            commits = self.repo.get_commits(path=file_path)
            commit_list = list(commits)
            if commit_list:
                # 最後のコミット（最初のコミット）を取得
                first_commit = commit_list[-1]
                author_name = first_commit.commit.author.name or "Unknown"
                
                # コミットアカウントのみ取得（author + committer）
                all_authors = [author_name]
                
                # committerも追加（authorと異なる場合）
                if first_commit.commit.committer and first_commit.commit.committer.name:
                    committer_name = first_commit.commit.committer.name
                    if committer_name != author_name and committer_name not in all_authors:
                        all_authors.append(committer_name)
                
                return {
                    'author_name': author_name,
                    'all_authors': all_authors,  # 全作成者リスト
                    'all_creator_names': all_authors,  # CSV出力用（ファイル作成者名）
                    'creation_date': first_commit.commit.author.date.isoformat(),
                    'commit_count': len(commit_list)
                }
            return None
        except Exception as e:
            print(f"ファイル作成情報取得エラー {file_path}: {e}")
            return None

    def get_files_by_author_type(self, df, target_ai_count=10, target_human_count=10):
        """AI/Humanファイル選択（ランダムサンプリング版）"""
        # AI作成ファイルと人間作成ファイルを分離
        ai_df = df[df['author_type'] == 'AI'].copy()
        human_df = df[df['author_type'] == 'Human'].copy()
        
        # ランダムサンプリング
        ai_files = []
        human_files = []
        
        # AI作成ファイルをランダムに選択
        if len(ai_df) > 0:
            sample_size_ai = min(target_ai_count, len(ai_df))
            ai_sampled = ai_df.sample(n=sample_size_ai, random_state=None)  # random_state=Noneで毎回異なる
            
            for _, row in ai_sampled.iterrows():
                ai_files.append({
                    'commit_hash': row['commit_hash'],
                    'added_file': row['added_file'],
                    'author_type': row['author_type'],
                    'ai_tool': row['ai_tool']
                })
        
        # 人間作成ファイルをランダムに選択
        if len(human_df) > 0:
            sample_size_human = min(target_human_count, len(human_df))
            human_sampled = human_df.sample(n=sample_size_human, random_state=None)
            
            for _, row in human_sampled.iterrows():
                human_files.append({
                    'commit_hash': row['commit_hash'],
                    'added_file': row['added_file'],
                    'author_type': row['author_type'],
                    'ai_tool': row['ai_tool']
                })
        
        # 同数に調整（数が小さい方合わせる）
        min_count = min(len(ai_files), len(human_files))
        ai_files = ai_files[:min_count]
        human_files = human_files[:min_count]
        
        print(f"ファイル数調整: AI={len(ai_files)} Human={len(human_files)} (同数に調整)")
        
        return ai_files + human_files

    def step2_find_commit_changed_files(self, df):
        """ステップ2: コミット履歴分析（API版）"""
        print("\n=== ステップ2: コミット履歴分析 (API版) ===")
        
        selected_files = self.get_files_by_author_type(df)
        ai_count = sum(1 for f in selected_files if f['author_type'] == 'AI')
        print(f"選択ファイル: {len(selected_files)} (AI:{ai_count} Human:{len(selected_files)-ai_count})")
        
        # ファイル情報記録用
        file_info_records = []
        
        results = []
        for idx, file_info in enumerate(selected_files):
            print(f"処理中: {idx+1}/{len(selected_files)} - {file_info['added_file']}")
            
            file_path = file_info['added_file']
            commit_hash = file_info['commit_hash']
            author_type = file_info['author_type']
            
            # ファイル作成情報を取得
            creation_info = self.get_file_creation_info(file_path)
            if creation_info:
                line_count = self.get_file_line_count(file_path, commit_hash)
                
                # ファイル情報を記録
                file_info_records.append({
                    'repository_name': self.repo_name_full,
                    'file_name': file_path,
                    'all_creator_names': creation_info['all_creator_names'],  # 全作成者名リスト
                    'line_count': line_count,
                    'created_by': author_type,
                    'creation_date': creation_info['creation_date'],
                    'commit_count': creation_info['commit_count']
                })
            else:
                # 情報取得失敗時も記録（エラーとしてマーク）
                print(f"  警告: ファイル情報取得失敗 - {file_path}")
                file_info_records.append({
                    'repository_name': self.repo_name_full,
                    'file_name': file_path,
                    'all_creator_names': [],
                    'line_count': 0,
                    'created_by': author_type,
                    'creation_date': '',
                    'commit_count': 0
                })
            
            commit_logs = self.get_file_commits_api(file_path)
            
            if not commit_logs:
                results.append({
                    'original_commit_type': author_type,
                    'original_commit_hash': commit_hash,
                    'file_path': file_path,
                    'commit_hash': 'No commits found',
                    'commit_date': '',
                    'author': '',
                    'all_authors': [],
                    'commit_message': '',
                    'is_ai_generated': False,
                    'ai_type': 'N/A',
                    'ai_tool': 'N/A'
                })
            else:
                for log in commit_logs:
                    is_ai, ai_type = self.is_ai_generated_commit(log['all_authors'])
                    results.append({
                        'original_commit_type': author_type,
                        'original_commit_hash': commit_hash,
                        'file_path': file_path,
                        'commit_hash': log['hash'],
                        'commit_date': log['date'],
                        'author': log['author'],
                        'all_authors': log['all_authors'],  # 全作成者リスト
                        'commit_message': log['message'],
                        'is_ai_generated': is_ai,
                        'ai_type': ai_type,
                        'ai_tool': self.detect_specific_ai_tool(log['all_authors']) if is_ai else 'N/A'
                    })
        
        # ファイル情報をインスタンス変数として保存
        self.file_info_records = file_info_records
        
        return pd.DataFrame(results) if results else None

    def prepare_prompt(self, commit_message: str, git_diff: str, context_window: int = 1024):
        """コミット分類用プロンプト作成"""
        prompt_head = "<s>[INST] <<SYS>>\nYou are a commit classifier based on commit message and code diff.Please classify the given commit into one of the ten categories: docs, perf, style, refactor, feat, fix, test, ci, build, and chore. The definitions of each category are as follows:\n**feat**: Code changes aim to introduce new features to the codebase, encompassing both internal and user-oriented features.\n**fix**: Code changes aim to fix bugs and faults within the codebase.\n**perf**: Code changes aim to improve performance, such as enhancing execution speed or reducing memory consumption.\n**style**: Code changes aim to improve readability without affecting the meaning of the code. This type encompasses aspects like variable naming, indentation, and addressing linting or code analysis warnings.\n**refactor**: Code changes aim to restructure the program without changing its behavior, aiming to improve maintainability. To avoid confusion and overlap, we propose the constraint that this category does not include changes classified as ``perf'' or ``style''. Examples include enhancing modularity, refining exception handling, improving scalability, conducting code cleanup, and removing deprecated code.\n**docs**: Code changes that modify documentation or text, such as correcting typos, modifying comments, or updating documentation.\n**test**: Code changes that modify test files, including the addition or updating of tests.\n**ci**: Code changes to CI (Continuous Integration) configuration files and scripts, such as configuring or updating CI/CD scripts, e.g., ``.travis.yml'' and ``.github/workflows''.\n**build**: Code changes affecting the build system (e.g., Maven, Gradle, Cargo). Change examples include updating dependencies, configuring build configurations, and adding scripts.\n**chore**: Code changes for other miscellaneous tasks that do not neatly fit into any of the above categories.\n<</SYS>>\n\n"
        prompt_head_encoded = tokenizer.encode(prompt_head, add_special_tokens=False)

        prompt_message = f"- given commit message:\n{commit_message}\n"
        prompt_message_encoded = tokenizer.encode(prompt_message, max_length=64, truncation=True, add_special_tokens=False)

        prompt_diff = f"- given commit diff: \n{git_diff}\n"
        remaining_length = (context_window - len(prompt_head_encoded) - len(prompt_message_encoded) - 6)
        prompt_diff_encoded = tokenizer.encode(prompt_diff, max_length=remaining_length, truncation=True, add_special_tokens=False)

        prompt_end = tokenizer.encode(" [/INST]", add_special_tokens=False)
        return tokenizer.decode(prompt_head_encoded + prompt_message_encoded + prompt_diff_encoded + prompt_end)

    def classify_commit(self, commit_message: str, git_diff: str, context_window: int = 1024):
        """コミット分類"""
        if not pipe or not tokenizer:
            return "model_not_available"

        try:
            prompt = self.prepare_prompt(commit_message, git_diff, context_window)
            result = pipe(prompt, max_new_tokens=10, pad_token_id=pipe.tokenizer.eos_token_id)
            label = result[0]["generated_text"].split()[-1]
            return label
        except Exception as e:
            print(f"分類エラー: {e}")
            return "classification_error"

    def fetch_message_and_diff(self, commit_sha):
        """GitHub API経由でコミット情報取得"""
        try:
            commit = self.repo.get_commit(commit_sha)
            
            if commit.parents:
                parent_sha = commit.parents[0].sha
                diff_url = self.repo.compare(parent_sha, commit_sha).diff_url
                return commit.commit.message, requests.get(diff_url).text
            return commit.commit.message, ""
        except Exception as e:
            print(f"GitHub取得エラー: {e}")
            return None, None

    def get_commit_changed_lines(self, commit_sha):
        """コミットの変更行数を取得"""
        try:
            commit = self.repo.get_commit(commit_sha)
            return commit.stats.additions + commit.stats.deletions
        except Exception as e:
            print(f"変更行数取得エラー {commit_sha[:8]}: {e}")
            return 0

    def step3_classify_commits(self, df):
        """ステップ3: コミット分類"""
        print("\n=== ステップ3: コミット分類 ===")
        
        if not pipe:
            print("分類モデル利用不可 - 分類スキップ")
            df['classification_label'] = 'not_classified'
            return df
        
        results = []
        total = len(df)
        
        try:
            for idx, row in df.iterrows():
                print(f"進捗: {idx}/{total} ({idx/total*100:.0f}%)")
                
                commit_sha = row['commit_hash']
                base_result = {
                    'original_commit_type': row['original_commit_type'],
                    'commit_hash': commit_sha,
                    'file_path': row['file_path'],
                    'commit_date': row['commit_date'],
                    'author': row['author'],
                    'is_ai_generated': row['is_ai_generated'],
                    'ai_tool': row.get('ai_tool', 'N/A'),
                    'commit_message': row['commit_message']
                }
                
                if commit_sha == 'No commits found':
                    base_result['classification_label'] = 'no_commits'
                else:
                    try:
                        message, diff = self.fetch_message_and_diff(commit_sha)
                        base_result['classification_label'] = self.classify_commit(message, diff) if message and diff else 'fetch_error'
                    except Exception as e:
                        print(f"エラー {commit_sha[:8]}: {e}")
                        base_result['classification_label'] = 'error'
                
                results.append(base_result)
            
            print("分類処理完了")
            return pd.DataFrame(results)
            
        except Exception as e:
            print(f"\n✗✗✗ 致命的エラー（Segmentation fault等）: {type(e).__name__} ✗✗✗")
            print(f"詳細: {str(e)}")
            print("このリポジトリをスキップします")
            return None

    def analyze_subset(self, subset_df, label):
        """サブセット分析（日本語出力）"""
        if len(subset_df) == 0:
            return [f"{label} コミットが見つかりませんでした"]
        
        analysis = [f"{label.upper()} コミット分析", "-" * 30]
        
        # 1. ファイル統計
        commits_per_file = subset_df.groupby('file_path').size()
        analysis.extend([
            f"1. ファイルごとのコミット数: 平均={commits_per_file.mean():.2f} 標準偏差={commits_per_file.std():.2f} 最小={commits_per_file.min()} 最大={commits_per_file.max()}",
            ""
        ])
        
        # 2. 分類ラベル分布
        analysis.append("2. 分類ラベルの分布:")
        overall_labels = subset_df['classification_label'].value_counts()
        for lbl, count in overall_labels.items():
            analysis.append(f"   {lbl}: {count}件 ({count/len(subset_df)*100:.1f}%)")
        analysis.append("")
        
        # 3. コミット頻度分析
        analysis.append("3. コミット頻度分析:")
        file_frequencies = []
        for file_path in subset_df['file_path'].unique():
            file_commits = subset_df[subset_df['file_path'] == file_path].copy()
            file_commits['commit_date'] = pd.to_datetime(file_commits['commit_date'])
            if len(file_commits) > 1:
                dates = file_commits['commit_date'].sort_values()
                time_diffs = [(dates.iloc[i] - dates.iloc[i-1]).days 
                            for i in range(1, len(dates)) if (dates.iloc[i] - dates.iloc[i-1]).days > 0]
                if time_diffs:
                    file_frequencies.extend(time_diffs)
        
        if file_frequencies:
            analysis.append(f"   平均間隔: {np.mean(file_frequencies):.1f}日 (標準偏差: {np.std(file_frequencies):.1f})")
        else:
            analysis.append("   頻度分析に十分なデータがありません")
        analysis.append("")
        
        # 4. AI判定統計
        ai_count = len(subset_df[subset_df['is_ai_generated'] == True])
        analysis.extend([
            f"4. 作成者: AI={ai_count}件 ({ai_count/len(subset_df)*100:.1f}%) 人間={len(subset_df)-ai_count}件 ({(len(subset_df)-ai_count)/len(subset_df)*100:.1f}%)",
            ""
        ])
        
        # 5. AIツール/モデルの分布（AI起源の場合のみ）
        if label == "AI起源" and 'ai_tool' in subset_df.columns:
            analysis.append("5. 使用されたAIツール/モデルの分布:")
            first_commits = subset_df.drop_duplicates(subset=['file_path'], keep='first')
            ai_tool_counts = first_commits['ai_tool'].value_counts()
            for tool, count in ai_tool_counts.items():
                if tool != 'N/A':
                    analysis.append(f"   {tool}: {count}件 ({count/len(first_commits)*100:.1f}%)")
            analysis.append("")
        
        return analysis

    def step4_analyze_commit_data(self, df):
        """ステップ4: データ分析（日本語出力）"""
        print("\n=== ステップ4: データ分析 ===")
        
        df['commit_date'] = pd.to_datetime(df['commit_date'])
        ai_df = df[df['original_commit_type'] == 'AI']
        human_df = df[df['original_commit_type'] == 'Human']
        
        # 統計結果構築
        ai_generated = len(df[df['is_ai_generated'] == True])
        results = [
            f"{self.repo_name} コミット分析結果", "=" * 50, "",
            "全体統計", "-" * 20,
            f"総コミット数: {len(df)}件",
            f"AI起源: {len(ai_df)}件 ({len(ai_df)/len(df)*100:.1f}%)",
            f"人間起源: {len(human_df)}件 ({len(human_df)/len(df)*100:.1f}%)",
            f"ユニークファイル数: {df['file_path'].nunique()}件",
            f"AI生成コミット: {ai_generated}件 ({ai_generated/len(df)*100:.1f}%)", ""
        ]
        
        # サブセット分析
        results.extend(self.analyze_subset(ai_df, "AI起源"))
        results.extend(self.analyze_subset(human_df, "人間起源"))
        
        # 比較分析
        if len(ai_df) > 0 and len(human_df) > 0:
            ai_cpf = ai_df.groupby('file_path').size()
            human_cpf = human_df.groupby('file_path').size()
            results.extend([
                "比較分析", "-" * 20,
                f"ファイルごとの平均コミット数 - AI: {ai_cpf.mean():.2f}件 人間: {human_cpf.mean():.2f}件",
                f"最も活発なファイル - AI: {ai_cpf.idxmax()} ({ai_cpf.max()}件) 人間: {human_cpf.idxmax()} ({human_cpf.max()}件)"
            ])
        
        # ファイル保存
        output_file = os.path.join(self.final_output_dir, f"{self.repo_name}_commit_analysis_results_properly.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(results))
        
        print(f"分析完了: {output_file}")
        print("\n".join(results[:10]) + "\n...")
        return results
    
    def save_individual_analysis(self, df, output_file):
        """個別リポジトリの詳細分析をTXTファイルに保存"""
        df['commit_date'] = pd.to_datetime(df['commit_date'])
        ai_df = df[df['original_commit_type'] == 'AI']
        human_df = df[df['original_commit_type'] == 'Human']
        
        results = [
            "=" * 80,
            f"{self.repo_name} - 個別リポジトリ分析結果",
            "=" * 80,
            "",
            f"リポジトリ: {self.repo_name_full}",
            f"スター数: {self.repo.stargazers_count:,}",
            f"分析日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
            "",
            "=" * 80,
            "■ 基本統計",
            "-" * 40,
            f"総コミット数: {len(df)}件",
            f"AI作成ファイルへのコミット: {len(ai_df)}件 ({len(ai_df)/len(df)*100:.1f}%)",
            f"人間作成ファイルへのコミット: {len(human_df)}件 ({len(human_df)/len(df)*100:.1f}%)",
            f"ユニークファイル数: {df['file_path'].nunique()}件",
            "",
        ]
        
        # AI作成ファイルの統計
        if len(ai_df) > 0:
            results.extend([
                "■ AI作成ファイルの統計",
                "-" * 40,
                f"ファイル数: {ai_df['file_path'].nunique()}件",
                f"総コミット数: {len(ai_df)}件",
                ""
            ])
            
            # コミット作成者の内訳
            ai_origin_ai = len(ai_df[ai_df['is_ai_generated'] == True])
            ai_origin_human = len(ai_df[ai_df['is_ai_generated'] == False])
            results.extend([
                "コミット作成者:",
                f"  AI: {ai_origin_ai}件 ({ai_origin_ai/len(ai_df)*100:.1f}%)",
                f"  人間: {ai_origin_human}件 ({ai_origin_human/len(ai_df)*100:.1f}%)",
                ""
            ])
            
            # コミット分類
            results.append("コミット分類:")
            for label, count in ai_df['classification_label'].value_counts().head(10).items():
                results.append(f"  {label}: {count}件 ({count/len(ai_df)*100:.1f}%)")
            results.append("")
        
        # 人間作成ファイルの統計
        if len(human_df) > 0:
            results.extend([
                "■ 人間作成ファイルの統計",
                "-" * 40,
                f"ファイル数: {human_df['file_path'].nunique()}件",
                f"総コミット数: {len(human_df)}件",
                ""
            ])
            
            # コミット作成者の内訳
            human_origin_ai = len(human_df[human_df['is_ai_generated'] == True])
            human_origin_human = len(human_df[human_df['is_ai_generated'] == False])
            results.extend([
                "コミット作成者:",
                f"  AI: {human_origin_ai}件 ({human_origin_ai/len(human_df)*100:.1f}%)",
                f"  人間: {human_origin_human}件 ({human_origin_human/len(human_df)*100:.1f}%)",
                ""
            ])
            
            # コミット分類
            results.append("コミット分類:")
            for label, count in human_df['classification_label'].value_counts().head(10).items():
                results.append(f"  {label}: {count}件 ({count/len(human_df)*100:.1f}%)")
            results.append("")
        
        # ファイルに保存
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(results))

    def save_detailed_results_to_csv(self, df_classified):
        """全コミット情報を詳細CSVに保存（累積更新版）"""
        print("\n--- 詳細結果CSV保存中 ---")
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(script_dir, "../data_list/RQ1/final_result/result_v3.csv")
        
        # CSVデータを作成
        csv_records = []
        
        for _, row in df_classified.iterrows():
            file_path = row['file_path']
            
            # ファイル情報を取得
            file_info = None
            if hasattr(self, 'file_info_records'):
                for record in self.file_info_records:
                    if record['file_name'] == file_path:
                        file_info = record
                        break
            
            # コミットの変更行数を取得
            changed_lines = 0
            if row['commit_hash'] != 'No commits found':
                changed_lines = self.get_commit_changed_lines(row['commit_hash'])
            
            # ファイル作成者名を取得（全アカウント）
            file_creator_names = ''
            if file_info and 'all_creator_names' in file_info:
                file_creator_names = ', '.join(file_info['all_creator_names'])
            
            # コミット作成者名を取得（全アカウント）
            commit_author_names = ''
            if 'all_authors' in row and row['all_authors']:
                if isinstance(row['all_authors'], list):
                    commit_author_names = ', '.join(row['all_authors'])
                else:
                    commit_author_names = str(row['all_authors'])
            
            csv_records.append({
                'repository_name': self.repo_name_full,
                'file_name': file_path,
                'file_created_by': row['original_commit_type'],
                'file_creator_names': file_creator_names,
                'file_line_count': file_info['line_count'] if file_info else 0,
                'file_creation_date': file_info['creation_date'] if file_info else '',
                'file_commit_count': file_info['commit_count'] if file_info else 0,
                'commit_message': row['commit_message'],
                'commit_created_by': 'AI' if row['is_ai_generated'] else 'Human',
                'commit_author_names': commit_author_names,
                'commit_changed_lines': changed_lines,
                'commit_date': row['commit_date']
            })
        
        new_df = pd.DataFrame(csv_records)
        
        # 既存のCSVがあれば読み込んで結合
        if os.path.exists(csv_path):
            existing_df = pd.read_csv(csv_path)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
        
        # CSVに保存
        combined_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"✓ 詳細結果CSV保存完了: {csv_path}")
        print(f"  今回追加: {len(new_df)}件, 合計: {len(combined_df)}件")

    def save_files_info_to_csv(self):
        """ファイル情報をCSVに保存（累積更新版）"""
        if not hasattr(self, 'file_info_records') or not self.file_info_records:
            print("保存するファイル情報がありません")
            return
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(script_dir, "../data_list/RQ1/final_result/RQ1_files_properly.csv")
        
        # 新しいデータをDataFrameに変換
        new_df = pd.DataFrame(self.file_info_records)
        
        # 既存のCSVがあれば読み込んで結合
        if os.path.exists(csv_path):
            existing_df = pd.read_csv(csv_path)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
        
        # CSVに保存
        combined_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"✓ ファイル情報をCSVに保存: {csv_path}")
        print(f"  今回追加: {len(new_df)}件, 合計: {len(combined_df)}件")

    def run_full_analysis(self):
        """全分析実行（API版）- エラーハンドリング強化版"""
        print(f"=== RQ1分析開始 (API版): {self.repo_name_full} ===")
        
        try:
            # step1: ファイル追加分析
            print("\n--- ステップ1: ファイル追加分析 ---")
            df_additions, step1_status = self.step1_find_added_files()
            if df_additions is None or len(df_additions) == 0:
                if step1_status == 'no_commits_90days':
                    print("⚠ ステップ1失敗: 90日以前のコミットが存在しません")
                    return None, 'no_commits_90days'
                elif step1_status == 'no_file_additions':
                    print("⚠ ステップ1失敗: ファイル追加コミットが見つかりませんでした")
                    return None, 'no_file_additions'
                else:
                    print("⚠ ステップ1失敗: データが取得できませんでした")
                    return None, 'step1_failed'
            
            print(f"✓ ステップ1完了: {len(df_additions)}件のファイル追加を検出")
            
            # AI作成ファイルが見つからなかった場合
            if step1_status == 'no_ai_files':
                print("⚠ 警告: AI作成ファイルが見つかりませんでした")
                return None, 'no_ai_files'
            
            # step2: コミット履歴分析
            print("\n--- ステップ2: コミット履歴分析 ---")
            df_history = self.step2_find_commit_changed_files(df_additions)
            if df_history is None or len(df_history) == 0:
                print("⚠ ステップ2: コミット履歴が取得できませんでした")
                return None, 'step2_failed'
            
            print(f"✓ ステップ2完了: {len(df_history)}件のコミット履歴を取得")
            
            # step3: コミット分類
            print("\n--- ステップ3: コミット分類 ---")
            df_classified = self.step3_classify_commits(df_history)
            if df_classified is None or len(df_classified) == 0:
                print("⚠ ステップ3: コミット分類ができませんでした")
                return None, 'step3_failed'
            
            print(f"✓ ステップ3完了: {len(df_classified)}件のコミットを分類")
            
            # 詳細結果をCSVに保存（全コミット情報）
            print("\n--- 詳細結果のCSV保存 ---")
            self.save_detailed_results_to_csv(df_classified)
            
            # 個別レポートは出力せず、統合分析でまとめて出力
            print(f"\n✓✓✓ 完了: {self.repo_name} ✓✓✓")
            
            # 結果を返す
            return {
                'df_additions': df_additions,
                'df_history': df_history,
                'df_classified': df_classified
            }, 'success'
            
        except Exception as e:
            print(f"\n✗✗✗ 予期しないエラー発生: {self.repo_name_full} ✗✗✗")
            print(f"エラー詳細: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, f'exception: {type(e).__name__}'


def analyze_multiple_repositories(repo_list, start_index=0, num_repos=3):
    """複数リポジトリの分析を実行 - 成功数ベース版"""
    github_token = os.getenv("GITHUB_TOKEN")
    
    if not github_token:
        print("エラー: GitHub tokenが設定されていません")
        print(".envファイルにGITHUB_TOKENを設定してください")
        return
    
    print(f"=" * 80)
    print(f"RQ1 複数リポジトリ分析 (GitHub API版)")
    print(f"=" * 80)
    print(f"開始位置: {start_index + 1}番目のリポジトリから")
    print(f"目標分析数: {num_repos}リポジトリ（成功基準）")
    print(f"GitHub API: OK")
    print(f"=" * 80)
    
    start_time = datetime.now()
    all_results = []
    all_classifications = []
    failed_repos = []
    
    # 成功したリポジトリがnum_repos個になるまで続ける
    idx = start_index
    while len(all_results) < num_repos and idx < len(repo_list):
        repo_info = repo_list[idx]
        repo_name_full = f"{repo_info['owner']}/{repo_info['repository_name']}"
        
        print(f"\n{'='*80}")
        print(f"[試行: {idx+1}] [成功: {len(all_results)}/{num_repos}] {repo_name_full}")
        print(f"スター数: {repo_info['stars']:,}")
        print(f"{'='*80}")
        
        try:
            # RQ1Analyzerの初期化
            print("リポジトリに接続中...")
            analyzer = RQ1AnalyzerAPI(repo_name_full, github_token)
            
            # 分析実行
            result, status = analyzer.run_full_analysis()
            
            if result is not None:
                all_results.append({
                    'repo': repo_name_full,
                    'stars': repo_info['stars'],
                    'analyzer': analyzer,
                    'data': result
                })
                all_classifications.append(result['df_classified'])
                print(f"\n✓✓✓ [成功: {len(all_results)}/{num_repos}] {repo_name_full} 分析成功 ✓✓✓")
                
                # ここまでの全リポジトリの統合分析を出力
                print(f"\n--- 統合分析レポート更新中 ({len(all_results)}件のリポジトリ) ---")
                elapsed_time = datetime.now() - start_time
                generate_combined_analysis(all_results, all_classifications, elapsed_time, failed_repos)
                print(f"✓ 統合分析レポート更新完了")
            else:
                # 失敗理由を詳細に記録
                reason_map = {
                    'no_commits_90days': '90日以前のコミットが存在しない',
                    'no_file_additions': '90日以前にファイル追加コミットなし',
                    'no_ai_files': 'AI作成ファイルが見つからない',
                    'step1_failed': 'ステップ1失敗',
                    'step2_failed': 'ステップ2失敗',
                    'step3_failed': 'ステップ3失敗'
                }
                reason = reason_map.get(status, status)
                
                failed_repos.append({
                    'repo': repo_name_full,
                    'stars': repo_info['stars'],
                    'reason': reason
                })
                print(f"\n✗✗✗ {repo_name_full} 分析失敗: {reason} ✗✗✗")
                print(f"→ 次のリポジトリに進みます... (残り成功必要数: {num_repos - len(all_results)})")
                
        except Exception as e:
            failed_repos.append({
                'repo': repo_name_full,
                'stars': repo_info['stars'],
                'reason': f'{type(e).__name__}: {str(e)}'
            })
            print(f"\n✗✗✗ {repo_name_full} エラー発生 ✗✗✗")
            print(f"エラー詳細: {type(e).__name__}: {str(e)}")
            print(f"→ 次のリポジトリに進みます... (残り成功必要数: {num_repos - len(all_results)})")
        
        idx += 1
    
    # 結果サマリー
    print(f"\n{'='*80}")
    print("分析結果サマリー")
    print(f"{'='*80}")
    print(f"成功: {len(all_results)}件（目標: {num_repos}件）")
    print(f"失敗: {len(failed_repos)}件")
    print(f"試行総数: {idx}件")
    
    if len(all_results) < num_repos:
        print(f"\n⚠ 警告: 目標の{num_repos}件に達しませんでした（リポジトリリスト不足）")
    
    if failed_repos:
        print(f"\n失敗したリポジトリ:")
        for failed in failed_repos:
            print(f"  - {failed['repo']}: {failed['reason']}")
    
    total_time = datetime.now() - start_time
    print(f"\n{'='*80}")
    print(f"総処理時間: {total_time}")
    print(f"{'='*80}")


def generate_combined_analysis(all_results, all_classifications, elapsed_time, failed_repos=None):
    """複数リポジトリの統合分析結果を生成（累積更新版）"""
    print("\n=== 統合分析結果生成中 ===")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "../data_list/RQ1/final_result")
    # ファイル名を固定して上書き更新
    output_file = os.path.join(output_dir, f"results_v3.txt")
    
    # 全データを統合
    combined_df = pd.concat(all_classifications, ignore_index=True)
    
    # 経過時間を文字列に変換
    hours, remainder = divmod(elapsed_time.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    time_str = f"{hours}時間{minutes}分{seconds}秒" if hours > 0 else f"{minutes}分{seconds}秒"
    
    # 総リポジトリ数（成功+失敗）
    total_repos = len(all_results) + (len(failed_repos) if failed_repos else 0)
    
    results = [
        "=" * 80,
        "複数リポジトリ統合分析結果",
        "=" * 80,
        "",
        "■ 分析概要",
        "-" * 40,
        f"分析日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
        f"分析対象リポジトリ数: {total_repos}件",
        f"分析成功リポジトリ数: {len(all_results)}件",
        f"分析失敗リポジトリ数: {len(failed_repos) if failed_repos else 0}件",
        f"総コミット数: {len(combined_df)}件",
        f"分析所要時間: {time_str}",
        ""
    ]
    
    # 失敗したリポジトリがある場合は記載
    if failed_repos and len(failed_repos) > 0:
        results.extend([
            "■ 分析失敗リポジトリ",
            "-" * 40
        ])
        for failed in failed_repos:
            results.append(f"× {failed['repo']}")
            results.append(f"  理由: {failed['reason']}")
        results.append("")
    
    # 統計サマリー
    total_ai = len(combined_df[combined_df['original_commit_type'] == 'AI'])
    total_human = len(combined_df[combined_df['original_commit_type'] == 'Human'])
    total_ai_generated = len(combined_df[combined_df['is_ai_generated'] == True])
    
    # AI/人間別のデータフレーム
    ai_df = combined_df[combined_df['original_commit_type'] == 'AI'].copy()
    human_df = combined_df[combined_df['original_commit_type'] == 'Human'].copy()
    
    # 日付をdatetime型に変換
    ai_df['commit_date'] = pd.to_datetime(ai_df['commit_date'])
    human_df['commit_date'] = pd.to_datetime(human_df['commit_date'])
    
    results.extend([
        "■ 全体統計",
        "-" * 40,
        f"総ファイル数: {combined_df['file_path'].nunique()}件",
        f"AI起源コミット（AI作成ファイルに対するコミット）: {total_ai}件 ({total_ai/len(combined_df)*100:.1f}%)",
        f"人間起源コミット（人間作成ファイルに対するコミット）: {total_human}件 ({total_human/len(combined_df)*100:.1f}%)",
        f"AI生成判定コミット: {total_ai_generated}件 ({total_ai_generated/len(combined_df)*100:.1f}%)",
        ""
    ])
    
    # AI作成ファイルの統計
    results.extend([
        "■ AI作成ファイルの統計",
        "-" * 40
    ])
    
    if len(ai_df) > 0:
        ai_unique_files = ai_df['file_path'].nunique()
        ai_commits_per_file = ai_df.groupby('file_path').size()
        
        # AI作成ファイルに対するコミットの作成者分析
        ai_origin_ai_commits = len(ai_df[ai_df['is_ai_generated'] == True])
        ai_origin_human_commits = len(ai_df[ai_df['is_ai_generated'] == False])
        
        results.extend([
            f"ファイル数: {ai_unique_files}件",
            f"総コミット数: {len(ai_df)}件",
            "",
            "コミット作成者の内訳:",
            f"  AIによるコミット: {ai_origin_ai_commits}件 ({ai_origin_ai_commits/len(ai_df)*100:.1f}%)",
            f"  人間によるコミット: {ai_origin_human_commits}件 ({ai_origin_human_commits/len(ai_df)*100:.1f}%)",
            "",
            f"1ファイルあたりの平均コミット数: {ai_commits_per_file.mean():.2f}件",
            f"1ファイルあたりの最小コミット数: {ai_commits_per_file.min()}件",
            f"1ファイルあたりの最大コミット数: {ai_commits_per_file.max()}件",
            f"1ファイルあたりの中央値コミット数: {ai_commits_per_file.median():.1f}件",
            ""
        ])
        
        # コミット頻度分析（AI）- 期間あたりのコミット回数
        ai_commit_rates = {
            '1week': [],
            '2weeks': [],
            '1month': [],
            '3months': []
        }
        
        for file_path in ai_df['file_path'].unique():
            file_commits = ai_df[ai_df['file_path'] == file_path].copy()
            if len(file_commits) > 0:
                dates = file_commits['commit_date'].sort_values()
                first_date = dates.iloc[0]
                last_date = dates.iloc[-1]
                total_days = (last_date - first_date).days
                
                if total_days > 0:
                    total_commits = len(file_commits)
                    
                    # 各期間でのコミット回数を計算
                    ai_commit_rates['1week'].append(total_commits / (total_days / 7.0))
                    ai_commit_rates['2weeks'].append(total_commits / (total_days / 14.0))
                    ai_commit_rates['1month'].append(total_commits / (total_days / 30.0))
                    ai_commit_rates['3months'].append(total_commits / (total_days / 90.0))
        
        if ai_commit_rates['1week']:
            results.extend([
                "コミット頻度（期間あたりのコミット回数）:",
                "  [1週間あたり]",
                f"    平均: {np.mean(ai_commit_rates['1week']):.2f}回",
                f"    中央値: {np.median(ai_commit_rates['1week']):.2f}回",
                f"    最小: {np.min(ai_commit_rates['1week']):.2f}回",
                f"    最大: {np.max(ai_commit_rates['1week']):.2f}回",
                f"    標準偏差: {np.std(ai_commit_rates['1week']):.2f}回",
                "  [2週間あたり]",
                f"    平均: {np.mean(ai_commit_rates['2weeks']):.2f}回",
                f"    中央値: {np.median(ai_commit_rates['2weeks']):.2f}回",
                "  [1ヶ月あたり]",
                f"    平均: {np.mean(ai_commit_rates['1month']):.2f}回",
                f"    中央値: {np.median(ai_commit_rates['1month']):.2f}回",
                "  [3ヶ月あたり]",
                f"    平均: {np.mean(ai_commit_rates['3months']):.2f}回",
                f"    中央値: {np.median(ai_commit_rates['3months']):.2f}回",
                ""
            ])
        else:
            results.append("コミット頻度: データ不足\n")
        
        # AI作成ファイルのコミット分類
        results.append("コミット分類の分布:")
        ai_labels = ai_df['classification_label'].value_counts()
        for label, count in ai_labels.items():
            results.append(f"  {label}: {count}件 ({count/len(ai_df)*100:.1f}%)")
        results.append("")
    else:
        results.extend(["データなし", ""])
    
    # 人間作成ファイルの統計
    results.extend([
        "■ 人間作成ファイルの統計",
        "-" * 40
    ])
    
    if len(human_df) > 0:
        human_unique_files = human_df['file_path'].nunique()
        human_commits_per_file = human_df.groupby('file_path').size()
        
        # 人間作成ファイルに対するコミットの作成者分析
        human_origin_ai_commits = len(human_df[human_df['is_ai_generated'] == True])
        human_origin_human_commits = len(human_df[human_df['is_ai_generated'] == False])
        
        results.extend([
            f"ファイル数: {human_unique_files}件",
            f"総コミット数: {len(human_df)}件",
            "",
            "コミット作成者の内訳:",
            f"  AIによるコミット: {human_origin_ai_commits}件 ({human_origin_ai_commits/len(human_df)*100:.1f}%)",
            f"  人間によるコミット: {human_origin_human_commits}件 ({human_origin_human_commits/len(human_df)*100:.1f}%)",
            "",
            f"1ファイルあたりの平均コミット数: {human_commits_per_file.mean():.2f}件",
            f"1ファイルあたりの最小コミット数: {human_commits_per_file.min()}件",
            f"1ファイルあたりの最大コミット数: {human_commits_per_file.max()}件",
            f"1ファイルあたりの中央値コミット数: {human_commits_per_file.median():.1f}件",
            ""
        ])
        
        # コミット頻度分析（人間）- 期間あたりのコミット回数
        human_commit_rates = {
            '1week': [],
            '2weeks': [],
            '1month': [],
            '3months': []
        }
        
        for file_path in human_df['file_path'].unique():
            file_commits = human_df[human_df['file_path'] == file_path].copy()
            if len(file_commits) > 0:
                dates = file_commits['commit_date'].sort_values()
                first_date = dates.iloc[0]
                last_date = dates.iloc[-1]
                total_days = (last_date - first_date).days
                
                if total_days > 0:
                    total_commits = len(file_commits)
                    
                    # 各期間でのコミット回数を計算
                    human_commit_rates['1week'].append(total_commits / (total_days / 7.0))
                    human_commit_rates['2weeks'].append(total_commits / (total_days / 14.0))
                    human_commit_rates['1month'].append(total_commits / (total_days / 30.0))
                    human_commit_rates['3months'].append(total_commits / (total_days / 90.0))
        
        if human_commit_rates['1week']:
            results.extend([
                "コミット頻度（期間あたりのコミット回数）:",
                "  [1週間あたり]",
                f"    平均: {np.mean(human_commit_rates['1week']):.2f}回",
                f"    中央値: {np.median(human_commit_rates['1week']):.2f}回",
                f"    最小: {np.min(human_commit_rates['1week']):.2f}回",
                f"    最大: {np.max(human_commit_rates['1week']):.2f}回",
                f"    標準偏差: {np.std(human_commit_rates['1week']):.2f}回",
                "  [2週間あたり]",
                f"    平均: {np.mean(human_commit_rates['2weeks']):.2f}回",
                f"    中央値: {np.median(human_commit_rates['2weeks']):.2f}回",
                "  [1ヶ月あたり]",
                f"    平均: {np.mean(human_commit_rates['1month']):.2f}回",
                f"    中央値: {np.median(human_commit_rates['1month']):.2f}回",
                "  [3ヶ月あたり]",
                f"    平均: {np.mean(human_commit_rates['3months']):.2f}回",
                f"    中央値: {np.median(human_commit_rates['3months']):.2f}回",
                ""
            ])
        else:
            results.append("コミット頻度: データ不足\n")
        
        # 人間作成ファイルのコミット分類
        results.append("コミット分類の分布:")
        human_labels = human_df['classification_label'].value_counts()
        for label, count in human_labels.items():
            results.append(f"  {label}: {count}件 ({count/len(human_df)*100:.1f}%)")
        results.append("")
    else:
        results.extend(["データなし", ""])
    
    # 全体のコミット分類の統計（参考）
    results.extend([
        "■ 全体のコミット分類の統計（参考）",
        "-" * 40
    ])
    label_counts = combined_df['classification_label'].value_counts()
    for label, count in label_counts.items():
        results.append(f"{label}: {count}件 ({count/len(combined_df)*100:.1f}%)")
    results.append("")
    
    # AI作成ファイルで使用されたAIツールの分析
    if len(ai_df) > 0:
        results.extend([
            "■ AI作成ファイルで使用されたAIツール",
            "-" * 40
        ])
        
        # 各ファイルの最初のコミット（ファイル作成時）のAIツールを取得
        first_commits = ai_df.drop_duplicates(subset=['file_path'], keep='first')
        tool_counts = first_commits['ai_tool'].value_counts()
        
        results.append(f"AI作成ファイル数: {len(first_commits)}件")
        results.append("")
        results.append("使用ツールの内訳:")
        for tool, count in tool_counts.items():
            if tool != 'N/A':
                results.append(f"  {tool}: {count}件 ({count/len(first_commits)*100:.1f}%)")
        results.append("")
    
    # リポジトリ別統計
    results.extend([
        "■ リポジトリ別サマリー",
        "-" * 40,
        ""
    ])
    
    for idx, result_info in enumerate(all_results):
        repo_name = result_info['repo']
        stars = result_info['stars']
        df = result_info['data']['df_classified']
        
        ai_count = len(df[df['original_commit_type'] == 'AI'])
        human_count = len(df[df['original_commit_type'] == 'Human'])
        ai_gen_count = len(df[df['is_ai_generated'] == True])
        
        results.extend([
            f"【{idx+1}】 {repo_name}",
            f"  スター数: {stars:,}",
            f"  総コミット数: {len(df)}件",
            f"  AI起源: {ai_count}件 ({ai_count/len(df)*100:.1f}%) / 人間起源: {human_count}件 ({human_count/len(df)*100:.1f}%)",
            f"  AI生成判定: {ai_gen_count}件 ({ai_gen_count/len(df)*100:.1f}%)",
            f"  ユニークファイル数: {df['file_path'].nunique()}件",
            ""
        ])
        
        # コミット分類分布
        results.append("  コミット分類:")
        repo_labels = df['classification_label'].value_counts().head(5)
        for label, count in repo_labels.items():
            results.append(f"    - {label}: {count}件 ({count/len(df)*100:.1f}%)")
        results.append("")
    
    # 比較分析
    results.extend([
        "■ リポジトリ間比較",
        "-" * 40,
        ""
    ])
    
    # AI率の比較
    results.append("AI起源コミット率:")
    for result_info in sorted(all_results, key=lambda x: len(x['data']['df_classified'][x['data']['df_classified']['original_commit_type'] == 'AI']) / len(x['data']['df_classified']), reverse=True):
        df = result_info['data']['df_classified']
        ai_rate = len(df[df['original_commit_type'] == 'AI']) / len(df) * 100
        results.append(f"  {result_info['repo']}: {ai_rate:.1f}%")
    results.append("")
    
    # ファイル保存
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(results))
    
    print(f"統合分析結果保存: {output_file}")
    print("\n".join(results[:30]) + "\n...")


def main():
    """メイン実行"""
    # CSVからリポジトリリスト読み込み
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "../dataset/repository_list.csv")
    
    print(f"リポジトリリスト読み込み: {csv_path}")
    repo_df = pd.read_csv(csv_path)
    repo_list = repo_df.to_dict('records')

    # 開始位置（上から何番目のリポジトリから始めるか）
    # 例: start_repo = 0 なら1番目から、start_repo = 100 なら101番目から開始
    start_repo = 0
    
    # 分析対象リポジトリ数
    num_repos = 100
    
    print(f"総リポジトリ数: {len(repo_list)}件")
    print(f"開始位置: {start_repo + 1}番目")
    print(f"分析対象: {num_repos}件")
    
    # 複数リポジトリ分析実行
    analyze_multiple_repositories(repo_list, start_repo, num_repos)


if __name__ == "__main__":
    main()
