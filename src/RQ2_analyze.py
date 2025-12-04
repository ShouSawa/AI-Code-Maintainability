import pandas as pd
import matplotlib.pyplot as plt
import os
from datetime import datetime

def analyze_rq2():
    """
    RQ2: AI作成ファイルの保守は誰が行っているのかを分析
    
    入力: results_v4.csv
    出力: 
        - results/RQ2_results.txt
        - results/RQ2_pieChart_AI.png
        - results/RQ2_pieChart_Human.png
    """
    
    # パス設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "../results/results_v4.csv")
    output_dir = os.path.join(script_dir, "../results")
    os.makedirs(output_dir, exist_ok=True)
    
    output_txt_path = os.path.join(output_dir, "RQ2_results.txt")
    
    print(f"読み込み中: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"CSV読み込みエラー: {e}")
        return

    # 結果格納用リスト
    results_text = []
    results_text.append("RQ2 分析結果: AI作成ファイルの保守主体分析")
    results_text.append("=" * 60)
    results_text.append(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    results_text.append("")

    # ---------------------------------------------------------
    # 1. AI作成ファイルに対するコミット分析
    # ---------------------------------------------------------
    print("AI作成ファイルの分析中...")
    
    ai_files_df = df[df['file_created_by'] == 'AI']
    ai_commit_counts = ai_files_df['commit_created_by'].value_counts()
    
    ai_total_commits = ai_commit_counts.sum()
    ai_ai_commits = ai_commit_counts.get('AI', 0)
    ai_human_commits = ai_commit_counts.get('Human', 0)
    
    ai_ai_ratio = (ai_ai_commits / ai_total_commits * 100) if ai_total_commits > 0 else 0
    ai_human_ratio = (ai_human_commits / ai_total_commits * 100) if ai_total_commits > 0 else 0
    
    results_text.append("1. AI作成ファイルに対するコミット内訳")
    results_text.append("-" * 40)
    results_text.append(f"総コミット数: {ai_total_commits}")
    results_text.append(f"AIによるコミット: {ai_ai_commits} ({ai_ai_ratio:.2f}%)")
    results_text.append(f"人間によるコミット: {ai_human_commits} ({ai_human_ratio:.2f}%)")
    results_text.append("")

    # 円グラフ作成 (AI作成ファイル)
    create_pie_chart(
        counts=[ai_ai_commits, ai_human_commits],
        labels=['AI', 'Human'],
        title="AI-Created Files",
        output_path=os.path.join(output_dir, "RQ2_pieChart_AI.png")
    )

    # ---------------------------------------------------------
    # 2. 人間作成ファイルに対するコミット分析
    # ---------------------------------------------------------
    print("人間作成ファイルの分析中...")
    
    human_files_df = df[df['file_created_by'] == 'Human']
    human_commit_counts = human_files_df['commit_created_by'].value_counts()
    
    human_total_commits = human_commit_counts.sum()
    human_ai_commits = human_commit_counts.get('AI', 0)
    human_human_commits = human_commit_counts.get('Human', 0)
    
    human_ai_ratio = (human_ai_commits / human_total_commits * 100) if human_total_commits > 0 else 0
    human_human_ratio = (human_human_commits / human_total_commits * 100) if human_total_commits > 0 else 0
    
    results_text.append("2. 人間作成ファイルに対するコミット内訳")
    results_text.append("-" * 40)
    results_text.append(f"総コミット数: {human_total_commits}")
    results_text.append(f"AIによるコミット: {human_ai_commits} ({human_ai_ratio:.2f}%)")
    results_text.append(f"人間によるコミット: {human_human_commits} ({human_human_ratio:.2f}%)")
    results_text.append("")

    # 円グラフ作成 (人間作成ファイル)
    create_pie_chart(
        counts=[human_ai_commits, human_human_commits],
        labels=['AI', 'Human'],
        title="Human-Created Files",
        output_path=os.path.join(output_dir, "RQ2_pieChart_Human.png")
    )

    # 結果保存
    with open(output_txt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(results_text))
    
    print(f"分析完了。結果を保存しました: {output_txt_path}")
    print(f"グラフを保存しました: {output_dir}")

def create_pie_chart(counts, labels, title, output_path):
    """
    円グラフを作成して保存する
    """
    plt.figure(figsize=(8, 8))
    
    # 色の設定 (AI: 赤系, Human: 青系)
    colors = ['#FF9999', '#99CCFF']
    
    # データが0の場合は表示しないための処理
    filtered_counts = []
    filtered_labels = []
    filtered_colors = []
    
    for count, label, color in zip(counts, labels, colors):
        if count > 0:
            filtered_counts.append(count)
            filtered_labels.append(label)
            filtered_colors.append(color)
            
    if not filtered_counts:
        print(f"警告: プロット用データがありません - {output_path}")
        plt.close()
        return

    # パーセンテージと件数を表示するための関数
    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct*total/100.0))
            return '{v:d}\n({p:.1f}%)'.format(v=val, p=pct)
        return my_autopct

    plt.pie(
        filtered_counts, 
        labels=filtered_labels, 
        colors=filtered_colors, 
        autopct=make_autopct(filtered_counts), 
        startangle=90, 
        counterclock=False,
        wedgeprops={'edgecolor': 'white'},
        textprops={'fontsize': 16}
    )
    
    plt.title(title, fontsize=20)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

if __name__ == "__main__":
    analyze_rq2()
