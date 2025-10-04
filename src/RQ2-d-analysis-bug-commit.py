import json
import subprocess
import os
import re
import statistics
from collections import defaultdict
from datetime import datetime

class CommitAnalyzer:
    def __init__(self, json_file_path):
        self.json_file_path = json_file_path
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
        self.stats = defaultdict(int)
        self.detailed_results = []
        # 変更行数の統計用
        self.ai_change_lines = []
        self.human_change_lines = []
        # 変更ファイル数の統計用
        self.ai_changed_files = []
        self.human_changed_files = []
        
    def load_json_data(self):
        """JSONファイルを読み込む"""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading JSON file: {e}")
            return []
    
    def get_commit_info(self, repo_name, commit_hash):
        """Gitリポジトリからコミット情報を取得"""
        try:
            # リポジトリのパスを推測（必要に応じて調整）
            repo_path = f"../cloned_Repository/{repo_name}"
            if not os.path.exists(repo_path):
                repo_path = f"./{repo_name}"
            if not os.path.exists(repo_path):
                print(f"Repository {repo_name} not found")
                return None
            
            # コミットメッセージと作成者情報を取得
            cmd = ['git', '-C', repo_path, 'show', '--format=%B%n---AUTHOR---%n%an%n%ae', '--no-patch', commit_hash]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                print(f"Git command failed for {commit_hash}: {result.stderr}")
                return None
            
            output = result.stdout.strip()
            parts = output.split('---AUTHOR---')
            
            if len(parts) >= 2:
                commit_message = parts[0].strip()
                author_info = parts[1].strip().split('\n')
                author_name = author_info[0] if len(author_info) > 0 else ""
                author_email = author_info[1] if len(author_info) > 1 else ""
                
                return {
                    'message': commit_message,
                    'author_name': author_name,
                    'author_email': author_email
                }
            
        except Exception as e:
            print(f"Error getting commit info for {commit_hash}: {e}")
        
        return None
    
    def get_commit_changes(self, repo_name, commit_hash):
        """コミットの変更行数とファイル数を取得"""
        try:
            repo_path = f"../cloned_Repository/{repo_name}"
            if not os.path.exists(repo_path):
                repo_path = f"./{repo_name}"
            if not os.path.exists(repo_path):
                return None
            
            # 変更行数を取得（--numstatで追加/削除行数を取得）
            cmd = ['git', '-C', repo_path, 'show', '--numstat', '--format=', commit_hash]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode != 0:
                print(f"Git numstat failed for {commit_hash}: {result.stderr}")
                return None
            
            total_added = 0
            total_deleted = 0
            changed_files = 0
            
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        try:
                            added = int(parts[0]) if parts[0] != '-' else 0
                            deleted = int(parts[1]) if parts[1] != '-' else 0
                            total_added += added
                            total_deleted += deleted
                            changed_files += 1
                        except ValueError:
                            # バイナリファイルなどで数値でない場合もファイルとしてカウント
                            changed_files += 1
                            continue
            
            return {
                'added': total_added,
                'deleted': total_deleted,
                'total_changes': total_added + total_deleted,
                'files_changed': changed_files
            }
            
        except Exception as e:
            print(f"Error getting commit changes for {commit_hash}: {e}")
            return None
    
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
    
    def analyze_commits(self):
        """全てのコミットを解析"""
        data = self.load_json_data()
        
        if not data:
            print("No data to analyze")
            return
        
        total_commits = 0
        processed_commits = 0
        
        for i,entry in enumerate(data):
            print("解析中：",i+1)
            repo_name = entry.get('repo_name', 'unknown')
            inducing_commits = entry.get('inducing_commit_hash', [])
            fix_commit = entry.get('fix_commit_hash', 'unknown')
            
            for commit_hash in inducing_commits:
                total_commits += 1
                commit_info = self.get_commit_info(repo_name, commit_hash)
                commit_changes = self.get_commit_changes(repo_name, commit_hash)
                
                if commit_info:
                    processed_commits += 1
                    is_ai, ai_type = self.detect_ai_commit(commit_info)
                    
                    # 統計情報を更新
                    if is_ai:
                        self.stats[f'ai_{ai_type}'] += 1
                        self.stats['total_ai'] += 1
                        # AI用の変更行数とファイル数を記録
                        if commit_changes:
                            self.ai_change_lines.append(commit_changes['total_changes'])
                            self.ai_changed_files.append(commit_changes['files_changed'])
                    else:
                        self.stats['human'] += 1
                        # 人間用の変更行数とファイル数を記録
                        if commit_changes:
                            self.human_change_lines.append(commit_changes['total_changes'])
                            self.human_changed_files.append(commit_changes['files_changed'])
                    
                    # 詳細結果を保存（統計用のみ）
                    result = {
                        'repo_name': repo_name,
                        'commit_hash': commit_hash,
                        'fix_commit_hash': fix_commit,
                        'is_ai': is_ai,
                        'ai_type': ai_type,
                        'author_name': commit_info['author_name'],
                        'author_email': commit_info['author_email'],
                        'message_preview': commit_info['message'][:100] + '...' if len(commit_info['message']) > 100 else commit_info['message']
                    }
                    
                    if commit_changes:
                        result.update({
                            'lines_added': commit_changes['added'],
                            'lines_deleted': commit_changes['deleted'],
                            'total_changes': commit_changes['total_changes'],
                            'files_changed': commit_changes['files_changed']
                        })
                    
                    self.detailed_results.append(result)
                else:
                    self.stats['failed_to_analyze'] += 1
        
        self.stats['total_commits'] = total_commits
        self.stats['processed_commits'] = processed_commits
        
        print(f"Analysis completed: {processed_commits}/{total_commits} commits processed")
    
    def calculate_change_statistics(self):
        """変更行数の統計を計算"""
        stats = {}
        
        if self.ai_change_lines:
            stats['ai'] = {
                'count': len(self.ai_change_lines),
                'mean': statistics.mean(self.ai_change_lines),
                'stdev': statistics.stdev(self.ai_change_lines) if len(self.ai_change_lines) > 1 else 0,
                'median': statistics.median(self.ai_change_lines),
                'min': min(self.ai_change_lines),
                'max': max(self.ai_change_lines)
            }
        
        if self.human_change_lines:
            stats['human'] = {
                'count': len(self.human_change_lines),
                'mean': statistics.mean(self.human_change_lines),
                'stdev': statistics.stdev(self.human_change_lines) if len(self.human_change_lines) > 1 else 0,
                'median': statistics.median(self.human_change_lines),
                'min': min(self.human_change_lines),
                'max': max(self.human_change_lines)
            }
        
        return stats
    
    def calculate_file_statistics(self):
        """変更ファイル数の統計を計算"""
        stats = {}
        
        if self.ai_changed_files:
            stats['ai'] = {
                'count': len(self.ai_changed_files),
                'mean': statistics.mean(self.ai_changed_files),
                'stdev': statistics.stdev(self.ai_changed_files) if len(self.ai_changed_files) > 1 else 0,
                'median': statistics.median(self.ai_changed_files),
                'min': min(self.ai_changed_files),
                'max': max(self.ai_changed_files)
            }
        
        if self.human_changed_files:
            stats['human'] = {
                'count': len(self.human_changed_files),
                'mean': statistics.mean(self.human_changed_files),
                'stdev': statistics.stdev(self.human_changed_files) if len(self.human_changed_files) > 1 else 0,
                'median': statistics.median(self.human_changed_files),
                'min': min(self.human_changed_files),
                'max': max(self.human_changed_files)
            }
        
        return stats
    
    def generate_report(self):
        """統計レポートを生成（詳細結果は含まない）"""
        report = []
        report.append("=" * 80)
        report.append("AI vs Human Commit Analysis Report")
        report.append("=" * 80)
        report.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Source File: {os.path.basename(self.json_file_path)}")
        report.append("")
        
        # 総計
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Inducing Commits: {self.stats['total_commits']}")
        report.append(f"Successfully Processed: {self.stats['processed_commits']}")
        report.append(f"Failed to Analyze: {self.stats['failed_to_analyze']}")
        report.append("")
        
        # AI vs Human統計
        total_ai = self.stats['total_ai']
        human_commits = self.stats['human']
        total_analyzed = total_ai + human_commits
        
        if total_analyzed > 0:
            report.append("COMMIT TYPE DISTRIBUTION")
            report.append("-" * 40)
            report.append(f"AI Commits: {total_ai} ({total_ai/total_analyzed*100:.1f}%)")
            report.append(f"Human Commits: {human_commits} ({human_commits/total_analyzed*100:.1f}%)")
            report.append("")
            
            # AI種類別統計
            if total_ai > 0:
                report.append("AI TYPE BREAKDOWN")
                report.append("-" * 40)
                for key, count in self.stats.items():
                    if key.startswith('ai_') and count > 0:
                        ai_type = key.replace('ai_', '').replace('_', ' ').title()
                        percentage = count / total_ai * 100
                        report.append(f"{ai_type}: {count} ({percentage:.1f}% of AI commits)")
                report.append("")
        
        # 変更行数の統計
        change_stats = self.calculate_change_statistics()
        if change_stats:
            report.append("CODE CHANGE STATISTICS (Lines)")
            report.append("-" * 40)
            
            if 'ai' in change_stats:
                ai_stats = change_stats['ai']
                report.append(f"AI Commits:")
                report.append(f"  Count: {ai_stats['count']}")
                report.append(f"  Mean lines changed: {ai_stats['mean']:.2f}")
                report.append(f"  Standard deviation: {ai_stats['stdev']:.2f}")
                report.append(f"  Median: {ai_stats['median']:.0f}")
                report.append(f"  Range: {ai_stats['min']} - {ai_stats['max']}")
                report.append("")
            
            if 'human' in change_stats:
                human_stats = change_stats['human']
                report.append(f"Human Commits:")
                report.append(f"  Count: {human_stats['count']}")
                report.append(f"  Mean lines changed: {human_stats['mean']:.2f}")
                report.append(f"  Standard deviation: {human_stats['stdev']:.2f}")
                report.append(f"  Median: {human_stats['median']:.0f}")
                report.append(f"  Range: {human_stats['min']} - {human_stats['max']}")
                report.append("")
        
        # 変更ファイル数の統計
        file_stats = self.calculate_file_statistics()
        if file_stats:
            report.append("FILE CHANGE STATISTICS")
            report.append("-" * 40)
            
            if 'ai' in file_stats:
                ai_stats = file_stats['ai']
                report.append(f"AI Commits:")
                report.append(f"  Count: {ai_stats['count']}")
                report.append(f"  Mean files changed: {ai_stats['mean']:.2f}")
                report.append(f"  Standard deviation: {ai_stats['stdev']:.2f}")
                report.append(f"  Median: {ai_stats['median']:.0f}")
                report.append(f"  Range: {ai_stats['min']} - {ai_stats['max']}")
                report.append("")
            
            if 'human' in file_stats:
                human_stats = file_stats['human']
                report.append(f"Human Commits:")
                report.append(f"  Count: {human_stats['count']}")
                report.append(f"  Mean files changed: {human_stats['mean']:.2f}")
                report.append(f"  Standard deviation: {human_stats['stdev']:.2f}")
                report.append(f"  Median: {human_stats['median']:.0f}")
                report.append(f"  Range: {human_stats['min']} - {human_stats['max']}")
                report.append("")
        
        # 分析対象のリポジトリ一覧
        repos = set()
        for result in self.detailed_results:
            repos.add(result['repo_name'])
        
        if repos:
            report.append("ANALYZED REPOSITORIES")
            report.append("-" * 40)
            for repo in sorted(repos):
                repo_commits = [r for r in self.detailed_results if r['repo_name'] == repo]
                ai_commits = len([r for r in repo_commits if r['is_ai']])
                human_commits = len([r for r in repo_commits if not r['is_ai']])
                report.append(f"{repo}: {len(repo_commits)} commits (AI: {ai_commits}, Human: {human_commits})")
            report.append("")
        
        return "\n".join(report)
    
    def save_results(self, output_dir="../data_list/RQ2/final_result"):
        """結果をファイルに保存"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"commit_ai_analysis_{timestamp}.txt"
        output_path = os.path.join(output_dir, filename)
        
        report = self.generate_report()
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"Results saved to: {output_path}")
            return output_path
        except Exception as e:
            print(f"Error saving results: {e}")
            return None

def main():
    # JSONファイルのパス
    # ----------入力-------------------
    repo_name = "ai"
    json_file = rf"c:\Users\Shota\Local_document\AI-Code-Maintainability\pyszz_v2\out\{repo_name}_bic_config.json"

    if not os.path.exists(json_file):
        print(f"JSON file not found: {json_file}")
        return
    
    # 解析実行
    analyzer = CommitAnalyzer(json_file)
    print("Starting commit analysis...")
    analyzer.analyze_commits()
    
    # 結果保存
    output_path = analyzer.save_results()
    
    if output_path:
        print("\nAnalysis Summary:")
        print(f"Total commits: {analyzer.stats['total_commits']}")
        print(f"AI commits: {analyzer.stats['total_ai']}")
        print(f"Human commits: {analyzer.stats['human']}")
        print(f"Failed to analyze: {analyzer.stats['failed_to_analyze']}")
        
        # 変更行数統計の表示
        change_stats = analyzer.calculate_change_statistics()
        if 'ai' in change_stats and 'human' in change_stats:
            print(f"\nCode Change Statistics:")
            print(f"AI commits - Mean lines: {change_stats['ai']['mean']:.2f}, StdDev: {change_stats['ai']['stdev']:.2f}")
            print(f"Human commits - Mean lines: {change_stats['human']['mean']:.2f}, StdDev: {change_stats['human']['stdev']:.2f}")
        
        # 変更ファイル数統計の表示
        file_stats = analyzer.calculate_file_statistics()
        if 'ai' in file_stats and 'human' in file_stats:
            print(f"\nFile Change Statistics:")
            print(f"AI commits - Mean files: {file_stats['ai']['mean']:.2f}, StdDev: {file_stats['ai']['stdev']:.2f}")
            print(f"Human commits - Mean files: {file_stats['human']['mean']:.2f}, StdDev: {file_stats['human']['stdev']:.2f}")

if __name__ == "__main__":
    main()