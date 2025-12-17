import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns # Pythonデータを可視化するためのライブラリ，バイオリンプロットに使用
import os
from datetime import datetime, timedelta
from scipy.stats import mannwhitneyu

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
    
    output_txt_path = os.path.join(output_dir, "RQ1_results_3months.txt")
    
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

    # ---------------------------------------------------------
    # 1. 全期間の分析
    # ---------------------------------------------------------
    print("\n=== 全期間の分析を開始します ===")
    run_analysis_process(df, output_dir, analysis_end_date, suffix="")

    # ---------------------------------------------------------
    # 2. 3ヶ月（90日）以内のデータに限定した分析
    # ---------------------------------------------------------
    print("\n=== 3ヶ月以内の分析を開始します ===")
    print("分析対象をファイル作成から3ヶ月以内に限定します。")
    df_3months = df.copy()
    df_3months['days_diff'] = (df_3months['commit_date'] - df_3months['file_creation_date']).dt.days
    # 作成日(0日)〜90日後まで
    df_3months = df_3months[(df_3months['days_diff'] >= 0) & (df_3months['days_diff'] <= 90)].copy()
    
    run_analysis_process(df_3months, output_dir, analysis_end_date, suffix="_3months", is_limited_period=True)

def perform_mannwhitneyu(data1, data2, label):
    """Mann-Whitney U検定を実行して結果文字列を返す"""
    try:
        # データが空の場合は検定できない
        if len(data1) == 0 or len(data2) == 0:
            return f"■ {label}の検定: データ不足のため実行不可\n"
            
        statistic, p_value = mannwhitneyu(data1, data2, alternative='two-sided')
        result = f"■ {label}のMann-Whitney U検定結果\n"
        result += f"  検定統計量 U: {statistic}\n"
        result += f"  p値: {p_value}\n"
        if p_value < 0.01:
            result += "  判定: ** 1%水準で有意差あり\n"
        elif p_value < 0.05:
            result += "  判定: * 5%水準で有意差あり\n"
        else:
            result += "  判定: 有意差なし\n"
        return result
    except Exception as e:
        return f"■ {label}の検定エラー: {e}\n"

def run_analysis_process(df, output_dir, analysis_end_date, suffix="", is_limited_period=False):
    """
    分析プロセスを実行する関数
    """
    output_txt_path = os.path.join(output_dir, f"RQ1_results{suffix}.txt")
    
    # 結果格納用リスト
    results_text = []
    title_suffix = " (作成から3ヶ月間限定)" if is_limited_period else ""
    period_text = "作成日 ～ 作成日+90日" if is_limited_period else "～ 2025/10/31"
    
    results_text.append(f"RQ1 分析結果: AI生成ファイルの保守性分析{title_suffix}")
    results_text.append("=" * 60)
    results_text.append(f"分析日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    results_text.append(f"分析対象期間: {period_text}")
    results_text.append("")

    # ---------------------------------------------------------
    # 1. コミット数の分析
    # ---------------------------------------------------------
    print(f"[{suffix}] コミット数の分析中...")
    
    # 各ファイルのコミット数を計算
    commit_counts = df.groupby(['repository_name', 'file_name', 'file_created_by']).size().reset_index(name='commit_count')
    
    # AI作成ファイルと人間作成ファイルのコミット数を取得
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

    # 有意差検定 (コミット数)
    results_text.append(perform_mannwhitneyu(ai_commit_counts, human_commit_counts, "コミット数"))
    results_text.append("")

    # バイオリンプロット作成 (コミット数) - 単体出力はスキップ
    # create_violin_plot(
    #     data_ai=ai_commit_counts,
    #     data_human=human_commit_counts,
    #     title="Counts",
    #     ylabel="Number of Commits",
    #     output_path=os.path.join(output_dir, f"RQ1_violinPlot_count{suffix}.png"),
    #     ylim=20
    # )

    # ---------------------------------------------------------
    # 2. コミット頻度の分析 (1週間ごと & 1か月ごと)
    # ---------------------------------------------------------
    print(f"[{suffix}] コミット頻度の分析中...")
    
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
        if is_limited_period:
            # 3ヶ月限定の場合: 終了日は作成日+90日、ただし分析全体の終了日を超えないようにする
            target_end_date = creation_date + timedelta(days=90)
            actual_end_date = min(target_end_date, analysis_end_date)
        else:
            # 全期間の場合
            actual_end_date = analysis_end_date
        
        weekly_median = calculate_period_median(commit_dates, creation_date, actual_end_date, days=7)
        monthly_median = calculate_period_median(commit_dates, creation_date, actual_end_date, days=30)
        
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

    # 有意差検定 (週間頻度)
    results_text.append(perform_mannwhitneyu(ai_weekly_medians, human_weekly_medians, "週間コミット頻度"))
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

    # 有意差検定 (月間頻度)
    results_text.append(perform_mannwhitneyu(ai_monthly_medians, human_monthly_medians, "月間コミット頻度"))
    results_text.append("")

    # ---------------------------------------------------------
    # 3. 時系列でのコミット数推移 (追加)
    # ---------------------------------------------------------
    print(f"[{suffix}] 時系列推移の分析中...")
    
    # 経過日数を計算
    df_ts = df.copy()
    df_ts['days_diff'] = (df_ts['commit_date'] - df_ts['file_creation_date']).dt.days
    
    # 週番号 (0始まり: 0-6日がWeek 1)
    df_ts['week_num'] = df_ts['days_diff'] // 7
    # 月番号 (0始まり: 0-29日がMonth 1)
    df_ts['month_num'] = df_ts['days_diff'] // 30
    
    # ユニークなファイルIDを作成
    df_ts['file_id'] = df_ts['repository_name'] + "::" + df_ts['file_name']
    
    # 全ファイルリストと作成者情報のマッピング
    file_creators = df_ts[['file_id', 'file_created_by']].drop_duplicates().set_index('file_id')['file_created_by']
    
    # --- 週次集計 ---
    # ファイルごと、週ごとのコミット数
    weekly_counts = df_ts.groupby(['file_id', 'week_num']).size().unstack(fill_value=0)
    
    # 期間制限がある場合はその期間まで、ない場合はデータが存在する最大まで
    # 3ヶ月限定なら13週程度、全期間なら最大52週(1年)まで表示するように制限
    max_week_limit = 13 if is_limited_period else 52
    max_week_data = weekly_counts.columns.max() if not weekly_counts.empty else 0
    max_week = min(max_week_limit, max_week_data)
    
    target_weeks = range(int(max_week) + 1)
    weekly_counts = weekly_counts.reindex(columns=target_weeks, fill_value=0)
    
    # AI/Humanに分割
    ai_files = file_creators[file_creators == 'AI'].index
    human_files = file_creators[file_creators == 'Human'].index
    
    ai_weekly_df = weekly_counts.loc[weekly_counts.index.intersection(ai_files)]
    human_weekly_df = weekly_counts.loc[weekly_counts.index.intersection(human_files)]
    
    results_text.append("3. 時系列でのコミット数推移")
    results_text.append("-" * 40)
    
    results_text.append(f"■ 週次推移 (Week 1 = 最初の7日間, 最大Week {max_week+1}まで表示)")
    results_text.append(f"{'Week':<6} | {'AI Mean':<10} | {'AI Median':<10} | {'Human Mean':<10} | {'Human Median':<10}")
    results_text.append("-" * 60)
    
    for w in target_weeks:
        ai_col = ai_weekly_df[w] if w in ai_weekly_df.columns else pd.Series([], dtype=float)
        human_col = human_weekly_df[w] if w in human_weekly_df.columns else pd.Series([], dtype=float)
        
        ai_mean = ai_col.mean() if not ai_col.empty else 0
        ai_median = ai_col.median() if not ai_col.empty else 0
        human_mean = human_col.mean() if not human_col.empty else 0
        human_median = human_col.median() if not human_col.empty else 0
        
        results_text.append(f"{w+1:<2}週間目| {ai_mean:<10.4f} | {ai_median:<10.1f} | {human_mean:<10.4f} | {human_median:<10.1f}")
    results_text.append("")

    # 週次推移の箱ひげ図を作成
    print(f"[{suffix}] 週次推移グラフの作成中...")
    create_weekly_trend_boxplot(
        ai_weekly_df, 
        human_weekly_df, 
        os.path.join(output_dir, f"RQ1_weekly_trend_boxplot{suffix}.png")
    )

    # --- 月次集計 ---
    # ファイルごと、月ごとのコミット数
    monthly_counts = df_ts.groupby(['file_id', 'month_num']).size().unstack(fill_value=0)
    
    # 3ヶ月限定なら3ヶ月、全期間なら最大24ヶ月(2年)まで表示
    max_month_limit = 3 if is_limited_period else 24
    max_month_data = monthly_counts.columns.max() if not monthly_counts.empty else 0
    max_month = min(max_month_limit, max_month_data)
    
    target_months = range(int(max_month) + 1)
    monthly_counts = monthly_counts.reindex(columns=target_months, fill_value=0)
    
    ai_monthly_df = monthly_counts.loc[monthly_counts.index.intersection(ai_files)]
    human_monthly_df = monthly_counts.loc[monthly_counts.index.intersection(human_files)]
    
    results_text.append(f"■ 月次推移 (Month 1 = 最初の30日間, 最大Month {max_month+1}まで表示)")
    results_text.append(f"{'Month':<6} | {'AI Mean':<10} | {'AI Median':<10} | {'Human Mean':<10} | {'Human Median':<10}")
    results_text.append("-" * 60)
    
    for m in target_months:
        ai_col = ai_monthly_df[m] if m in ai_monthly_df.columns else pd.Series([], dtype=float)
        human_col = human_monthly_df[m] if m in human_monthly_df.columns else pd.Series([], dtype=float)
        
        ai_mean = ai_col.mean() if not ai_col.empty else 0
        ai_median = ai_col.median() if not ai_col.empty else 0
        human_mean = human_col.mean() if not human_col.empty else 0
        human_median = human_col.median() if not human_col.empty else 0
        
        results_text.append(f"{m+1:<6} | {ai_mean:<10.4f} | {ai_median:<10.1f} | {human_mean:<10.4f} | {human_median:<10.1f}")
    results_text.append("")

    # バイオリンプロット作成 (週間頻度) - 単体出力はスキップ
    # create_violin_plot(
    #     data_ai=pd.Series(ai_weekly_medians),
    #     data_human=pd.Series(human_weekly_medians),
    #     title="Frequency\n(Week)",
    #     ylabel="Median Commits per Week",
    #     output_path=os.path.join(output_dir, f"RQ1_violinPlot_frequency_weekly{suffix}.png"),
    #     ylim=0.2
    # )
    
    # バイオリンプロット作成 (月間頻度) - 単体出力はスキップ
    # create_violin_plot(
    #     data_ai=pd.Series(ai_monthly_medians),
    #     data_human=pd.Series(human_monthly_medians),
    #     title="Frequency\n(Month)",
    #     ylabel="Median Commits per Month",
    #     output_path=os.path.join(output_dir, f"RQ1_violinPlot_frequency_monthly{suffix}.png"),
    #     ylim=3
    # )

    # ---------------------------------------------------------
    # 3. まとめたバイオリンプロットの作成
    # ---------------------------------------------------------
    print(f"[{suffix}] 結合グラフの作成中...")
    
    # ylimの設定
    ylim_weekly = 0.6 if is_limited_period else 0.2
    ylim_monthly = 5.0 if is_limited_period else 3.0
    
    combined_data = [
        {
            'ai': ai_commit_counts,
            'human': human_commit_counts,
            'xlabel': "Count",
            'ylabel': "Number of Commits",
            'ylim': 20
        },
        {
            'ai': pd.Series(ai_weekly_medians),
            'human': pd.Series(human_weekly_medians),
            'xlabel': "Frequency\n(Week)",
            'ylabel': "Median Commits per Week",
            'ylim': ylim_weekly
        },
        {
            'ai': pd.Series(ai_monthly_medians),
            'human': pd.Series(human_monthly_medians),
            'xlabel': "Frequency\n(Month)",
            'ylabel': "Median Commits per Month",
            'ylim': ylim_monthly
        }
    ]
    
    create_combined_violin_plot(
        dataset_list=combined_data,
        output_path=os.path.join(output_dir, f"RQ1_violinPlot_combined{suffix}.png")
    )

    # ylabelなしバージョンの作成
    print(f"[{suffix}] 結合グラフ（ylabelなし）の作成中...")
    combined_data_no_ylabel = []
    for item in combined_data:
        new_item = item.copy()
        new_item['ylabel'] = "" # ylabelを空にする
        combined_data_no_ylabel.append(new_item)

    create_combined_violin_plot(
        dataset_list=combined_data_no_ylabel,
        output_path=os.path.join(output_dir, f"RQ1_violinPlot_combined{suffix}_no_ylabel.png")
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

def draw_violin_on_ax(ax, data_ai, data_human, xlabel, ylabel, ylim=None, show_legend=True):
    """
    指定されたAxesオブジェクトにバイオリンプロットを描画する
    """
    # データフレーム形式に変換（seaborn用）
    df_ai = pd.DataFrame({'Value': data_ai, 'Type': 'AI'})
    df_human = pd.DataFrame({'Value': data_human, 'Type': 'Human'})
    df_plot = pd.concat([df_ai, df_human], ignore_index=True)
    
    # データが空の場合はスキップ
    if len(df_plot) == 0:
        return

    # ダミーのx軸を設定（split=Trueで左右に結合させるため）
    df_plot['Dummy'] = "All Files"
    
    # 1. バイオリンプロット
    sns.violinplot(
        data=df_plot, 
        x='Dummy', 
        y='Value', 
        hue='Type', 
        split=True,     # AIと人間を左右にくっつける
        inner=None,     # 中身を描かない
        palette={"AI": "#FF9999", "Human": "#99CCFF"},
        cut=0, # 範囲外の表示をしない
        ax=ax
    )
    
    # Seabornが自動的に追加した凡例を削除 (手動で制御するため)
    if ax.get_legend() is not None:
        ax.get_legend().remove()
    
    # 2. 箱ひげ図を重ねる (ax.boxplotを使用)
    box_width = 0.1
    
    # AIの箱ひげ図
    ax.boxplot(
        [data_ai], 
        positions=[-0.1], 
        widths=box_width,
        patch_artist=True,
        boxprops=dict(facecolor='white', alpha=0.5, edgecolor='black'),
        whiskerprops=dict(color='black'),
        capprops=dict(color='black'),
        medianprops=dict(color='black'),
        showfliers=False,
        manage_ticks=False
    )
    
    # Humanの箱ひげ図
    ax.boxplot(
        [data_human], 
        positions=[0.1], 
        widths=box_width,
        patch_artist=True,
        boxprops=dict(facecolor='white', alpha=0.5, edgecolor='black'),
        whiskerprops=dict(color='black'),
        capprops=dict(color='black'),
        medianprops=dict(color='black'),
        showfliers=False,
        manage_ticks=False
    )
    
    # 平均値を計算してプロットに追加 (白抜きの菱形)
    means = df_plot.groupby('Type')['Value'].mean()
    
    if 'AI' in means:
        ax.scatter(x=[-0.1], y=[means['AI']], color='white', marker='D', s=60, zorder=10, edgecolor='black', label='Mean')
    if 'Human' in means:
        ax.scatter(x=[0.1], y=[means['Human']], color='white', marker='D', s=60, zorder=10, edgecolor='black')
    
    if ylim is not None:
        ax.set_ylim(0, ylim)
    
    # 文字サイズを大きく設定
    ax.set_ylabel(ylabel, fontsize=28) # 24 -> 28
    ax.set_xlabel("", fontsize=28) 
    
    # x軸の目盛りとしてタイトルを表示
    ax.set_xticks([0])
    ax.set_xticklabels([xlabel], fontsize=32) # 28 -> 32
    
    # 目盛りの文字サイズ変更
    ax.tick_params(axis='y', which='major', labelsize=24) # 22 -> 24
    
    # 凡例
    if show_legend:
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, loc='upper right', fontsize=20) # 18 -> 20

def create_violin_plot(data_ai, data_human, title, ylabel, output_path, ylim=None):
    """
    バイオリンプロットを作成して保存する (単体用ラッパー)
    """
    # 縦長に変更 (幅5, 高さ8) -> (幅5, 高さ8)
    plt.figure(figsize=(5, 8))
    ax = plt.gca()
    
    # スタイル設定
    sns.set_style("whitegrid")
    
    draw_violin_on_ax(ax, data_ai, data_human, title, ylabel, ylim, show_legend=True)
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def create_combined_violin_plot(dataset_list, output_path):
    """
    3つのバイオリンプロットを横に並べて保存する
    """
    # 横長 (幅15, 高さ8) -> (幅14, 高さ8)
    fig, axes = plt.subplots(1, 3, figsize=(14, 8))
    
    # スタイル設定
    sns.set_style("whitegrid")
    
    for i, data in enumerate(dataset_list):
        draw_violin_on_ax(
            ax=axes[i],
            data_ai=data['ai'],
            data_human=data['human'],
            xlabel=data['xlabel'],
            ylabel=data['ylabel'],
            ylim=data['ylim'],
            show_legend=False
        )
    
    # 共通の凡例を作成 (最初のプロットからハンドルとラベルを取得)
    handles, labels = axes[0].get_legend_handles_labels()
    # 図全体の上部に凡例を表示
    fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 1.08), ncol=3, fontsize=24) # 20 -> 24
    
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches='tight')
    plt.close()

def create_weekly_trend_boxplot(ai_df, human_df, output_path):
    """
    週ごとのコミット数推移を箱ひげ図で可視化する
    """
    # データをロング形式に変換
    # ai_df, human_dfは columns=WeekNum, index=FileID, values=CommitCount
    ai_long = ai_df.melt(var_name='Week', value_name='CommitCount')
    ai_long['Type'] = 'AI'
    
    human_long = human_df.melt(var_name='Week', value_name='CommitCount')
    human_long['Type'] = 'Human'
    
    df_plot = pd.concat([ai_long, human_long], ignore_index=True)
    
    # Weekを1始まりにする (0 -> 1)
    df_plot['Week'] = df_plot['Week'] + 1
    
    plt.figure(figsize=(14, 8))
    sns.set_style("whitegrid")
    
    # 箱ひげ図
    ax = sns.boxplot(
        data=df_plot,
        x='Week',
        y='CommitCount',
        hue='Type',
        palette={"AI": "#FF9999", "Human": "#99CCFF"},
        showfliers=False
    )
    
    # Y軸の範囲を制限（3以上のコミット数は表示しない）
    plt.ylim(0, 5)
    
    plt.title("Weekly Commit Count Trend", fontsize=16)
    plt.xlabel("Period (Week)", fontsize=14)
    plt.ylabel("Commit Count", fontsize=14)
    plt.legend(title="Creator", fontsize=12)
    
    # X軸のラベルが見やすくなるように調整
    if df_plot['Week'].nunique() > 20:
        plt.xticks(rotation=90)
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

if __name__ == "__main__":
    analyze_rq1()
