from datasets import load_dataset

# Hugging Face から全PR情報を読み込み
# all_pull_request：全てのPR情報を取得
dataset = load_dataset("hao-li/AIDev", split="all_pull_request", cache_dir="./tmp_hf_cache", download_mode="force_redownload")

# データセットの概要を表示
print(dataset)