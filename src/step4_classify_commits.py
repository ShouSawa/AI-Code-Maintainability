"""
Step4: コミット分類
機能: step3で取得したコミットを分類してCSVに保存
"""

import os
import pandas as pd
from datetime import datetime
from github import Github
from dotenv import load_dotenv
from tqdm import tqdm
from transformers import pipeline
import requests

# componentsフォルダからインポート
from components.check_network import retry_with_network_check

# .envファイルを読み込む
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path)

# モデル読み込み
print("分類モデル読み込み中...")
pipe = pipeline("text-generation", model="0x404/ccs-code-llama-7b", device_map="auto")
tokenizer = pipe.tokenizer
print("モデル読み込み完了")


class CommitClassifier:
    def __init__(self, repo_name_full, github_token):
        """
        Args:
            repo_name_full: 'owner/repo' 形式のリポジトリ名
            github_token: GitHub Personal Access Token
        """
        self.repo_name_full = repo_name_full
        self.github_token = github_token
        
        # GitHub API初期化
        self.g = Github(self.github_token)
        self.repo = self.g.get_repo(repo_name_full)

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
        try:
            prompt = self.prepare_prompt(commit_message, git_diff, context_window)
            result = pipe(prompt, max_new_tokens=10, pad_token_id=pipe.tokenizer.eos_token_id)
            label = result[0]["generated_text"].split()[-1]
            return label
        except Exception as e:
            print(f"  分類エラー: {e}")
            return "classification_error"

    @retry_with_network_check
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
            print(f"  GitHub取得エラー: {e}")
            return None, None

    def get_commit_changed_lines(self, commit_sha):
        """コミットの変更行数を取得"""
        try:
            commit = self.repo.get_commit(commit_sha)
            return commit.stats.additions + commit.stats.deletions
        except Exception as e:
            print(f"  変更行数取得エラー: {e}")
            return 0


def classify_commits(df, github_token):
    """コミットを分類
    
    Args:
        df: step3の出力DataFrame
        github_token: GitHub token
        
    Returns:
        DataFrame: 分類結果を追加したDataFrame
    """
    results = []
    
    # リポジトリごとに処理
    for repo_name in df['repository_name'].unique():
        print(f"\n{repo_name}")
        repo_df = df[df['repository_name'] == repo_name]
        
        try:
            classifier = CommitClassifier(repo_name, github_token)
            
            for _, row in tqdm(repo_df.iterrows(), total=len(repo_df), desc=f"  分類中", leave=False):
                commit_sha = row['commit_hash']
                
                # コミット情報取得
                message, diff = classifier.fetch_message_and_diff(commit_sha)
                
                if message is None:
                    classification_label = "fetch_error"
                    changed_lines = 0
                else:
                    # 分類実行
                    classification_label = classifier.classify_commit(message, diff)
                    changed_lines = classifier.get_commit_changed_lines(commit_sha)
                
                # 結果を記録
                result = row.to_dict()
                result['classification_label'] = classification_label
                result['changed_lines'] = changed_lines
                results.append(result)
                
        except Exception as e:
            print(f"  エラー: {e}")
            # エラーが発生した場合でも、残りのデータを分類なしで記録
            for _, row in repo_df.iterrows():
                result = row.to_dict()
                result['classification_label'] = 'repo_error'
                result['changed_lines'] = 0
                results.append(result)
    
    return pd.DataFrame(results)


def main():
    """メイン実行"""
    # GitHub token取得
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("エラー: GitHub tokenが設定されていません")
        return
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_csv = os.path.join(script_dir, "../results/EASE-results/csv/step3_all_commits.csv")
    output_csv = os.path.join(script_dir, "../results/EASE-results/csv/step4_classified_commits.csv")
    
    print("=" * 80)
    print("Step4: コミット分類")
    print("=" * 80)
    print(f"入力: {input_csv}")
    print(f"出力: {output_csv}")
    print("=" * 80)
    
    # step3の結果を読み込み
    if not os.path.exists(input_csv):
        print(f"\nエラー: {input_csv} が見つかりません")
        print("先にstep3_get_commits.pyを実行してください")
        return
    
    df = pd.read_csv(input_csv)
    print(f"\n読み込み: {len(df)}件のコミット")
    print(f"リポジトリ数: {df['repository_name'].nunique()}件")
    
    # 処理開始
    start_time = datetime.now()
    classified_df = classify_commits(df, github_token)
    
    # CSV保存
    if len(classified_df) > 0:
        classified_df.to_csv(output_csv, index=False, encoding='utf-8-sig')
        
        print(f"\n✓ 保存完了: {len(classified_df)}件のコミット")
        
        # 分類結果のサマリー
        if 'classification_label' in classified_df.columns:
            print("\n分類結果:")
            label_counts = classified_df['classification_label'].value_counts()
            for label, count in label_counts.items():
                print(f"  {label}: {count}件 ({count/len(classified_df)*100:.1f}%)")
    else:
        print("\n✗ 分類結果がありません")
    
    # 処理時間表示
    elapsed_time = datetime.now() - start_time
    print(f"\n総処理時間: {elapsed_time}")
    print("=" * 80)


if __name__ == "__main__":
    main()
