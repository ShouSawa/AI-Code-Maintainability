import pandas as pd
import subprocess
import os
from datetime import datetime
import csv
import re

def is_ai_generated_commit(commit_message, author_name, author_email):
    """
    コミットメッセージ、作成者名、メールアドレスからAI生成かどうかを判定
    """
    ai_patterns = {
        'openai_codex': [
            r'openai.*codex', r'codex', r'gpt-.*code', r'ai.*generated',
            r'automated.*fix', r'auto.*generated'
        ],
        'devin': [
            r'devin', r'devin.*ai', r'automated.*devin'
        ],
        'github_copilot': [
            r'github.*copilot', r'copilot', r'co-authored-by:.*github.*copilot',
            r'suggested.*by.*copilot', r'copilot.*suggestion'
        ],
        'cursor': [
            r'cursor.*ai', r'cursor.*editor', r'cursor.*suggestion'
        ],
        'claude_code': [
            r'claude.*code', r'claude.*ai', r'anthropic.*claude'
        ],
        'general_ai': [
            r'ai.*assisted', r'machine.*generated', r'automatically.*generated',
            r'bot.*commit', r'automated.*commit', r'ai.*commit',
            r'auto.*fix', r'auto.*update', r'automated.*update'
        ]
    }
    
    text_to_check = f"{commit_message} {author_name} {author_email}".lower()
    
    for ai_type, patterns in ai_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_to_check, re.IGNORECASE):
                return True, ai_type
    
    return False, "human"

def detect_specific_ai_tool(commit_message, author_name, author_email):
    """
    特定のAIツールを検出する
    """
    combined_text = (commit_message + ' ' + author_name + ' ' + author_email).lower()
    
    if any(re.search(keyword, combined_text) for keyword in [r'github.*copilot', r'copilot']):
        return 'GitHub Copilot'
    elif any(re.search(keyword, combined_text) for keyword in [r'openai.*codex', r'codex']):
        return 'OpenAI Codex'
    elif any(re.search(keyword, combined_text) for keyword in [r'devin', r'devin.*ai']):
        return 'Devin'
    elif any(re.search(keyword, combined_text) for keyword in [r'cursor.*ai', r'cursor.*editor']):
        return 'Cursor'
    elif any(re.search(keyword, combined_text) for keyword in [r'claude.*code', r'claude.*ai', r'anthropic']):
        return 'Claude Code'
    elif any(re.search(keyword, combined_text) for keyword in [r'gpt', r'chatgpt', r'openai']):
        return 'ChatGPT/OpenAI'
    else:
        return 'General AI'

def get_git_log_for_file(repo_path, file_path):
    """
    指定されたファイルのGitコミット履歴を取得する（古い順）
    """
    try:
        # git logコマンドでファイルの履歴を取得（古い順）
        cmd = [
            'git', 'log', 
            '--follow',  # ファイルの名前変更を追跡
            '--reverse',  # 古い順（時系列順）でソート
            '--pretty=format:%H|%ci|%an|%ae|%s',  # ハッシュ|日時|作者名|作者メール|コミットメッセージ
            '--', file_path
        ]
        
        result = subprocess.run(
            cmd, 
            cwd=repo_path, 
            capture_output=True, 
            text=True, 
            encoding='utf-8',
            errors='replace'  # エンコーディングエラーを回避
        )
        
        if result.returncode == 0:
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
        else:
            print(f"Error getting git log for {file_path}: {result.stderr}")
            return []
            
    except Exception as e:
        print(f"Exception getting git log for {file_path}: {e}")
        return []

def get_files_by_author_type(df, target_ai_count=7, target_human_count=7):
    """
    AIとHumanのコミットから、それぞれ指定された数だけファイルを取得する
    """
    ai_files = []
    human_files = []
    
    for _, row in df.iterrows():
        if len(ai_files) >= target_ai_count and len(human_files) >= target_human_count:
            break
            
        if row['author_type'] == 'AI' and len(ai_files) < target_ai_count:
            ai_files.append({
                'commit_hash': row['commit_hash'],
                'added_file': row['added_file'],
                'author_type': row['author_type']
            })
        elif row['author_type'] == 'Human' and len(human_files) < target_human_count:
            human_files.append({
                'commit_hash': row['commit_hash'],
                'added_file': row['added_file'],
                'author_type': row['author_type']
            })
    
    return ai_files + human_files

def process_file_commits():
    """
    CSVからAIとHumanのコミットを7件ずつ取得し、それらのファイルのコミット履歴を処理する
    """
    # CSVファイルを読み込み
    # --------------入力--------------------------
    repo_name = "ai"
    csv_file = f'../data_list/RQ1/{repo_name}_file_additions.csv'
    df = pd.read_csv(csv_file)
    
    if df.empty:
        print("CSV file is empty")
        return
    
    # AIとHumanのファイルを7件ずつ取得
    selected_files = get_files_by_author_type(df, target_ai_count=7, target_human_count=7)
    
    print(f"Selected {len(selected_files)} files for processing:")
    ai_count = sum(1 for f in selected_files if f['author_type'] == 'AI')
    human_count = sum(1 for f in selected_files if f['author_type'] == 'Human')
    print(f"  AI files: {ai_count}")
    print(f"  Human files: {human_count}")
    
    # リポジトリのパス
    repo_path = f'../cloned_Repository/{repo_name}'

    if not os.path.exists(repo_path):
        print(f"Repository path does not exist: {repo_path}")
        return
    
    # 出力ディレクトリを作成
    output_dir = '../data_list/RQ1/'
    os.makedirs(output_dir, exist_ok=True)
    
    # 結果を格納するリスト
    results = []
    
    # 選択されたファイルを処理
    for file_info in selected_files:
        file_path = file_info['added_file']
        commit_hash = file_info['commit_hash']
        author_type = file_info['author_type']
        
        print(f"Processing file: {file_path} (from {author_type} commit: {commit_hash[:8]})")
        
        # ファイルのコミット履歴を取得
        commit_logs = get_git_log_for_file(repo_path, file_path)
        
        if not commit_logs:
            print(f"  No commit history found for {file_path}")
            # コミット履歴が見つからない場合でもファイル名は記録
            results.append({
                'original_commit_type': author_type,
                'original_commit_hash': commit_hash,
                'file_path': file_path,
                'commit_hash': 'No commits found',
                'commit_date': '',
                'author': '',
                'commit_message': '',
                'is_ai_generated': False,
                'ai_type': 'N/A',
                'ai_tool': 'N/A'
            })
        else:
            print(f"  Found {len(commit_logs)} commits for {file_path}")
            # 各コミットの情報を処理
            for log_line in commit_logs:
                if not log_line:
                    continue
                    
                try:
                    parts = log_line.split('|')
                    if len(parts) >= 5:
                        commit_hash_log = parts[0]
                        commit_date = parts[1]
                        author_name = parts[2]
                        author_email = parts[3]
                        commit_message = parts[4] if len(parts) > 4 else ''
                        
                        # AI判定を実行
                        is_ai, ai_type = is_ai_generated_commit(commit_message, author_name, author_email)
                        ai_tool = detect_specific_ai_tool(commit_message, author_name, author_email) if is_ai else 'N/A'
                        
                        results.append({
                            'original_commit_type': author_type,
                            'original_commit_hash': commit_hash,
                            'file_path': file_path,
                            'commit_hash': commit_hash_log,
                            'commit_date': commit_date,
                            'author': author_name,
                            'commit_message': commit_message,
                            'is_ai_generated': is_ai,
                            'ai_type': ai_type,
                            'ai_tool': ai_tool
                        })
                        
                except Exception as e:
                    print(f"  Error processing log line: {log_line}, Error: {e}")
                    continue
    
    # 結果をCSVファイルに出力
    output_file = os.path.join(output_dir, f'{repo_name}_file_commit_history.csv')

    if results:
        df_output = pd.DataFrame(results)
        df_output.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\nResults saved to: {output_file}")
        print(f"Total records: {len(results)}")
        
        # 結果の概要を表示
        print("\nSummary:")
        total_commits = len([r for r in results if r['commit_hash'] != 'No commits found'])
        ai_commits = len([r for r in results if r['is_ai_generated']])
        human_commits = len([r for r in results if not r['is_ai_generated'] and r['commit_hash'] != 'No commits found'])
        
        print(f"Total commits analyzed: {total_commits}")
        print(f"AI-generated commits: {ai_commits}")
        print(f"Human-generated commits: {human_commits}")
        
        # ファイル別の統計
        print("\nFile statistics:")
        ai_files = len([r for r in results if r['original_commit_type'] == 'AI'])
        human_files = len([r for r in results if r['original_commit_type'] == 'Human'])
        print(f"Files from AI commits: {ai_files // len(commit_logs) if commit_logs else 0}")
        print(f"Files from Human commits: {human_files // len(commit_logs) if commit_logs else 0}")
        
        if ai_commits > 0:
            print("\nAI Tools breakdown:")
            ai_tools = {}
            for r in results:
                if r['is_ai_generated'] and r['ai_tool'] != 'N/A':
                    tool = r['ai_tool']
                    ai_tools[tool] = ai_tools.get(tool, 0) + 1
            for tool, count in ai_tools.items():
                print(f"  {tool}: {count}")
        
    else:
        print("No results to save")

if __name__ == "__main__":
    process_file_commits()