"""
180日以前のコミット数カウントプログラム
機能: repository_listのリポジトリを上からチェックし、2025年1月1日から180日以前のコミット数を表示
"""

import os
import pandas as pd
from datetime import datetime, timedelta
import re
import time
from github import Github
from dotenv import load_dotenv
import json
import csv
import socket  # ネットワーク接続確認用

# srcフォルダ内の.envファイルを読み込む
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path)


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


class OldCommitCounter:
    """180日以前のコミット数をカウントするクラス"""
    
    def __init__(self, github_token):
        """初期化"""
        self.github_token = github_token
        if not self.github_token:
            raise ValueError("GitHub tokenが必要です。.envファイルにGITHUB_TOKENを設定してください。")
        
        self.g = Github(self.github_token)
        
        # 出力ディレクトリ
        self.output_dir = os.path.join(script_dir, "../dataset")
        os.makedirs(self.output_dir, exist_ok=True)
        
    @retry_with_network_check
    def count_repo_old_commits(self, repo_full_name):
        """リポジトリの180日以前のコミット数をカウント"""
        print(f"\nチェック中: {repo_full_name}")
        
        try:
            repo = self.g.get_repo(repo_full_name)
            
            # 2025年1月1日から180日前 = 2024年7月4日
            cutoff_date = datetime(2024, 7, 4)
            
            # 180日以前のコミットを全て取得してカウント
            commits = repo.get_commits(until=cutoff_date)
            
            commit_count = 0
            for commit in commits:
                commit_count += 1
                if commit_count % 100 == 0:
                    print(f"  カウント中: {commit_count}件...")
                
                # API rate limit対策
                time.sleep(0.05)
            
            print(f"  → 2024年7月4日以前のコミット数: {commit_count}件")
            
            return {
                'repo': repo_full_name,
                'stars': repo.stargazers_count,
                'old_commits_count': commit_count
            }
            
        except Exception as e:
            print(f"  エラー: {e}")
            return None
    
    def count_all_repos(self):
        """repository_listの全リポジトリをチェック"""
        print("="*80)
        print("180日以前のコミット数カウント開始")
        print("対象期間: 2024年7月4日以前")
        print("="*80)
        
        # repository_list.csvを読み込む
        csv_path = os.path.join(script_dir, "../dataset/repository_list.csv")
        if not os.path.exists(csv_path):
            print(f"エラー: {csv_path} が見つかりません")
            return
        
        df = pd.read_csv(csv_path)
        print(f"リポジトリリスト読み込み完了: {len(df)}件\n")
        
        results = []
        
        for index, row in df.iterrows():
            repo_full_name = f"{row['owner']}/{row['repository_name']}"
            print(f"[{index + 1}/{len(df)}] ", end='')
            
            result = self.count_repo_old_commits(repo_full_name)
            
            if result:
                results.append(result)
            
            # API rate limit対策
            time.sleep(1)
        
        print(f"\n{'='*80}")
        print(f"カウント完了")
        print(f"  処理完了: {len(results)}件")
        print(f"{'='*80}")
        
        # 結果をテキストファイルに保存
        self.save_results(results)
        
        return results
    
    def save_results(self, results):
        """結果をテキストファイルに保存"""
        output_path = os.path.join(self.output_dir, "old_commits_count.txt")
        
        # 総コミット数を計算
        total_commits = sum(r['old_commits_count'] for r in results)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("180日以前のコミット数カウント結果\n")
            f.write(f"対象期間: 2024年7月4日以前\n")
            f.write(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"処理リポジトリ数: {len(results)}\n")
            f.write(f"総コミット数: {total_commits:,}件\n")
            f.write("="*80 + "\n\n")
            
            for i, result in enumerate(results, 1):
                f.write(f"{i}. {result['repo']}\n")
                f.write(f"   スター数: {result['stars']:,}\n")
                f.write(f"   180日以前のコミット数: {result['old_commits_count']:,}件\n\n")
        
        print(f"\n結果を保存しました: {output_path}")
        print(f"総コミット数: {total_commits:,}件")


def main():
    """メイン処理"""
    # GitHub tokenを取得
    github_token = os.getenv('GITHUB_TOKEN')
    
    if not github_token:
        print("エラー: GITHUB_TOKENが設定されていません")
        print("src/.envファイルにGITHUB_TOKEN=your_token_hereを設定してください")
        return
    
    # カウント実行
    counter = OldCommitCounter(github_token)
    results = counter.count_all_repos()
    
    print("\n" + "="*80)
    print("全ての処理が完了しました！")
    print("="*80)


if __name__ == "__main__":
    main()
