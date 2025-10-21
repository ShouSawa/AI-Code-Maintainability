"""
RQ1統合プログラム: AIコミット分析システム（GitHub API版）
機能: リポジトリをクローンせずにGitHub APIで分析
"""

import os
import pandas as pd
from datetime import datetime, timedelta
import re
import numpy as np
from transformers import pipeline
import requests
from github import Github
from dotenv import load_dotenv
import time

# srcフォルダ内の.envファイルを読み込む
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path)

pipe = pipeline("text-generation", model="0x404/ccs-code-llama-7b", device_map="auto")
tokenizer = pipe.tokenizer

class RQ1AnalyzerAPI:
    # AIパターン定義（クラス変数で共有）
    AI_PATTERNS = {
        'copilot': [r'github.*copilot', r'copilot', r'co-authored-by:.*github.*copilot'],
        'codex': [r'openai.*codex', r'codex', r'gpt-.*code'],
        'devin': [r'devin', r'devin.*ai'],
        'cursor': [r'cursor.*ai', r'cursor.*editor'],
        'claude': [r'claude.*code', r'claude.*ai', r'anthropic'],
        'general': [r'ai.*assisted', r'machine.*generated', r'bot.*commit', r'automated.*commit', r'ai.*commit']
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

    def is_ai_generated_commit(self, commit_message, author_name, author_email):
        """AIコミット判定"""
        text = f"{commit_message} {author_name} {author_email}".lower()
        
        for ai_type, patterns in self.AI_PATTERNS.items():
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
                return True, ai_type
        return False, "human"

    def detect_specific_ai_tool(self, commit_message, author_name, author_email):
        """AIツール特定"""
        text = f"{commit_message} {author_name} {author_email}".lower()
        
        tool_map = {
            'GitHub Copilot': [r'github.*copilot', r'copilot'],
            'OpenAI Codex': [r'openai.*codex', r'codex'],
            'Devin': [r'devin'],
            'Cursor': [r'cursor.*ai', r'cursor.*editor'],
            'Claude Code': [r'claude.*code', r'claude.*ai', r'anthropic'],
            'ChatGPT/OpenAI': [r'gpt', r'chatgpt', r'openai']
        }
        
        for tool, patterns in tool_map.items():
            if any(re.search(pattern, text) for pattern in patterns):
                return tool
        return 'General AI'

    def get_commits_with_file_additions_api(self, max_commits=500):
        """GitHub APIで90日以前のファイル追加コミット取得"""
        print("=== GitHub APIでコミット取得中 ===")
        
        cutoff_date = datetime.now() - timedelta(days=90)
        commits_data = []
        
        try:
            # コミット取得（日付でフィルタ）
            commits = self.repo.get_commits(until=cutoff_date)
            
            count = 0
            for commit in commits:
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
                            'date': commit_date,
                            'message': message,
                            'added_files': added_files
                        })
                    
                    # API rate limit対策
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"コミット処理エラー {commit.sha[:8]}: {e}")
                    continue
            
            print(f"コミット取得完了: {len(commits_data)}件（ファイル追加あり）")
            return commits_data
            
        except Exception as e:
            print(f"GitHub API エラー: {e}")
            return []

    def step1_find_added_files(self):
        """ステップ1: ファイル追加分析（API版）"""
        print("\n=== ステップ1: ファイル追加分析 (API版) ===")
        
        commits_data = self.get_commits_with_file_additions_api()
        
        if not commits_data:
            print("ファイル追加コミット未発見")
            return None
        
        # データ作成
        csv_data = []
        for commit in commits_data:
            is_ai, ai_type = self.is_ai_generated_commit(
                commit['message'], commit['author_name'], commit['author_email']
            )
            author_type = "AI" if is_ai else "Human"
            ai_tool = self.detect_specific_ai_tool(
                commit['message'], commit['author_name'], commit['author_email']
            ) if is_ai else "N/A"
            
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
        
        df = pd.DataFrame(csv_data)
        print(f"分析完了 - 総計:{len(df)} AI:{len(df[df['author_type']=='AI'])} Human:{len(df[df['author_type']=='Human'])}")
        return df

    def get_file_commits_api(self, file_path):
        """GitHub APIで特定ファイルのコミット履歴取得"""
        try:
            commits = self.repo.get_commits(path=file_path)
            commit_logs = []
            
            for commit in commits:
                commit_logs.append({
                    'hash': commit.sha,
                    'date': commit.commit.author.date.isoformat(),
                    'author': commit.commit.author.name or "Unknown",
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

    def get_files_by_author_type(self, df, target_ai_count=10, target_human_count=10):
        """AI/Humanファイル選択（同数調整版）"""
        ai_files, human_files = [], []
        
        for _, row in df.iterrows():
            if len(ai_files) >= target_ai_count and len(human_files) >= target_human_count:
                break
            
            file_info = {
                'commit_hash': row['commit_hash'],
                'added_file': row['added_file'],
                'author_type': row['author_type'],
                'ai_tool': row['ai_tool']
            }
            
            if row['author_type'] == 'AI' and len(ai_files) < target_ai_count:
                ai_files.append(file_info)
            elif row['author_type'] == 'Human' and len(human_files) < target_human_count:
                human_files.append(file_info)
        
        # 同数に調整
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
        
        results = []
        for idx, file_info in enumerate(selected_files):
            print(f"処理中: {idx+1}/{len(selected_files)} - {file_info['added_file']}")
            
            file_path = file_info['added_file']
            commit_hash = file_info['commit_hash']
            author_type = file_info['author_type']
            
            commit_logs = self.get_file_commits_api(file_path)
            
            if not commit_logs:
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
                for log in commit_logs:
                    is_ai, ai_type = self.is_ai_generated_commit(
                        log['message'], log['author'], log['email']
                    )
                    results.append({
                        'original_commit_type': author_type,
                        'original_commit_hash': commit_hash,
                        'file_path': file_path,
                        'commit_hash': log['hash'],
                        'commit_date': log['date'],
                        'author': log['author'],
                        'commit_message': log['message'],
                        'is_ai_generated': is_ai,
                        'ai_type': ai_type,
                        'ai_tool': self.detect_specific_ai_tool(
                            log['message'], log['author'], log['email']
                        ) if is_ai else 'N/A'
                    })
        
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

    def step3_classify_commits(self, df):
        """ステップ3: コミット分類"""
        print("\n=== ステップ3: コミット分類 ===")
        
        if not pipe:
            print("分類モデル利用不可 - 分類スキップ")
            df['classification_label'] = 'not_classified'
            return df
        
        results = []
        total = len(df)
        
        for idx, row in df.iterrows():
            if idx % 20 == 0:
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
        output_file = os.path.join(self.final_output_dir, f"{self.repo_name}_commit_analysis_results.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(results))
        
        print(f"分析完了: {output_file}")
        print("\n".join(results[:10]) + "\n...")
        return results

    def run_full_analysis(self):
        """全分析実行（API版）"""
        print(f"=== RQ1分析開始 (API版): {self.repo_name_full} ===")
        
        # step1: ファイル追加分析
        df_additions = self.step1_find_added_files()
        if df_additions is None:
            return print("ステップ1エラー - 終了")
        
        # step2: コミット履歴分析
        df_history = self.step2_find_commit_changed_files(df_additions)
        if df_history is None:
            return print("ステップ2エラー - 終了")
        
        # step3: コミット分類
        df_classified = self.step3_classify_commits(df_history)
        if df_classified is None:
            return print("ステップ3エラー - 終了")
        
        # 最終保存
        print("\n=== 最終結果保存 ===")
        current_datetime = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = os.path.join(self.final_output_dir, f"{self.repo_name}_commit_classification_results_{current_datetime}.csv")
        
        # CSV保存
        df_classified[['original_commit_type', 'commit_hash', 'file_path', 'classification_label',
                    'commit_date', 'author', 'is_ai_generated', 'ai_tool', 'commit_message']].to_csv(
                    csv_file, index=False, encoding='utf-8')
        
        # 分析実行
        self.step4_analyze_commit_data(df_classified)
        
        print(f"\n=== 完了: {self.repo_name} ===")
        print(f"CSV: {csv_file}")
        print(f"TXT: {os.path.join(self.final_output_dir, f'{self.repo_name}_commit_analysis_results.txt')}")


def main():
    """メイン実行"""
    # 設定
    repo_name_full = "TheAlgorithms/Python"  # owner/repo 形式
    github_token = os.getenv("GITHUB_TOKEN")
    
    print(f"=== RQ1分析 (GitHub API版) ===")
    print(f"リポジトリ: {repo_name_full}")
    print(f"GitHub API: {'OK' if github_token else 'NG'}")
    
    if not github_token:
        print("エラー: GitHub tokenが設定されていません")
        print(".envファイルにGITHUB_TOKENを設定してください")
        return
    
    start_time = datetime.now()
    
    try:
        analyzer = RQ1AnalyzerAPI(repo_name_full, github_token)
        analyzer.run_full_analysis()
    except Exception as e:
        print(f"エラー: {e}")
    
    print(f"処理時間: {datetime.now() - start_time}")


if __name__ == "__main__":
    main()
