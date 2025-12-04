import pandas as pd
import matplotlib.pyplot as plt
import os

def analyze_commit_classification():
    # ファイルパスの定義
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, '..', 'results', 'results_v4.csv')
    output_txt = os.path.join(base_dir, '..', 'results', 'RQ3_results.txt')
    output_img_ai = os.path.join(base_dir, '..', 'results', 'RQ3_pieChart_AI.png')
    output_img_human = os.path.join(base_dir, '..', 'results', 'RQ3_pieChart_Human.png')

    # CSVファイルの読み込み
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: File not found at {input_file}")
        return

    # AIと人間が作成したファイルのデータをフィルタリング
    ai_df = df[df['file_created_by'] == 'AI']
    human_df = df[df['file_created_by'] == 'Human']

    # コミット分類の分析
    ai_counts = ai_df['commit_classification'].value_counts()
    human_counts = human_df['commit_classification'].value_counts()

    ai_total = len(ai_df)
    human_total = len(human_df)

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
    def create_pie_chart(counts, title, output_path):
        if counts.empty:
            print(f"No data for {title}")
            return
        
        # 値の降順でカウントをソート
        counts = counts.sort_values(ascending=False)
        total_val = counts.sum()
        
        plot_values = []
        plot_labels = []
        legend_labels = [] # 凡例用の全ラベルリスト
        
        # 表示閾値（3%未満は表示しない）
        threshold = 0.03

        for i, (index, value) in enumerate(zip(counts.index, counts.values)):
            plot_values.append(value)
            percentage = value / total_val
            
            # 凡例用には全ての項目を作成（個別にパーセンテージ表示）
            legend_labels.append(f'{index} ({percentage*100:.1f}%)')

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

        plt.figure(figsize=(14, 10)) # 図のサイズを拡大
        
        # 円グラフのプロット
        # autopctを追加し、戻り値を受け取る変数を変更
        patches, texts, autotexts = plt.pie(
            plot_values, 
            labels=plot_labels, # 円グラフの外側にラベル（名前）
            startangle=90,
            counterclock=False,
            textprops={'fontsize': 25}, # 外側のラベルのフォントサイズを拡大
            autopct=autopct_format,     # 内側に件数とパーセンテージを表示
            pctdistance=0.75,           # 内側のテキストの位置
            labeldistance=1.1           # 外側のラベルの位置
        )
        
        # 内側のテキスト（autotexts）のスタイル調整
        for autotext in autotexts:
            autotext.set_fontsize(23) # 内側のテキストのフォントサイズを拡大
            autotext.set_color('black')
        
        # 凡例には全ての項目を表示
        plt.legend(patches, legend_labels, loc="best", fontsize=12, bbox_to_anchor=(1, 0.5))
        plt.title(title, fontsize=25, pad=40) # タイトルのフォントサイズを拡大、グラフとの間隔を広げる
        plt.axis('equal')  # アスペクト比を等しくして円グラフを円形に描画
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        print(f"Pie chart saved to {output_path}")

    create_pie_chart(ai_counts, 'AI Created Files', output_img_ai)
    create_pie_chart(human_counts, 'Human Created Files', output_img_human)

if __name__ == "__main__":
    analyze_commit_classification()
