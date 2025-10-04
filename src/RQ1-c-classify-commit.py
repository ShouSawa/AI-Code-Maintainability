from transformers import pipeline
import requests
from github import Github
import os
import pandas as pd

# モデル読み込み
pipe = pipeline("text-generation", model="0x404/ccs-code-llama-7b", device_map="auto")
tokenizer = pipe.tokenizer

def prepare_prompt(commit_message: str, git_diff: str, context_window: int = 1024):
    """プロンプトを準備する関数"""
    # システムメッセージ（分類の指示）
    prompt_head = "<s>[INST] <<SYS>>\\nあなたはコミットメッセージとコード差分を基にコミットを分類するツールです。以下の10カテゴリのいずれかに分類してください：docs, perf, style, refactor, feat, fix, test, ci, build, chore\\n[各カテゴリの詳細定義...]<</SYS>>\\n\\n"

    # メッセージとdiffを適切な長さに調整
    prompt_head_encoded = tokenizer.encode(prompt_head, add_special_tokens=False)

    prompt_message = f"- コミットメッセージ:\\n{commit_message}\\n"
    prompt_message_encoded = tokenizer.encode(prompt_message, max_length=64,
                                            truncation=True, add_special_tokens=False)

    prompt_diff = f"- コード差分:\\n{git_diff}\\n"
    remaining_length = (context_window - len(prompt_head_encoded) - len(prompt_message_encoded) - 6)
    prompt_diff_encoded = tokenizer.encode(prompt_diff, max_length=remaining_length,truncation=True, add_special_tokens=False)

    prompt_end = tokenizer.encode(" [/INST]", add_special_tokens=False)

    return tokenizer.decode(prompt_head_encoded + prompt_message_encoded + prompt_diff_encoded + prompt_end)

def classify_commit(commit_message: str, git_diff: str, context_window: int = 1024):
    """コミットを分類する関数"""
    prompt = prepare_prompt(commit_message, git_diff, context_window)
    result = pipe(prompt, max_new_tokens=10, pad_token_id=pipe.tokenizer.eos_token_id)
    label = result[0]["generated_text"].split()[-1]
    return label

def fetch_message_and_diff(repo_name, commit_sha):
    """GitHubからコミット情報を取得"""
    g = Github(os.getenv("GITHUB_TOKEN"))

    try:
        repo = g.get_repo(repo_name)
        commit = repo.get_commit(commit_sha)

        if commit.parents:
            parent_sha = commit.parents[0].sha
            diff_url = repo.compare(parent_sha, commit_sha).diff_url
            return commit.commit.message, requests.get(diff_url).text
        else:
            raise ValueError("親コミットが見つかりません")
    except Exception as e:
        raise RuntimeError(f"コミット情報取得エラー: {e}")

def load_commit_data(csv_path):
    """CSVファイルからコミットデータを読み込む"""
    return pd.read_csv(csv_path)

def save_classification_results(results,repo_name_full):

    repo_name = repo_name_full.split("/")[1]  # "AutoGPT"だけを抽出
    output_path = f"../data_list/RQ1/final_result/{repo_name}_commit_classification_results.csv"
    """分類結果をCSVファイルに保存"""
    df_results = pd.DataFrame(results)
    
    # 列の順序を指定（original_commit_typeを1列目に追加）
    columns_order = [
        'original_commit_type',  # 1列目に追加
        'commit_hash',
        'file_path', 
        'classification_label',
        'commit_date',
        'author',
        'is_ai_generated',
        'commit_message'
    ]
    
    df_results = df_results[columns_order]
    df_results.to_csv(output_path, index=False, encoding='utf-8')
    print(f"結果を保存しました: {output_path}")

def process_commits(repo_name_full):

    repo_name = repo_name_full.split("/")[1]  # "AutoGPT"だけを抽出
    csv_path=f"../data_list/RQ1/{repo_name}_file_commit_history.csv"
    """CSVのすべてのコミットを処理する"""
    df = load_commit_data(csv_path)
    results = []
    
    for index, row in df.iterrows():
        commit_sha = row['commit_hash']
        try:
            message, diff = fetch_message_and_diff(repo_name_full, commit_sha)  # GitHub API呼び出しには完全な名前を使用
            classification = classify_commit(message, diff)
            
            result = {
                'original_commit_type': row['original_commit_type'],  # 追加
                'commit_hash': commit_sha,
                'file_path': row['file_path'],
                'classification_label': classification,
                'commit_date': row['commit_date'],
                'author': row['author'],
                'is_ai_generated': row['is_ai_generated'],
                'commit_message': row['commit_message']
            }
            results.append(result)
            print(f"処理完了: {commit_sha[:8]} -> {classification}")
            
        except Exception as e:
            print(f"エラー (commit: {commit_sha[:8]}): {e}")
            # エラーの場合もデータを保持（分類ラベルは'error'とする）
            result = {
                'original_commit_type': row['original_commit_type'],  # 追加
                'commit_hash': commit_sha,
                'file_path': row['file_path'],
                'classification_label': 'error',
                'commit_date': row['commit_date'],
                'author': row['author'],
                'is_ai_generated': row['is_ai_generated'],
                'commit_message': row['commit_message']
            }
            results.append(result)
            
    return results

# 使用例
if __name__ == "__main__":
    # -------入力--------------------------
    repo_name_full="drivly/ai"
    results = process_commits(repo_name_full)
    
    # 結果をCSVファイルに保存
    save_classification_results(results, repo_name_full)

    # 結果を表示
    print("\n=== 処理結果 ===")
    for result in results:
        print(f"元のコミットタイプ: {result['original_commit_type']}")
        print(f"コミット: {result['commit_hash'][:8]}")
        print(f"ファイル: {result['file_path']}")
        print(f"分類結果: {result['classification_label']}")
        print(f"作者: {result['author']} ({'AI' if result['is_ai_generated'] else '人間'})")
        print("-" * 50)

