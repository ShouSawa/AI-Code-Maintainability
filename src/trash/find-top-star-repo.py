import pandas as pd
import requests
import time
from collections import defaultdict

def find_repo(df):
    """
    parquetファイルからrepo_urlを取得し、最もスター数の多いリポジトリを表示する
    """
    # repo_urlからユニークなリポジトリを取得
    unique_repos = df['repo_url'].unique()
    
    repo_stars = {}
    failed_repos = []
    
    print(f"検索対象のリポジトリ数: {len(unique_repos)}")
    
    for i, repo_url in enumerate(unique_repos):
        try:
            # GitHub URLからowner/repoの形式を抽出
            if 'github.com' in repo_url:
                parts = repo_url.replace('https://github.com/', '').replace('http://github.com/', '').split('/')
                if len(parts) >= 2:
                    owner = parts[0]
                    repo_name = parts[1]
                    
                    # GitHub API呼び出し
                    api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
                    response = requests.get(api_url)
                    
                    if response.status_code == 200:
                        repo_data = response.json()
                        stars = repo_data.get('stargazers_count', 0)
                        repo_stars[repo_url] = {
                            'stars': stars,
                            'full_name': repo_data.get('full_name', ''),
                            'description': repo_data.get('description', ''),
                            'language': repo_data.get('language', ''),
                            'created_at': repo_data.get('created_at', ''),
                            'updated_at': repo_data.get('updated_at', '')
                        }
                        print(f"進行状況: {i+1}/{len(unique_repos)} - {owner}/{repo_name}: {stars} stars")
                    else:
                        failed_repos.append(f"{repo_url} (Status: {response.status_code})")
                        
                    # API制限を避けるため少し待機
                    time.sleep(0.1)
                        
        except Exception as e:
            failed_repos.append(f"{repo_url} (Error: {str(e)})")
            continue
    
    if repo_stars:
        # スター数で並び替え
        sorted_repos = sorted(repo_stars.items(), key=lambda x: x[1]['stars'], reverse=True)
        
        print("\n" + "="*80)
        print("🌟 最もスター数の多いリポジトリ TOP 10")
        print("="*80)
        
        for rank, (repo_url, info) in enumerate(sorted_repos[:10], 1):
            print(f"{rank:2d}. {info['full_name']}")
            print(f"    ⭐ Stars: {info['stars']:,}")
            print(f"    🔗 URL: {repo_url}")
            print(f"    📝 Description: {info['description'][:100]}..." if info['description'] else "    📝 Description: N/A")
            print(f"    💻 Language: {info['language']}")
            print(f"    📅 Created: {info['created_at'][:10]}")
            print(f"    🔄 Updated: {info['updated_at'][:10]}")
            print()
        
        # 統計情報
        total_stars = sum(info['stars'] for info in repo_stars.values())
        avg_stars = total_stars / len(repo_stars)
        
        print("="*80)
        print("📊 統計情報")
        print("="*80)
        print(f"検索成功したリポジトリ数: {len(repo_stars)}")
        print(f"検索失敗したリポジトリ数: {len(failed_repos)}")
        print(f"総スター数: {total_stars:,}")
        print(f"平均スター数: {avg_stars:.1f}")
        
        if failed_repos:
            print(f"\n⚠️ 検索に失敗したリポジトリ:")
            for failed in failed_repos[:5]:  # 最初の5つのみ表示
                print(f"  - {failed}")
            if len(failed_repos) > 5:
                print(f"  ... その他 {len(failed_repos) - 5} 件")
                
        return sorted_repos[0] if sorted_repos else None
    else:
        print("❌ スター数を取得できるリポジトリが見つかりませんでした。")
        return None

if __name__ == '__main__':
    df = pd.read_parquet("../data_list/all_pull_request_local.parquet")
    top_repo = find_repo(df)
    
    if top_repo:
        repo_url, info = top_repo
        print(f"\n🏆 最もスター数の多いリポジトリ: {info['full_name']} ({info['stars']:,} stars)")

