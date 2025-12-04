import pandas as pd
import os

def find_test_commits():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, '..', 'results', 'results_v4.csv')

    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: File not found at {input_file}")
        return

    # Filter for 'tests' classification
    # Note: The user said "tests", but looking at the file content I see "fix", "chore". 
    # I should check if "tests" exists or if it might be "test".
    # I will filter for exact match 'tests' first as requested.
    
    test_commits = df[df['commit_classification'] == 'tests']
    
    if test_commits.empty:
        print("No commits found with classification 'tests'.")
        # Let's also check for 'test' just in case
        test_commits_singular = df[df['commit_classification'] == 'test']
        if not test_commits_singular.empty:
             print(f"Found {len(test_commits_singular)} commits with classification 'test'.")
             print(test_commits_singular[['repository_name', 'commit_hash', 'file_name', 'commit_classification']].to_string())
    else:
        print(f"Found {len(test_commits)} commits with classification 'tests':")
        print(test_commits[['repository_name', 'commit_hash', 'file_name', 'commit_classification']].to_string())

if __name__ == "__main__":
    find_test_commits()
