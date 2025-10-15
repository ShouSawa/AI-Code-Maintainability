"""
RQ1統合プログラム: AIコミット分析システム（高速化版）
機能: AI vs Human のファイル追加・コミット履歴・分類・統計分析を一括実行
"""

import os
import subprocess
import pandas as pd
from datetime import datetime, timedelta
import re
import numpy as np
from transformers import pipeline
import requests
from github import Github

class RQ1Analyzer:
    # AIパターン定義（クラス変数で共有）
    AI_PATTERNS = {
        'copilot': [r'github.*copilot', r'copilot', r'co-authored-by:.*github.*copilot'],
        'codex': [r'openai.*codex', r'codex', r'gpt-.*code'],
        'devin': [r'devin', r'devin.*ai'],
        'cursor': [r'cursor.*ai', r'cursor.*editor'],
        'claude': [r'claude.*code', r'claude.*ai', r'anthropic'],
        'general': [r'ai.*assisted', r'machine.*generated', r'bot.*commit', r'automated.*commit', r'ai.*commit']
    }
    
    def __init__(self, repo_name, repo_name_full, github_token=None):
        self.repo_name = repo_name
        self.repo_name_full = repo_name_full
        self.github_token = github_token
        
        # パス設定
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.repo_path = os.path.join(script_dir, f"../cloned_Repository/{repo_name}")
        self.final_output_dir = os.path.join(script_dir, "../data_list/RQ1/final_result")
        os.makedirs(self.final_output_dir, exist_ok=True)
        
        self.pipe = None
        self.tokenizer = None
    def initialize_classification_model(self):
        """分類モデル初期化"""
        try:
            print("分類モデル初期化中...")
            self.pipe = pipeline("text-generation", model="0x404/ccs-code-llama-7b", device_map="auto")
            self.tokenizer = self.pipe.tokenizer
            print("分類モデル初期化完了")
        except Exception as e:
            print(f"分類モデル初期化失敗: {e}")
            self.pipe = None

    def is_ai_generated_commit(self, commit_message, author_name, author_email):
        """AIコミット判定（統合パターンマッチング）"""
        text = f"{commit_message} {author_name} {author_email}".lower()
        
        for ai_type, patterns in self.AI_PATTERNS.items():
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
                return True, ai_type
        return False, "human"

    def detect_specific_ai_tool(self, commit_message, author_name, author_email):
        """AIツール特定（簡素化版）"""
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

    def get_commits_with_file_additions(self):
        """90日以前のファイル追加コミット取得（高速化版）"""
        original_cwd = os.getcwd()
        try:
            os.chdir(self.repo_path)
            cutoff_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            
            cmd = ['git', 'log', '--until', cutoff_date, '--name-status',
                   '--pretty=format:%H|%an|%ae|%ad|%s', '--date=iso']
            
            result = subprocess.run(cmd, capture_output=True, text=True, 
                                  encoding='utf-8', errors='replace')
            return result.stdout if result.returncode == 0 else ""
        except Exception as e:
            print(f"Git取得エラー: {e}")
            return ""
        finally:
            os.chdir(original_cwd)

    def parse_commit_data(self, git_output):
        """Git出力解析（効率化版）"""
        lines = git_output.strip().split('\n')
        commits_data = []
        current_commit = None
        
        for line in lines:
            if '|' in line and not line.startswith(('A\t', 'M\t', 'D\t')):
                parts = line.split('|', 4)
                if len(parts) >= 5:
                    current_commit = {
                        'hash': parts[0], 'author_name': parts[1], 'author_email': parts[2],
                        'date': parts[3], 'message': parts[4], 'added_files': []
                    }
            elif line.startswith('A\t') and current_commit:
                current_commit['added_files'].append(line[2:])
            elif line == '' and current_commit and current_commit['added_files']:
                commits_data.append(current_commit)
                current_commit = None
        
        # 最後のコミット処理
        if current_commit and current_commit['added_files']:
            commits_data.append(current_commit)
        
        return commits_data

    def step1_find_added_files(self):
        """ステップ1: ファイル追加分析（高速版）"""
        print("=== ステップ1: ファイル追加分析 ===")
        
        if not os.path.exists(self.repo_path):
            print(f"リポジトリ未発見: {self.repo_path}")
            return None
        
        git_output = self.get_commits_with_file_additions()
        if not git_output:
            print("Git出力取得失敗")
            return None
        
        commits_data = self.parse_commit_data(git_output)
        if not commits_data:
            print("ファイル追加コミット未発見")
            return None
        
        # データ作成（リスト内包表記で高速化）
        csv_data = []
        for commit in commits_data:
            is_ai, ai_type = self.is_ai_generated_commit(commit['message'], commit['author_name'], commit['author_email'])
            author_type = "AI" if is_ai else "Human"
            ai_tool = self.detect_specific_ai_tool(commit['message'], commit['author_name'], commit['author_email']) if is_ai else "N/A"
            
            csv_data.extend([{
                'commit_hash': commit['hash'], 'commit_date': commit['date'],
                'added_file': file_path, 'author_type': author_type,
                'ai_type': ai_type, 'ai_tool': ai_tool,
                'author_name': commit['author_name'], 'author_email': commit['author_email'],
                'commit_message': commit['message']
            } for file_path in commit['added_files']])
        
        df = pd.DataFrame(csv_data)
        print(f"分析完了 - 総計:{len(df)} AI:{len(df[df['author_type']=='AI'])} Human:{len(df[df['author_type']=='Human'])}")
        return df

    def get_git_log_for_file(self, file_path):
        """ファイル履歴取得（簡素化版）"""
        try:
            cmd = ['git', 'log', '--follow', '--reverse', 
                   '--pretty=format:%H|%ci|%an|%ae|%s', '--', file_path]
            result = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, 
                                  text=True, encoding='utf-8', errors='replace')
            return result.stdout.strip().split('\n') if result.returncode == 0 and result.stdout.strip() else []
        except Exception as e:
            print(f"履歴取得エラー {file_path}: {e}")
            return []

    def get_files_by_author_type(self, df, target_ai_count=7, target_human_count=7):
        """AI/Humanファイル選択（効率化版）"""
        ai_files, human_files = [], []
        
        for _, row in df.iterrows():
            if len(ai_files) >= target_ai_count and len(human_files) >= target_human_count:
                break
            
            file_info = {'commit_hash': row['commit_hash'], 'added_file': row['added_file'], 'author_type': row['author_type']}
            if row['author_type'] == 'AI' and len(ai_files) < target_ai_count:
                ai_files.append(file_info)
            elif row['author_type'] == 'Human' and len(human_files) < target_human_count:
                human_files.append(file_info)
        
        return ai_files + human_files

    def step2_find_commit_changed_files(self, df):
        """ステップ2: コミット履歴分析（高速版）"""
        print("\n=== ステップ2: コミット履歴分析 ===")
        
        selected_files = self.get_files_by_author_type(df)
        ai_count = sum(1 for f in selected_files if f['author_type'] == 'AI')
        print(f"選択ファイル: {len(selected_files)} (AI:{ai_count} Human:{len(selected_files)-ai_count})")
        
        results = []
        for file_info in selected_files:
            file_path = file_info['added_file']
            commit_hash = file_info['commit_hash']
            author_type = file_info['author_type']
            
            commit_logs = self.get_git_log_for_file(file_path)
            
            if not commit_logs:
                # 履歴なしの場合
                results.append({
                    'original_commit_type': author_type, 'original_commit_hash': commit_hash,
                    'file_path': file_path, 'commit_hash': 'No commits found',
                    'commit_date': '', 'author': '', 'commit_message': '',
                    'is_ai_generated': False, 'ai_type': 'N/A', 'ai_tool': 'N/A'
                })
            else:
                # 履歴処理（効率化）
                for log_line in commit_logs:
                    if not log_line:
                        continue
                    try:
                        parts = log_line.split('|', 4)
                        if len(parts) >= 5:
                            is_ai, ai_type = self.is_ai_generated_commit(parts[4], parts[2], parts[3])
                            results.append({
                                'original_commit_type': author_type, 'original_commit_hash': commit_hash,
                                'file_path': file_path, 'commit_hash': parts[0],
                                'commit_date': parts[1], 'author': parts[2], 'commit_message': parts[4],
                                'is_ai_generated': is_ai, 'ai_type': ai_type,
                                'ai_tool': self.detect_specific_ai_tool(parts[4], parts[2], parts[3]) if is_ai else 'N/A'
                            })
                    except Exception as e:
                        print(f"ログ処理エラー: {e}")
                        continue
        
        return pd.DataFrame(results) if results else None

    def classify_commit(self, commit_message, git_diff):
        """コミット分類（簡素化版）"""
        if not self.pipe or not self.tokenizer:
            return "model_not_available"
        
        try:
            # プロンプト構築（統合版）
            prompt = f"<s>[INST] <<SYS>>\\nコミット分類：docs, perf, style, refactor, feat, fix, test, ci, build, chore<</SYS>>\\n\\n- メッセージ：{commit_message[:100]}\\n- 差分：{git_diff[:500]}\\n [/INST]"
            result = self.pipe(prompt, max_new_tokens=10, pad_token_id=self.pipe.tokenizer.eos_token_id)
            return result[0]["generated_text"].split()[-1]
        except Exception as e:
            print(f"分類エラー: {e}")
            return "classification_error"

    def fetch_message_and_diff(self, commit_sha):
        """GitHub API経由でコミット情報取得"""
        if not self.github_token:
            return None, None
        
        try:
            g = Github(self.github_token)
            repo = g.get_repo(self.repo_name_full)
            commit = repo.get_commit(commit_sha)
            
            if commit.parents:
                diff_url = repo.compare(commit.parents[0].sha, commit_sha).diff_url
                return commit.commit.message, requests.get(diff_url).text
            return commit.commit.message, ""
        except Exception as e:
            print(f"GitHub取得エラー: {e}")
            return None, None

    def step3_classify_commits(self, df):
        """ステップ3: コミット分類（効率化版）"""
        print("\n=== ステップ3: コミット分類 ===")
        
        if not self.github_token:
            print("GitHub token未設定 - 分類スキップ")
            return pd.DataFrame([{
                'original_commit_type': row['original_commit_type'], 'commit_hash': row['commit_hash'],
                'file_path': row['file_path'], 'classification_label': 'not_classified',
                'commit_date': row['commit_date'], 'author': row['author'],
                'is_ai_generated': row['is_ai_generated'], 'commit_message': row['commit_message']
            } for _, row in df.iterrows()])
        
        # モデル初期化
        if not self.pipe:
            self.initialize_classification_model()
        
        results = []
        total = len(df)
        
        for idx, row in df.iterrows():
            if idx % 20 == 0:
                print(f"進捗: {idx}/{total} ({idx/total*100:.0f}%)")
            
            commit_sha = row['commit_hash']
            base_result = {
                'original_commit_type': row['original_commit_type'], 'commit_hash': commit_sha,
                'file_path': row['file_path'], 'commit_date': row['commit_date'],
                'author': row['author'], 'is_ai_generated': row['is_ai_generated'],
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
        """サブセット分析（効率化版）"""
        if len(subset_df) == 0:
            return [f"No {label} commits found"]
        
        analysis = [f"{label.upper()} COMMITS ANALYSIS", "-" * 30]
        
        # 1. ファイル統計
        commits_per_file = subset_df.groupby('file_path').size()
        analysis.extend([
            f"1. Commits per file: avg={commits_per_file.mean():.2f} std={commits_per_file.std():.2f} min={commits_per_file.min()} max={commits_per_file.max()}",
            ""
        ])
        
        # 2. 分類ラベル分布
        analysis.append("2. Classification distribution:")
        overall_labels = subset_df['classification_label'].value_counts()
        for lbl, count in overall_labels.items():
            analysis.append(f"   {lbl}: {count} ({count/len(subset_df)*100:.1f}%)")
        analysis.append("")
        
        # 3. コミット頻度分析（簡素化）
        analysis.append("3. Commit frequency analysis:")
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
            analysis.append(f"   Avg interval: {np.mean(file_frequencies):.1f} days (std: {np.std(file_frequencies):.1f})")
        else:
            analysis.append("   Insufficient data for frequency analysis")
        analysis.append("")
        
        # 4. AI判定統計
        ai_count = len(subset_df[subset_df['is_ai_generated'] == True])
        analysis.extend([
            f"4. Authorship: AI={ai_count} ({ai_count/len(subset_df)*100:.1f}%) Human={len(subset_df)-ai_count} ({(len(subset_df)-ai_count)/len(subset_df)*100:.1f}%)",
            ""
        ])
        
        return analysis

    def step4_analyze_commit_data(self, df):
        """ステップ4: データ分析（効率化版）"""
        print("\n=== ステップ4: データ分析 ===")
        
        df['commit_date'] = pd.to_datetime(df['commit_date'])
        ai_df = df[df['original_commit_type'] == 'AI']
        human_df = df[df['original_commit_type'] == 'Human']
        
        # 統計結果構築
        ai_generated = len(df[df['is_ai_generated'] == True])
        results = [
            f"{self.repo_name} Commit Analysis Results", "=" * 50, "",
            "OVERALL STATISTICS", "-" * 20,
            f"Total commits: {len(df)}",
            f"AI-originated: {len(ai_df)} ({len(ai_df)/len(df)*100:.1f}%)",
            f"Human-originated: {len(human_df)} ({len(human_df)/len(df)*100:.1f}%)",
            f"Unique files: {df['file_path'].nunique()}",
            f"AI-generated commits: {ai_generated} ({ai_generated/len(df)*100:.1f}%)", ""
        ]
        
        # サブセット分析
        results.extend(self.analyze_subset(ai_df, "AI-Originated"))
        results.extend(self.analyze_subset(human_df, "Human-Originated"))
        
        # 比較分析
        if len(ai_df) > 0 and len(human_df) > 0:
            ai_cpf = ai_df.groupby('file_path').size()
            human_cpf = human_df.groupby('file_path').size()
            results.extend([
                "COMPARATIVE ANALYSIS", "-" * 20,
                f"Avg commits per file - AI: {ai_cpf.mean():.2f} Human: {human_cpf.mean():.2f}",
                f"Most active - AI: {ai_cpf.idxmax()} ({ai_cpf.max()}) Human: {human_cpf.idxmax()} ({human_cpf.max()})"
            ])
        
        # ファイル保存
        output_file = os.path.join(self.final_output_dir, f"{self.repo_name}_commit_analysis_results.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(results))
        
        print(f"分析完了: {output_file}")
        print("\n".join(results[:10]) + "\n...")
        return results

    def run_full_analysis(self):
        """全分析実行（超高速版）"""
        print(f"=== RQ1分析開始: {self.repo_name} ===")
        
        # パイプライン実行
        df_additions = self.step1_find_added_files()
        if df_additions is None:
            return print("ステップ1エラー - 終了")
        
        df_history = self.step2_find_commit_changed_files(df_additions)
        if df_history is None:
            return print("ステップ2エラー - 終了")
        
        df_classified = self.step3_classify_commits(df_history)
        if df_classified is None:
            return print("ステップ3エラー - 終了")
        
        # 最終保存
        print("\n=== 最終結果保存 ===")
        csv_file = os.path.join(self.final_output_dir, f"{self.repo_name}_commit_classification_results.csv")
        
        # 列順序指定して保存
        df_classified[['original_commit_type', 'commit_hash', 'file_path', 'classification_label',
                      'commit_date', 'author', 'is_ai_generated', 'commit_message']].to_csv(
                      csv_file, index=False, encoding='utf-8')
        
        # 分析実行
        self.step4_analyze_commit_data(df_classified)
        
        print(f"\n=== 完了: {self.repo_name} ===")
        print(f"CSV: {csv_file}")
        print(f"TXT: {os.path.join(self.final_output_dir, f'{self.repo_name}_commit_analysis_results.txt')}")

def main():
    """メイン実行（超効率化版）"""
    # 設定
    repo_name = "ai"
    repo_name_full = "drivly/ai"
    github_token = os.getenv("GITHUB_TOKEN")
    
    print(f"=== RQ1超高速分析 ===")
    print(f"リポジトリ: {repo_name_full}")
    print(f"GitHub API: {'OK' if github_token else 'NG（分類無効）'}")
    
    start_time = datetime.now()
    RQ1Analyzer(repo_name, repo_name_full, github_token).run_full_analysis()
    
    print(f"処理時間: {datetime.now() - start_time}")

if __name__ == "__main__":
    main()