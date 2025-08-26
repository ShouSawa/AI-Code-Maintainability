import json
import random
import os

def reduce_json_randomly(input_file, output_count=100):
    # JSONファイルを読み込み
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # データが100個未満の場合は警告
    if len(data) < output_count:
        print(f"Warning: データが{len(data)}個しかありません。全てのデータを出力します。")
        output_count = len(data)
    
    # ランダムに100個選択
    selected_data = random.sample(data, output_count)
    
    # 出力ファイル名を生成
    input_dir = os.path.dirname(input_file)
    input_filename = os.path.basename(input_file)
    filename_without_ext = os.path.splitext(input_filename)[0]
    output_filename = f"{filename_without_ext}-100.json"
    output_path = os.path.join(input_dir, output_filename)
    
    # 新しいJSONファイルに書き込み
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(selected_data, f, indent=2, ensure_ascii=False)
    
    print(f"元のデータ数: {len(data)}個")
    print(f"選択されたデータ数: {len(selected_data)}個")
    print(f"出力ファイル: {output_path}")

# 実行
if __name__ == "__main__":
    # -----------入力--------------------
    repo_name = "ai"

    input_file = rf"c:\Users\Shota\Local_document\AI-Code-Maintainability\data_list\RQ2\{repo_name}-bug-fixes.json"
    reduce_json_randomly(input_file)