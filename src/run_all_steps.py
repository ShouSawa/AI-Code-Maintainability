"""
全ステップ実行スクリプト
機能: step1からstep4まで順番に実行
"""

import subprocess
import sys
import os
from datetime import datetime

def run_step(step_name, script_path):
    """各ステップを実行
    
    Args:
        step_name: ステップ名
        script_path: スクリプトパス
    """
    print("\n" + "=" * 80)
    print(f"{step_name} 開始")
    print("=" * 80)
    
    start_time = datetime.now()
    
    try:
        # Pythonスクリプトを実行
        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            capture_output=False,
            text=True
        )
        
        elapsed_time = datetime.now() - start_time
        print(f"\n✓ {step_name} 完了 (所要時間: {elapsed_time})")
        return True
        
    except subprocess.CalledProcessError as e:
        elapsed_time = datetime.now() - start_time
        print(f"\n✗ {step_name} 失敗 (所要時間: {elapsed_time})")
        print(f"エラー: {e}")
        return False


def main():
    """メイン実行"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    steps = [
        ("Step1: ファイル追加情報取得", os.path.join(script_dir, "step1_get_files.py")),
        ("Step2: ファイル選択", os.path.join(script_dir, "step2_choose_files.py")),
        ("Step3: コミット履歴取得", os.path.join(script_dir, "step3_get_commits.py")),
        ("Step4: コミット分類", os.path.join(script_dir, "step4_classify_commits.py"))
    ]
    
    print("=" * 80)
    print("RQ1分析: 全ステップ実行")
    print("=" * 80)
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    overall_start = datetime.now()
    
    # 各ステップを順番に実行
    for step_name, script_path in steps:
        success = run_step(step_name, script_path)
        
        if not success:
            print("\n" + "=" * 80)
            print("エラーが発生したため、処理を中断します")
            print("=" * 80)
            sys.exit(1)
    
    # 全体の処理時間
    overall_elapsed = datetime.now() - overall_start
    
    print("\n" + "=" * 80)
    print("全ステップ完了！")
    print("=" * 80)
    print(f"総処理時間: {overall_elapsed}")
    print("\n出力ファイル:")
    print("  - ../results/EASE-results/csv/step1_all_files.csv")
    print("  - ../results/EASE-results/csv/step2_selected_files.csv")
    print("  - ../results/EASE-results/csv/step3_all_commits.csv")
    print("  - ../results/EASE-results/csv/step4_classified_commits.csv")
    print("=" * 80)


if __name__ == "__main__":
    main()
