import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

class AutoGPTCommitAnalyzer:
    def __init__(self):
        self.ai_patterns = {
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
        
        # -------------入力------------------
        self.repo_path = Path("../cloned_Repository/chunky-dad")
        self.output_path = Path("../data_list/RQ2/final_result/")
        
    def detect_ai_commit(self, commit_info):
        """コミット情報からAIによるものか判定"""
        if not commit_info:
            return False, "unknown"
        
        text_to_check = f"{commit_info['message']} {commit_info['author_name']} {commit_info['author_email']}".lower()
        
        for ai_type, patterns in self.ai_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_to_check, re.IGNORECASE):
                    return True, ai_type
        
        return False, "human"
    
    def get_all_commits(self):
        """リポジトリから全てのコミット情報を取得"""
        commits = []
        
        try:
            # Git logコマンドでコミット情報を取得
            cmd = [
                'git', 'log', '--all', '--pretty=format:%H|%an|%ae|%s|%ad',
                '--date=iso'
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                print(f"Git command failed: {result.stderr}")
                return commits
            
            # 出力を解析
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|')
                    if len(parts) >= 5:
                        commit_info = {
                            'hash': parts[0],
                            'author_name': parts[1],
                            'author_email': parts[2],
                            'message': parts[3],
                            'date': parts[4]
                        }
                        commits.append(commit_info)
            
            print(f"取得したコミット数: {len(commits)}")
            return commits
            
        except Exception as e:
            print(f"コミット取得中にエラーが発生しました: {e}")
            return commits
    
    def analyze_commits(self):
        """全コミットを分析してAI/人間の判定を行う"""
        print("リポジトリのコミット分析を開始します...")
        
        # リポジトリの存在確認
        if not self.repo_path.exists():
            print(f"エラー: リポジトリが見つかりません: {self.repo_path}")
            return
        
        # 出力ディレクトリの作成
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # 全コミット取得
        commits = self.get_all_commits()
        
        if not commits:
            print("コミットが取得できませんでした。")
            return
        
        # 分析結果
        results = {
            'total_commits': len(commits),
            'ai_commits': 0,
            'human_commits': 0,
            'ai_types': {},
            'ai_commit_details': [],
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        print("コミットを分析中...")
        for i, commit in enumerate(commits):
            if i % 100 == 0:
                print(f"進捗: {i}/{len(commits)} コミット処理済み")
            
            is_ai, ai_type = self.detect_ai_commit(commit)
            
            if is_ai:
                results['ai_commits'] += 1
                results['ai_types'][ai_type] = results['ai_types'].get(ai_type, 0) + 1
                results['ai_commit_details'].append({
                    'hash': commit['hash'][:8],
                    'author': commit['author_name'],
                    'message': commit['message'][:100],
                    'ai_type': ai_type,
                    'date': commit['date']
                })
            else:
                results['human_commits'] += 1
        
        # 割合計算
        ai_percentage = (results['ai_commits'] / results['total_commits']) * 100
        human_percentage = (results['human_commits'] / results['total_commits']) * 100
        
        # 結果をテキストファイルに出力
        repo_name = self.repo_path.name
        output_file = self.output_path / f"{repo_name}_commit_analysis.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("AutoGPT Repository Commit Analysis Results\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"分析日時: {results['analysis_date']}\n")
            f.write(f"リポジトリパス: {self.repo_path.absolute()}\n\n")
            
            f.write("=" * 40 + "\n")
            f.write("全体統計\n")
            f.write("=" * 40 + "\n")
            f.write(f"総コミット数: {results['total_commits']:,}\n")
            f.write(f"AIコミット数: {results['ai_commits']:,}\n")
            f.write(f"人間コミット数: {results['human_commits']:,}\n\n")
            
            f.write(f"AIコミット割合: {ai_percentage:.2f}%\n")
            f.write(f"人間コミット割合: {human_percentage:.2f}%\n\n")
            
            if results['ai_types']:
                f.write("=" * 40 + "\n")
                f.write("AIタイプ別統計\n")
                f.write("=" * 40 + "\n")
                for ai_type, count in sorted(results['ai_types'].items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / results['ai_commits']) * 100
                    f.write(f"{ai_type}: {count:,} コミット ({percentage:.1f}%)\n")
                f.write("\n")
            
            if results['ai_commit_details']:
                f.write("=" * 40 + "\n")
                f.write("AIコミット詳細 (最新10件)\n")
                f.write("=" * 40 + "\n")
                for detail in results['ai_commit_details'][:10]:
                    f.write(f"Hash: {detail['hash']}\n")
                    f.write(f"Author: {detail['author']}\n")
                    f.write(f"Type: {detail['ai_type']}\n")
                    f.write(f"Date: {detail['date']}\n")
                    f.write(f"Message: {detail['message']}...\n")
                    f.write("-" * 30 + "\n")
        
        print(f"\n分析完了!")
        print(f"結果が保存されました: {output_file}")
        print(f"\n=== 分析結果サマリー ===")
        print(f"総コミット数: {results['total_commits']:,}")
        print(f"AIコミット: {results['ai_commits']:,} ({ai_percentage:.2f}%)")
        print(f"人間コミット: {results['human_commits']:,} ({human_percentage:.2f}%)")
        
        # AIタイプ別統計をコンソールにも表示
        if results['ai_types']:
            print(f"\n{'='*40}")
            print("AIタイプ別統計")
            print(f"{'='*40}")
            for ai_type, count in sorted(results['ai_types'].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / results['ai_commits']) * 100
                print(f"{ai_type}: {count:,} コミット ({percentage:.1f}%)")

def main():
    analyzer = AutoGPTCommitAnalyzer()
    analyzer.analyze_commits()

if __name__ == "__main__":
    main()