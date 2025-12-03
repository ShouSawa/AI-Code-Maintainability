import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns # Pythonデータを可視化するためのライブラリ，バイオリンプロットに使用
import os
from datetime import datetime, timedelta

def analyze_rq1():
    """
    RQ1: AIが生成したファイルはどの程度保守されているのかを分析
    
    入力: results_v4.csv
    出力: 
        - results/RQ1_results.txt
        - results/RQ1_violinPlot_count.png
        - results/RQ1_violinPlot_frequency_weekly.png
        - results/RQ1_violinPlot_frequency_monthly.png
    """
    
    # パス設定
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, "../results/results_v4.csv")
    output_dir = os.path.join(script_dir, "../results")
    os.makedirs(output_dir, exist_ok=True)
    
    output_txt_path = os.path.join(output_dir, "RQ1_results.txt")
    
    print(f"読み込み中: {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"CSV読み込みエラー: {e}")
        return

    # 日付変換（タイムゾーンを削除して統一）
    df['commit_date'] = pd.to_datetime(df['commit_date']).dt.tz_localize(None)
    df['file_creation_date'] = pd.to_datetime(df['file_creation_date']).dt.tz_localize(None)
    
    # 分析終了日
    analysis_end_date = pd.to_datetime("2025-10-31")

    # ファイル単位のデータフレーム作成
    # file_name, repository_name, file_created_by でユニークにする
    files_df = df[['repository_name', 'file_name', 'file_created_by', 'file_creation_date']].drop_duplicates()
    
    # 結果格納用リスト
    results_text = []
    results_text.append("RQ1 分析結果: AI生成ファイルの保守性分析")
    results_text.append("=" * 60)
    results_text.append(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    results_text.append(f"分析対象期間: ～ 2025/10/31")
    results_text.append("")

    # ---------------------------------------------------------
    # 1. コミット数の分析
    # ---------------------------------------------------------
    print("コミット数の分析中...")
    
    # 各ファイルのコミット数を計算
    commit_counts = df.groupby(['repository_name', 'file_name', 'file_created_by']).size().reset_index(name='commit_count')
    
    # コミット数が0のファイルも考慮する必要があるが、results_v4.csvはコミット履歴ベースなので、
    # 少なくとも1回（作成時）のコミットが含まれているはず。
    # ただし、作成時のコミットが含まれていない場合（履歴取得の仕様による）は0になる可能性があるが、
    # 今回のデータセットはコミット履歴から作られているので、ここに現れるファイルは少なくとも1コミットある。
    
    ai_commit_counts = commit_counts[commit_counts['file_created_by'] == 'AI']['commit_count']
    human_commit_counts = commit_counts[commit_counts['file_created_by'] == 'Human']['commit_count']
    
    def get_stats(data, label):
        return {
            'label': label,
            'count': len(data),
            'sum': data.sum(),
            'mean': data.mean(),
            'min': data.min(),
            'max': data.max(),
            'median': data.median(),
            'std': data.std()
        }

    ai_stats_count = get_stats(ai_commit_counts, "AI作成ファイル")
    human_stats_count = get_stats(human_commit_counts, "人間作成ファイル")
    
    results_text.append("1. コミット数の分析")
    results_text.append("-" * 40)
    
    for stats in [ai_stats_count, human_stats_count]:
        results_text.append(f"■ {stats['label']}")
        results_text.append(f"  ファイル数: {stats['count']}")
        results_text.append(f"  総コミット数: {stats['sum']}")
        results_text.append(f"  平均値: {stats['mean']:.2f}")
        results_text.append(f"  最小値: {stats['min']}")
        results_text.append(f"  最大値: {stats['max']}")
        results_text.append(f"  中央値: {stats['median']}")
        results_text.append(f"  標準偏差: {stats['std']:.2f}")
        results_text.append("")

    # バイオリンプロット作成 (コミット数)
    create_violin_plot(
        data_ai=ai_commit_counts,
        data_human=human_commit_counts,
        title="Distribution of Commit Counts per File",
        ylabel="Number of Commits",
        output_path=os.path.join(output_dir, "RQ1_violinPlot_count.png")
    )

    # ---------------------------------------------------------
    # 2. コミット頻度の分析 (1週間ごと & 1か月ごと)
    # ---------------------------------------------------------
    print("コミット頻度の分析中...")
    
    # 各ファイルごとの期間別コミット数の中央値を計算
    ai_weekly_medians = []
    ai_monthly_medians = []
    human_weekly_medians = []
    human_monthly_medians = []
    
    # ファイルごとに処理
    # repository_nameとfile_nameでグルーピングして処理
    grouped = df.groupby(['repository_name', 'file_name', 'file_created_by', 'file_creation_date'])
    
    for (repo, file_name, creator, creation_date), group in grouped:
        # コミット日付のリスト
        commit_dates = group['commit_date'].sort_values()
        
        # 期間ごとの集計
        weekly_median = calculate_period_median(commit_dates, creation_date, analysis_end_date, days=7)
        monthly_median = calculate_period_median(commit_dates, creation_date, analysis_end_date, days=30)
        
        if creator == 'AI':
            if weekly_median is not None: ai_weekly_medians.append(weekly_median)
            if monthly_median is not None: ai_monthly_medians.append(monthly_median)
        else:
            if weekly_median is not None: human_weekly_medians.append(weekly_median)
            if monthly_median is not None: human_monthly_medians.append(monthly_median)
            
    # 統計計算
    ai_weekly_stats = get_stats(pd.Series(ai_weekly_medians), "AI作成ファイル (週間)")
    human_weekly_stats = get_stats(pd.Series(human_weekly_medians), "人間作成ファイル (週間)")
    
    ai_monthly_stats = get_stats(pd.Series(ai_monthly_medians), "AI作成ファイル (月間)")
    human_monthly_stats = get_stats(pd.Series(human_monthly_medians), "人間作成ファイル (月間)")
    
    results_text.append("2. コミット頻度の分析 (各ファイルの期間ごとのコミット数の中央値の統計)")
    results_text.append("-" * 40)
    
    results_text.append("■ 1週間ごとの頻度")
    for stats in [ai_weekly_stats, human_weekly_stats]:
        results_text.append(f"  [{stats['label']}]")
        results_text.append(f"  対象ファイル数: {stats['count']}")
        results_text.append(f"  平均値: {stats['mean']:.4f}")
        results_text.append(f"  最小値: {stats['min']}")
        results_text.append(f"  最大値: {stats['max']}")
        results_text.append(f"  中央値: {stats['median']}")
        results_text.append(f"  標準偏差: {stats['std']:.4f}")
        results_text.append("")
        
    results_text.append("■ 1か月ごとの頻度")
    for stats in [ai_monthly_stats, human_monthly_stats]:
        results_text.append(f"  [{stats['label']}]")
        results_text.append(f"  対象ファイル数: {stats['count']}")
        results_text.append(f"  平均値: {stats['mean']:.4f}")
        results_text.append(f"  最小値: {stats['min']}")
        results_text.append(f"  最大値: {stats['max']}")
        results_text.append(f"  中央値: {stats['median']}")
        results_text.append(f"  標準偏差: {stats['std']:.4f}")
        results_text.append("")

    # バイオリンプロット作成 (週間頻度)
    create_violin_plot(
        data_ai=pd.Series(ai_weekly_medians),
        data_human=pd.Series(human_weekly_medians),
        title="Distribution of Weekly Commit Frequency (Median per File)",
        ylabel="Median Commits per Week",
        output_path=os.path.join(output_dir, "RQ1_violinPlot_frequency_weekly.png")
    )
    
    # バイオリンプロット作成 (月間頻度)
    create_violin_plot(
        data_ai=pd.Series(ai_monthly_medians),
        data_human=pd.Series(human_monthly_medians),
        title="Distribution of Monthly Commit Frequency (Median per File)",
        ylabel="Median Commits per Month",
        output_path=os.path.join(output_dir, "RQ1_violinPlot_frequency_monthly.png")
    )

    # 結果保存
    with open(output_txt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(results_text))
    
    print(f"分析完了。結果を保存しました: {output_txt_path}")
    print(f"グラフを保存しました: {output_dir}")

def calculate_period_median(commit_dates, start_date, end_date, days):
    """
    指定期間ごとのコミット数を集計し、その中央値を返す
    """
    if pd.isna(start_date):
        # 作成日が不明な場合は最初のコミット日を使用
        start_date = commit_dates.min()
        
    current_date = start_date
    counts = []
    
    # 期間が終了日を超えるまでループ
    while current_date + timedelta(days=days) <= end_date:
        next_date = current_date + timedelta(days=days)
        # 期間内のコミット数をカウント
        count = ((commit_dates >= current_date) & (commit_dates < next_date)).sum()
        counts.append(count)
        current_date = next_date
        
    if not counts:
        return None
        
    return np.median(counts)

def create_violin_plot(data_ai, data_human, title, ylabel, output_path):
    """
    バイオリンプロットを作成して保存する
    """
    # 縦長に変更 (幅6, 高さ12)
    plt.figure(figsize=(6, 12))
    
    # データフレーム形式に変換（seaborn用）
    df_ai = pd.DataFrame({'Value': data_ai, 'Type': 'AI'})
    df_human = pd.DataFrame({'Value': data_human, 'Type': 'Human'})
    df_plot = pd.concat([df_ai, df_human], ignore_index=True)
    
    # データが空の場合はスキップ
    if len(df_plot) == 0:
        print(f"警告: プロット用データがありません - {output_path}")
        return

    # スタイル設定
    sns.set_style("whitegrid")
    
    # ダミーのx軸を設定
    df_plot['Dummy'] = "All Files"
    
    # 1. バイオリンプロット（中身なし、split=True）
    ax = sns.violinplot(
        data=df_plot, 
        x='Dummy', 
        y='Value', 
        hue='Type', 
        split=True, 
        inner=None, # 中身を描かない
        palette={"AI": "#FF9999", "Human": "#99CCFF"}
    )
    
    # 2. 箱ひげ図を重ねる
    # widthを小さくしてバイオリンの中に収まるようにする
    sns.boxplot(
        data=df_plot, 
        x='Dummy', 
        y='Value', 
        hue='Type',
        width=1, # 幅を狭く設定
        fliersize=0, # 外れ値（点）は表示しない（バイオリンで分布が見えるため）
        palette={"AI": "#FF9999", "Human": "#99CCFF"},
        ax=ax,
        boxprops={'alpha': 0.8} # 半透明
    )
    
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xlabel("") # x軸ラベルは不要
    
    # 凡例の整理（重複を防ぐため、最初の2つだけ表示）
    handles, labels = ax.get_legend_handles_labels()
    plt.legend(handles[:2], labels[:2], title="")
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

if __name__ == "__main__":
    analyze_rq1()
