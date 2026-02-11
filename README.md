# To What Extent Does Agent-generated Code Require Maintenance? An Empirical Study
This repository contains the replication package, including the source code and results of the paper.

## Data
Download the following files from AIDev-full dataset on Hugging Face and place them in the dataset/ directory:

・repository.parquet

or you can get this dataset by running get-dataset.py:
```
python src/get-dataset.py
```

## How to run
1. Download the dataset:
```
python src/get-dataset.py
```

2. Make sure the parquet files are in dataset/:

・ AI-Code-Maintainability\dataset\repository.parquet

3. Generate the repository list used to get data:
```
python src/create_repository_list.py
```

4. Get commits data to created files by AI and Human referring repository list:
```
python src/get-AI-files.py
```

5. RQ1：Analyze commit frequency and line changed ratio:
```
python src/RQ1_analyze.py
```

6. RQ2：Analyze committer:
```
python src/RQ2_analyze.py
```
   
7. RQ3：Analyze commit types:
```
python src/RQ3_analyze.py
```

## CCS (System for classifying commits) in RQ3
https://figshare.com/articles/dataset/A_First_Look_at_Conventional_Commits_Classification/26507083?file=49041904
