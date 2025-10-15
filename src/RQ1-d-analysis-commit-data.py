"""
AI
"""

import pandas as pd
import numpy as np
from datetime import datetime
import statistics
from collections import defaultdict, Counter

def analyze_commit_data(csv_file_path):
    # CSVファイルを読み込み
    df = pd.read_csv(csv_file_path)
    
    # commit_dateを日時型に変換
    df['commit_date'] = pd.to_datetime(df['commit_date'])
    
    # original_commit_type別にデータを分割
    ai_df = df[df['original_commit_type'] == 'AI']
    human_df = df[df['original_commit_type'] == 'Human']
    
    results = []
    results.append("AutoGPT Commit Classification Analysis Results (by Original Commit Type)")
    results.append("=" * 70)
    results.append("")
    
    # 全体の統計
    results.append("OVERALL STATISTICS")
    results.append("-" * 30)
    results.append(f"Total commits: {len(df)}")
    results.append(f"AI-originated commits: {len(ai_df)} ({len(ai_df)/len(df)*100:.1f}%)")
    results.append(f"Human-originated commits: {len(human_df)} ({len(human_df)/len(df)*100:.1f}%)")
    results.append(f"Total unique files: {df['file_path'].nunique()}")
    results.append("")
    
    # is_ai_generated統計も追加
    results.append("COMMIT AUTHORSHIP STATISTICS")
    results.append("-" * 30)
    ai_generated_commits = len(df[df['is_ai_generated'] == True])
    human_generated_commits = len(df[df['is_ai_generated'] == False])
    results.append(f"AI-generated commits: {ai_generated_commits} ({ai_generated_commits/len(df)*100:.1f}%)")
    results.append(f"Human-generated commits: {human_generated_commits} ({human_generated_commits/len(df)*100:.1f}%)")
    results.append("")

    def analyze_subset(subset_df, label):
        if len(subset_df) == 0:
            return [f"No {label} commits found"]
        
        analysis = []
        analysis.append(f"{label.upper()} COMMITS ANALYSIS")
        analysis.append("-" * 30)
        
        # 1. ファイルあたりのコミット数とその統計
        commits_per_file = subset_df.groupby('file_path').size()
        analysis.append(f"1. Commits per file statistics:")
        analysis.append(f"   Average commits per file: {commits_per_file.mean():.2f}")
        analysis.append(f"   Standard deviation: {commits_per_file.std():.2f}")
        analysis.append(f"   Min commits per file: {commits_per_file.min()}")
        analysis.append(f"   Max commits per file: {commits_per_file.max()}")
        analysis.append("")
        
        # 2. ファイルあたりのclassification_labelの分類割合
        analysis.append(f"2. Classification label distribution per file:")
        file_label_dist = {}
        for file_path in subset_df['file_path'].unique():
            file_commits = subset_df[subset_df['file_path'] == file_path]
            label_counts = file_commits['classification_label'].value_counts()
            total_commits = len(file_commits)
            file_label_dist[file_path] = {label: count/total_commits*100 
                                        for label, count in label_counts.items()}
        
        # 平均的な分類割合を計算
        all_labels = set()
        for dist in file_label_dist.values():
            all_labels.update(dist.keys())
        
        avg_label_dist = {}
        for label in all_labels:
            percentages = [dist.get(label, 0) for dist in file_label_dist.values()]
            avg_label_dist[label] = np.mean(percentages)
        
        for label, avg_pct in sorted(avg_label_dist.items()):
            analysis.append(f"   {label}: {avg_pct:.1f}% (average across files)")
        analysis.append("")
        
        # 3. 全体のclassification_labelの分類割合
        analysis.append(f"3. Overall classification label distribution:")
        overall_labels = subset_df['classification_label'].value_counts()
        for label, count in overall_labels.items():
            percentage = count / len(subset_df) * 100
            analysis.append(f"   {label}: {count} commits ({percentage:.1f}%)")
        analysis.append("")
        
        # 4. ファイルあたりのコミット頻度分析
        analysis.append(f"4. Commit frequency analysis per file:")
        file_frequencies = []
        
        for file_path in subset_df['file_path'].unique():
            file_commits = subset_df[subset_df['file_path'] == file_path].sort_values('commit_date')
            if len(file_commits) > 1:
                dates = file_commits['commit_date'].tolist()
                time_diffs = []
                for i in range(1, len(dates)):
                    diff_days = (dates[i] - dates[i-1]).days
                    if diff_days > 0:  # 同日のコミットは除外
                        time_diffs.append(diff_days)
                
                if time_diffs:
                    avg_interval = np.mean(time_diffs)
                    file_frequencies.append(avg_interval)
        
        if file_frequencies:
            analysis.append(f"   Average interval between commits: {np.mean(file_frequencies):.1f} days")
            analysis.append(f"   Standard deviation: {np.std(file_frequencies):.1f} days")
        else:
            analysis.append(f"   Insufficient data for frequency analysis")
        analysis.append("")
        
        # 5. is_ai_generated統計（サブセット内）
        analysis.append(f"5. Commit authorship within {label} commits:")
        ai_generated_in_subset = len(subset_df[subset_df['is_ai_generated'] == True])
        human_generated_in_subset = len(subset_df[subset_df['is_ai_generated'] == False])
        analysis.append(f"   AI-generated commits: {ai_generated_in_subset} ({ai_generated_in_subset/len(subset_df)*100:.1f}%)")
        analysis.append(f"   Human-generated commits: {human_generated_in_subset} ({human_generated_in_subset/len(subset_df)*100:.1f}%)")
        analysis.append("")
        
        return analysis
    
    # AI起源コミットの分析
    results.extend(analyze_subset(ai_df, "AI-Originated"))
    results.append("")
    
    # 人間起源コミットの分析
    results.extend(analyze_subset(human_df, "Human-Originated"))
    results.append("")
    
    # 比較分析
    results.append("COMPARATIVE ANALYSIS")
    results.append("-" * 30)
    
    if len(ai_df) > 0 and len(human_df) > 0:
        ai_commits_per_file = ai_df.groupby('file_path').size()
        human_commits_per_file = human_df.groupby('file_path').size()
        
        results.append("Average commits per file comparison:")
        results.append(f"   AI-originated: {ai_commits_per_file.mean():.2f}")
        results.append(f"   Human-originated: {human_commits_per_file.mean():.2f}")
        results.append("")
        
        # 最も活発なファイル
        ai_most_active = ai_commits_per_file.idxmax() if len(ai_commits_per_file) > 0 else "N/A"
        human_most_active = human_commits_per_file.idxmax() if len(human_commits_per_file) > 0 else "N/A"
        
        results.append("Most active files:")
        if ai_most_active != "N/A":
            results.append(f"   AI-originated: {ai_most_active} ({ai_commits_per_file.max()} commits)")
        if human_most_active != "N/A":
            results.append(f"   Human-originated: {human_most_active} ({human_commits_per_file.max()} commits)")
    
    return results

def main():
    #--------入力-----------------------
    repo_name = "ai"
    csv_file_path = rf"c:\Users\Shota\Local_document\AI-Code-Maintainability\data_list\RQ1\final_result\{repo_name}_commit_classification_results.csv"
    output_file_path = rf"c:\Users\Shota\Local_document\AI-Code-Maintainability\data_list\RQ1\final_result\{repo_name}_commit_analysis_results.txt"
    
    try:
        # 分析実行
        results = analyze_commit_data(csv_file_path)
        
        # 結果をファイルに保存
        with open(output_file_path, 'w', encoding='utf-8') as f:
            for line in results:
                f.write(line + '\n')
        
        print(f"Analysis completed successfully!")
        print(f"Results saved to: {output_file_path}")
        
        # 結果をコンソールにも表示
        print("\n" + "="*60)
        print("ANALYSIS RESULTS PREVIEW:")
        print("="*60)
        for line in results[:20]:  # 最初の20行を表示
            print(line)
        print("...")
        print(f"Full results saved to {output_file_path}")
        
    except Exception as e:
        print(f"Error occurred during analysis: {str(e)}")
        print(f"Please check if the CSV file exists at: {csv_file_path}")

if __name__ == "__main__":
    main()