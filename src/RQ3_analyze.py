import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import os

def analyze_commit_classification():
    # ファイルパスの定義
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, '..', 'results', 'results_v4.csv')
    output_txt = os.path.join(base_dir, '..', 'results', 'RQ3_results.txt')
    output_pdf_h = os.path.join(base_dir, '..', 'results', 'RQ3_pieCharts_horizontal.pdf')
    output_pdf_v = os.path.join(base_dir, '..', 'results', 'RQ3_pieCharts_vertical.pdf')

    # CSVファイルの読み込み
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: File not found at {input_file}")
        return

    # --- 追加: ファイル作成コミットを除外する処理 ---
    # 日付比較のためにdatetime型に変換
    df['commit_date'] = pd.to_datetime(df['commit_date'])
    df['file_creation_date'] = pd.to_datetime(df['file_creation_date'])
    
    # 作成日時とコミット日時が一致する行（作成コミット）を除外
    # 一致する行をすべて削除するのではなく、各ファイルにつき1つだけ（最初の1つ）を除外する
    original_count = len(df)
    
    # 条件に一致する行を特定
    mask_creation = df['commit_date'] == df['file_creation_date']
    
    # 除外対象のインデックスを特定するための処理
    # repository_nameとfile_nameでグループ化し、条件に合う最初の行のインデックスを取得
    creation_commit_indices = df[mask_creation].groupby(['repository_name', 'file_name']).head(1).index
    
    # 特定したインデックスを除外
    df = df.drop(creation_commit_indices)
    
    print(f"作成コミットを除外しました: {original_count} -> {len(df)} 件")
    # --------------------------------------------

    # AIと人間が作成したファイルのデータをフィルタリング
    ai_df = df[df['file_created_by'] == 'AI']
    human_df = df[df['file_created_by'] == 'Human']

    # コミット分類の分析
    ai_counts = ai_df['commit_classification'].value_counts()
    human_counts = human_df['commit_classification'].value_counts()

    ai_total = len(ai_df)
    human_total = len(human_df)

    # 統一されたカラーマップの作成
    all_categories = set(ai_counts.index) | set(human_counts.index)
    # tab20カラーパレットを使用して、各カテゴリに固定の色を割り当て
    cmap = plt.get_cmap('tab20')
    colors_map = {cat: cmap(i % 20) for i, cat in enumerate(sorted(list(all_categories)))}

    # 出力テキストの準備
    output_lines = []
    
    output_lines.append("AI Created Files")
    output_lines.append(f"Total Commits: {ai_total}")
    for commit_type, count in ai_counts.items():
        percentage = (count / ai_total) * 100 if ai_total > 0 else 0
        output_lines.append(f"{commit_type}: {count} ({percentage:.2f}%)")
    
    output_lines.append("\nHuman Created Files Commit Classification:")
    output_lines.append(f"Total Commits: {human_total}")
    for commit_type, count in human_counts.items():
        percentage = (count / human_total) * 100 if human_total > 0 else 0
        output_lines.append(f"{commit_type}: {count} ({percentage:.2f}%)")

    # テキストファイルへの書き込み
    with open(output_txt, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    print(f"Results written to {output_txt}")

    # 円グラフの生成
    def create_pie_chart(counts, title, ax, colors_map):
        if counts.empty:
            print(f"No data for {title}")
            return
        
        # 値の降順でカウントをソート
        counts = counts.sort_values(ascending=False)
        total_val = counts.sum()
        
        plot_values = []
        plot_labels = []
        slice_colors = [] # スライス用の色リスト
        
        # 表示閾値（3%未満は表示しない）
        threshold = 0.03

        for i, (index, value) in enumerate(zip(counts.index, counts.values)):
            plot_values.append(value)
            percentage = value / total_val
            slice_colors.append(colors_map.get(index, 'gray')) # マップから色を取得
            
            # 3%未満はラベルを表示しない（まとめる機能は削除）
            if percentage >= threshold:
                plot_labels.append(index)
            else:
                plot_labels.append("")

        # autopct用の関数（件数とパーセンテージを表示）
        def autopct_format(pct):
            # 閾値未満の場合は表示しない
            if pct < threshold * 100:
                return ""
            val = int(round(pct * total_val / 100.0))
            return f'{val}\n({pct:.1f}%)'

        # 円グラフのプロット
        # autopctを追加し、戻り値を受け取る変数を変更
        patches, texts, autotexts = ax.pie(
            plot_values, 
            labels=plot_labels, # 円グラフの外側にラベル（名前）
            colors=slice_colors, # 固定色を適用
            startangle=90,
            counterclock=False,
            textprops={'fontsize': 45}, # 外側のラベルのフォントサイズを拡大
            autopct=autopct_format,     # 内側に件数とパーセンテージを表示
            pctdistance=0.75,           # 内側のテキストの位置
            labeldistance=1.15          # 外側のラベルの位置
        )
        
        # 内側のテキスト（autotexts）のスタイル調整
        for autotext in autotexts:
            autotext.set_fontsize(30) # 内側のテキストのフォントサイズを拡大
            autotext.set_color('black')
        
        # 凡例は表示しない
        # ax.legend(patches, legend_labels, loc="center left", fontsize=18, bbox_to_anchor=(1, 0.5))
        
        ax.set_title(title, fontsize=50, pad=40) # タイトルのフォントサイズを拡大、グラフとの間隔を広げる
        ax.axis('equal')  # アスペクト比を等しくして円グラフを円形に描画

    # PDF作成 (横並び)
    with PdfPages(output_pdf_h) as pdf:
        fig_h, axes_h = plt.subplots(1, 2, figsize=(28, 14))
        create_pie_chart(ai_counts, 'AI Created Files', axes_h[0], colors_map)
        create_pie_chart(human_counts, 'Human Created Files', axes_h[1], colors_map)
        plt.tight_layout()
        pdf.savefig(fig_h)
        plt.close(fig_h)
    print(f"Pie charts (Horizontal) saved to {output_pdf_h}")

    # PDF作成 (縦並び)
    with PdfPages(output_pdf_v) as pdf:
        fig_v, axes_v = plt.subplots(2, 1, figsize=(14, 28))
        create_pie_chart(ai_counts, 'AI Created Files', axes_v[0], colors_map)
        create_pie_chart(human_counts, 'Human Created Files', axes_v[1], colors_map)
        plt.tight_layout()
        pdf.savefig(fig_v)
        plt.close(fig_v)
    print(f"Pie charts (Vertical) saved to {output_pdf_v}")

if __name__ == "__main__":
    analyze_commit_classification()
