"""
コミットの作者がAIか人間かを分類し、統計を分析するスクリプト
"""

import pandas as pd

def classify_author_type(name):
    """
    作者名がAIか人間かを分類
    """
    if pd.isna(name):
        return "Unknown"
    
    name_lower = str(name).lower()
    
    # AIボット・サービスのキーワード
    ai_keywords = [
        'copilot', 'devin-ai', 'devin', 'cursor', 'cursoragent',
        'bot', '[bot]', 'ai-integration', 'assistant', 'gpt',
        'claude', 'gemini', 'llm', 'automated', 'auto-', 
        'web-flow', 'github-actions', 'dependabot', 'renovate',
        'coderabbit', 'ellipsis-dev', 'sweep-ai', 'AI'
    ]
    
    # AIキーワードが含まれているかチェック
    for keyword in ai_keywords:
        if keyword in name_lower:
            return "AI/Bot"
    
    # 明らかに人間の名前パターン（firstname lastname形式）
    if ' ' in name and len(name.split()) == 2:
        parts = name.split()
        # 両方とも大文字で始まる場合は人間の可能性が高い
        if parts[0][0].isupper() and parts[1][0].isupper():
            return "Human"
    
    # その他は人間と仮定（デフォルト）
    return "Human"

def analyze_ai_vs_human(df):
    """
    AIと人間のコミット統計を分析
    """
    print("=== AIと人間の分類分析 ===")
    
    # authorの分類
    df['author_type'] = df['author'].apply(classify_author_type)
    author_type_counts = df['author_type'].value_counts()
    
    print("\n【Author分類】")
    print(author_type_counts)
    print("\n【Author分類の割合】")
    author_percentages = df['author_type'].value_counts(normalize=True) * 100
    for type_name, percentage in author_percentages.items():
        print(f"{type_name}: {percentage:.2f}%")
    
    # committerの分類
    df['committer_type'] = df['committer'].apply(classify_author_type)
    committer_type_counts = df['committer_type'].value_counts()
    
    print("\n【Committer分類】")
    print(committer_type_counts)
    print("\n【Committer分類の割合】")
    committer_percentages = df['committer_type'].value_counts(normalize=True) * 100
    for type_name, percentage in committer_percentages.items():
        print(f"{type_name}: {percentage:.2f}%")
    
    # 上位AIツールの詳細
    print("\n=== 上位AIツール/ボット（Author） ===")
    ai_authors = df[df['author_type'] == 'AI/Bot']['author'].value_counts().head(10)
    print(ai_authors)
    
    print("\n=== 上位AIツール/ボット（Committer） ===")
    ai_committers = df[df['committer_type'] == 'AI/Bot']['committer'].value_counts().head(10)
    print(ai_committers)
    
    # 上位人間開発者
    print("\n=== 上位人間開発者（Author） ===")
    human_authors = df[df['author_type'] == 'Human']['author'].value_counts().head(10)
    print(human_authors)
    
    return df

def check_parquet(df):
    print("\n=== 列名一覧 ===")
    print(df.columns.tolist())
    
    print("PRデータ件数:", len(df))
    
    # AI vs 人間の分析を実行
    df_analyzed = analyze_ai_vs_human(df)
    
    # 分類結果をCSVで保存
    classification_summary = []
    
    # Author統計
    author_stats = df_analyzed.groupby(['author', 'author_type']).size().reset_index(name='commit_count')
    author_stats.to_csv("../data_list/author_classification.csv", index=False)
    
    # Committer統計
    committer_stats = df_analyzed.groupby(['committer', 'committer_type']).size().reset_index(name='commit_count')
    committer_stats.to_csv("../data_list/committer_classification.csv", index=False)
    
    print(f"\n分類結果を保存しました:")
    print(f"- ../data_list/author_classification.csv")
    print(f"- ../data_list/committer_classification.csv")

if __name__ == '__main__':
    df = pd.read_parquet("../data_list/pr_commit_details_local.parquet")
    check_parquet(df)