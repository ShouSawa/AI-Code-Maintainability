"""
AIによって追加されたファイルを特定し、CSVに保存するスクリプト
"""

import os
import subprocess
import pandas as pd
from datetime import datetime, timedelta
import re

def is_ai_generated_commit(commit_message, author_name, author_email):
    """
    コミットメッセージ、作成者名、メールアドレスからAI生成かどうかを判定
    """
    # RQ2と同じAIパターンを使用
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
            r'bot.*commit', r'automated.*commit', r'ai.*commit'
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

def get_commits_with_file_additions(repo_path, since_date):
    """
    指定した日次以前のファイル追加を含むコミットを取得
    """
    # 現在のディレクトリを保存
    original_cwd = os.getcwd()
    
    try:
        os.chdir(repo_path)
        # 6ヶ月前の日付を計算
        cutoff_date = datetime.now() - timedelta(days=90)
        until_str = cutoff_date.strftime('%Y-%m-%d')
        
        # 1年前以前のファイル追加を含むコミットを取得
        cmd = [
            'git', 'log',
            '--until', until_str,
            '--name-status',
            '--pretty=format:%H|%an|%ae|%ad|%s',
            '--date=iso'
        ]
        
        # エンコーディングの問題を解決するために、環境変数を設定してUTF-8を強制
        env = os.environ.copy()
        env['LANG'] = 'en_US.UTF-8'
        env['LC_ALL'] = 'en_US.UTF-8'
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True,
            encoding='utf-8',  # 明示的にUTF-8を指定
            errors='replace',  # デコードエラーを無視して置換文字に変換
            env=env
        )
        return result.stdout
        
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e}")
        return ""
    except UnicodeDecodeError as e:
        print(f"Encoding error: {e}")
        # エラーが発生した場合はバイナリモードで読み込み、手動でデコード
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                env=env
            )
            # バイナリデータをUTF-8でデコード、エラーは無視
            return result.stdout.decode('utf-8', errors='replace')
        except Exception as e:
            print(f"Failed to decode output: {e}")
            return ""
    finally:
        # 元のディレクトリに戻る
        os.chdir(original_cwd)

def parse_commit_data(git_output):
    """
    Gitの出力を解析してコミット情報とファイル変更を抽出
    """
    lines = git_output.strip().split('\n')
    commits_data = []
    
    current_commit = None
    
    for line in lines:
        if '|' in line and not line.startswith(('A\t', 'M\t', 'D\t')):
            # コミット情報行
            parts = line.split('|')
            if len(parts) >= 5:
                current_commit = {
                    'hash': parts[0],
                    'author_name': parts[1],
                    'author_email': parts[2],
                    'date': parts[3],
                    'message': '|'.join(parts[4:]),
                    'added_files': []
                }
        elif line.startswith('A\t') and current_commit:
            # ファイル追加行
            file_path = line[2:]  # 'A\t'を除去
            current_commit['added_files'].append(file_path)
        elif line == '' and current_commit:
            # 空行でコミット終了
            if current_commit['added_files']:  # ファイル追加があった場合のみ
                commits_data.append(current_commit)
            current_commit = None
    
    # 最後のコミットを処理
    if current_commit and current_commit['added_files']:
        commits_data.append(current_commit)
    
    return commits_data

def analyze_file_additions():
    """
    AutoGPTリポジトリのファイル追加コミットを分析
    """
    # スクリプトのディレクトリを基準にした絶対パスを取得
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # ----------入力------------------
    repo_path = os.path.join(script_dir, "../cloned_Repository/ai")

    if not os.path.exists(repo_path):
        print(f"リポジトリが見つかりません: {repo_path}")
        return
    
    print(f"リポジトリパス: {os.path.abspath(repo_path)}")
    print("コミット情報を取得中...")
    git_output = get_commits_with_file_additions(repo_path, None)
    
    if not git_output:
        print("コミット情報の取得に失敗しました")
        return
    
    print(f"取得したGit出力の長さ: {len(git_output)} 文字")
    print("コミットデータを解析中...")
    commits_data = parse_commit_data(git_output)
    
    print(f"解析されたコミット数: {len(commits_data)}")
    
    if not commits_data:
        print("ファイル追加を含むコミットが見つかりませんでした")
        return
    
    # CSV用のデータリストを作成
    csv_data = []
    
    for commit in commits_data:
        is_ai, ai_type = is_ai_generated_commit(
            commit['message'], 
            commit['author_name'], 
            commit['author_email']
        )
        
        if is_ai:
            author_type = "AI"
            ai_tool = detect_specific_ai_tool(
                commit['message'], 
                commit['author_name'], 
                commit['author_email']
            )
        else:
            author_type = "Human"
            ai_tool = "N/A"
        
        # 各ファイルに対して行を作成
        for file_path in commit['added_files']:
            csv_data.append({
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
    
    print(f"CSV行数: {len(csv_data)}")
    
    if not csv_data:
        print("CSVデータが空です")
        return
    
    # DataFrameに変換
    try:
        df = pd.DataFrame(csv_data)
        print(f"DataFrame作成成功: {len(df)} 行, {len(df.columns)} 列")
    except Exception as e:
        print(f"DataFrame作成エラー: {e}")
        return
    
    # 出力ディレクトリを絶対パスで指定
    output_dir = os.path.join(script_dir, "../data_list/RQ1")
    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"出力ディレクトリ作成/確認完了: {os.path.abspath(output_dir)}")
    except Exception as e:
        print(f"出力ディレクトリ作成エラー: {e}")
        return
    
    # CSVファイルに保存
    repo_name = os.path.basename(repo_path)
    output_file = os.path.join(output_dir, f"{repo_name}_file_additions.csv")
    try:
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"CSV保存成功: {os.path.abspath(output_file)}")
        
        # ファイルが実際に存在するか確認
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"ファイル確認成功: サイズ {file_size} bytes")
        else:
            print("ファイルが作成されていません")
            return
            
    except Exception as e:
        print(f"CSV保存エラー: {e}")
        return
    
    print(f"\n=== 分析結果 ===")
    print(f"総ファイル追加数: {len(df)}")
    print(f"AIによるファイル追加: {len(df[df['author_type'] == 'AI'])}")
    print(f"人間によるファイル追加: {len(df[df['author_type'] == 'Human'])}")
    
    if len(df[df['author_type'] == 'AI']) > 0:
        print(f"\n=== AIツール別内訳 ===")
        ai_tool_counts = df[df['author_type'] == 'AI']['ai_tool'].value_counts()
        for tool, count in ai_tool_counts.items():
            print(f"{tool}: {count}")
        
        print(f"\n=== AI種類別内訳 ===")
        ai_type_counts = df[df['author_type'] == 'AI']['ai_type'].value_counts()
        for ai_type, count in ai_type_counts.items():
            print(f"{ai_type}: {count}")
    
    print(f"\n結果を保存しました: {output_file}")
    
    # サンプル表示
    print(f"\n=== サンプルデータ ===")
    if len(df) > 0:
        print(df.head(10).to_string())
    else:
        print("表示するデータがありません")
    
    return df

if __name__ == '__main__':
    analyze_file_additions()