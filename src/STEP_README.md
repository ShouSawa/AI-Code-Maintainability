# RQ1分析: ステップ別実行ガイド

このディレクトリには、get-AI-files.pyの処理を4つのステップに分割したスクリプトが含まれています。

## 📂 ファイル構成

```
src/
├── step1_get_files.py          # ファイル追加情報取得
├── step2_choose_files.py       # ファイル選択
├── step3_get_commits.py        # コミット履歴取得
├── step4_classify_commits.py   # コミット分類
└── run_all_steps.py            # 全ステップ一括実行
```

## 🔄 処理フロー

### Step1: ファイル追加情報取得
- **入力**: `../dataset/repository_list.csv`
- **出力**: `../results/EASE-results/csv/step1_all_files.csv`
- **機能**: 2025/1/1～2025/7/31にaddedされたファイルを全て取得

```bash
python step1_get_files.py
```

### Step2: ファイル選択
- **入力**: `../results/EASE-results/csv/step1_all_files.csv`
- **出力**: `../results/EASE-results/csv/step2_selected_files.csv`
- **機能**: AIと人間のファイルを同数ランダムに選択（各リポジトリ最大10件ずつ）

```bash
python step2_choose_files.py
```

### Step3: コミット履歴取得
- **入力**: `../results/EASE-results/csv/step2_selected_files.csv`
- **出力**: `../results/EASE-results/csv/step3_all_commits.csv`
- **機能**: 選択されたファイルの全コミット履歴を取得（～2025/10/31）

```bash
python step3_get_commits.py
```

### Step4: コミット分類
- **入力**: `../results/EASE-results/csv/step3_all_commits.csv`
- **出力**: `../results/EASE-results/csv/step4_classified_commits.csv`
- **機能**: コミットを10カテゴリに分類（feat, fix, docs, etc.）

```bash
python step4_classify_commits.py
```

## 🚀 使用方法

### 方法1: 全ステップを一括実行

```bash
python run_all_steps.py
```

### 方法2: 各ステップを個別に実行

```bash
# Step1から順番に実行
python step1_get_files.py
python step2_choose_files.py
python step3_get_commits.py
python step4_classify_commits.py
```

## 📋 出力CSVのカラム構成

### step1_all_files.csv
- `repository_name`: リポジトリ名
- `file_path`: ファイルパス
- `commit_hash`: コミットハッシュ
- `commit_date`: コミット日時
- `author_type`: 作成者タイプ（AI/Human）
- `ai_type`: AIツール名
- `author_name`: 作成者名
- `author_email`: 作成者メール
- `all_authors`: 全作成者
- `commit_message`: コミットメッセージ

### step2_selected_files.csv
- step1と同じ構成（選択されたファイルのみ）

### step3_all_commits.csv
- `repository_name`: リポジトリ名
- `file_path`: ファイルパス
- `original_author_type`: 元の作成者タイプ
- `original_commit_hash`: 元のコミットハッシュ
- `commit_hash`: コミットハッシュ
- `commit_date`: コミット日時
- `author_name`: 作成者名
- `all_authors`: 全作成者
- `author_email`: 作成者メール
- `is_ai_generated`: AI判定
- `ai_type`: AIツール名
- `commit_message`: コミットメッセージ

### step4_classified_commits.csv
- step3の全カラム + 以下
- `classification_label`: 分類ラベル
- `changed_lines`: 変更行数

## ⚙️ 必要な設定

### 1. GitHub Token
`.env`ファイルに以下を設定：
```
GITHUB_TOKEN=your_github_token_here
```

### 2. リポジトリリスト
`../dataset/repository_list.csv`に以下の形式でリポジトリリストを用意：
```csv
owner,repository_name,stars
microsoft,vscode,150000
facebook,react,200000
```

### 3. 必要なライブラリ
```bash
pip install pandas numpy tqdm PyGithub python-dotenv transformers torch
```

## 📊 処理時間の目安

- **Step1**: 約10-30分（リポジトリ数による）
- **Step2**: 約1分
- **Step3**: 約30-60分（選択ファイル数による）
- **Step4**: 約1-3時間（コミット数による）

## 🔍 トラブルシューティング

### エラー: GitHub tokenが設定されていません
→ `.env`ファイルに`GITHUB_TOKEN`を設定してください

### エラー: CSVファイルが見つかりません
→ 前のステップを先に実行してください

### エラー: API rate limit
→ GitHub APIのレート制限に達しています。しばらく待ってから再実行してください

## 📝 注意事項

- Step4は機械学習モデルを使用するため、GPUを推奨します
- API rate limitを考慮し、適度に`time.sleep()`を入れています
- ネットワークエラー時は自動的に再接続を試みます

## 🆚 get-AI-files.pyとの違い

### 利点
- ✅ ステップごとに結果を保存するため、途中から再開可能
- ✅ 各ステップを個別に実行・デバッグ可能
- ✅ 中間結果をCSVで確認できる

### 欠点
- ❌ ディスク容量を多く使用する
- ❌ ファイルI/Oが増えるため、若干遅い

## 📌 推奨される使い方

1. **初回実行**: `run_all_steps.py`で全ステップを実行
2. **エラー発生時**: エラーが起きたステップだけ再実行
3. **データ確認**: 各ステップのCSVを確認しながら進める
