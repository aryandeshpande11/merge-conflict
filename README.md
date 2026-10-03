# Merge Conflict Resolution Predictor
> An XGBoost-based multi-class classifier that predicts how a Git merge conflict should be resolved — automatically determining whether to `keep_local`, `keep_incoming`, or `combine_both`.

---

## Problem Statement

When two developers modify the same file in different branches and attempt to merge, Git raises a **merge conflict**. Resolving these conflicts is one of the most time-consuming and error-prone parts of collaborative software development.

This project mines real-world merge conflict history from open-source Java repositories and trains a machine learning model to **predict the resolution strategy** a developer would choose, based on features extracted from the conflict itself.

---

## Repositories Used for Dataset Mining

| Repository | Domain | Merge Commits Mined |
|---|---|---|
| [dropwizard](https://github.com/dropwizard/dropwizard) | Java REST framework | ~1,303 |
| [jbehave-core](https://github.com/jbehave/jbehave-core) | BDD Testing Framework | ~500+ |
| [zanata-server](https://github.com/zanata/zanata-server) | Translation Platform | ~500+ |
| [grails-core](https://github.com/apache/grails-core) | Web Application Framework | ~1,400+ |

---

## Methodology

### Step 1 — Data Mining Pipeline

For every historical merge commit across the 4 repositories, we **replay** the merge programmatically using Git commands:

```
git log --merges --format="%H %P"     → Find all merge commits
git checkout <parent_1>               → Travel back to branch 1
git merge --no-commit --no-ff <p2>    → Replay the merge (do not finalize)
git diff --name-only --diff-filter=U  → Detect conflicting files
git merge --abort                     → Reset and move to next commit
```

If the replayed merge results in a conflict (exit code ≠ 0), we extract features from the conflict state before aborting.

### Step 2 — Labeling Strategy

To automatically label how the conflict was **actually resolved** by the original developer, we compare the final merged file content against the two parent branches:

- If `merged file == parent_1 file` → **`keep_local`**
- If `merged file == parent_2 file` → **`keep_incoming`**
- If `merged file ≠ both` → **`combine_both`** (manual edit merging both sides)

We check up to 3 conflicting files per merge commit and use majority voting for the final label.

### Step 3 — Feature Engineering (V3)

We extract **12 features** per conflict, including both structural and semantic features:

| Feature | Description | Type |
|---|---|---|
| `Conflicting_Files_Count` | Number of files with conflicts | Structural |
| `Author_Match` | 1 if both parents authored by same developer | Structural |
| `Lines_Changed_Local` | Lines modified in branch 1 vs common ancestor | Structural |
| `Lines_Changed_Incoming` | Lines modified in branch 2 vs common ancestor | Structural |
| `Total_Lines_Changed` | Sum of both parent changes | Derived |
| `Conflict_Chunk_Count` | Number of `<<<<<<< ======= >>>>>>>` blocks | **Conflict-level** |
| `Avg_Chunk_Size` | Average lines per conflict chunk | **Conflict-level** |
| `Local_Conflict_Lines` | Lines on the LOCAL side of conflict markers | **Conflict-level** |
| `Incoming_Conflict_Lines` | Lines on the INCOMING side of conflict markers | **Conflict-level** |
| `Local_Incoming_Ratio` | Ratio of local vs incoming conflict lines | **Conflict-level** |
| `Primary_File_Type` | Type of file (0=Code, 1=Config, 2=Docs, 3=Other) | Semantic |
| `Time_Diff_Hours` | Hours between the two parent commits | Temporal |

### Step 4 — Handling Class Imbalance (SMOTE)

The natural distribution of labels in real-world data is heavily skewed:

| Label | Raw Count |
|---|---|
| `combine_both` | 304 |
| `keep_local` | 213 |
| `keep_incoming` | 12 |

A model trained on this raw distribution would learn to almost never predict `keep_incoming`. We apply **SMOTE (Synthetic Minority Oversampling Technique)** to synthetically generate samples for minority classes, balancing all three to 304 rows each (912 total training rows).

### Step 5 — Model Training

We use **XGBoost (Extreme Gradient Boosting)** with tuned hyperparameters:

```python
XGBClassifier(
    objective     = 'multi:softprob',   # Multi-class with probability output
    num_class     = 3,
    max_depth     = 6,
    learning_rate = 0.05,              # Slow, careful learning
    n_estimators  = 300,               # 300 boosting rounds
    subsample     = 0.8,               # 80% row sampling per tree
    colsample_bytree = 0.8,            # 80% feature sampling per tree
    min_child_weight = 3,              # Prevents fitting on tiny groups
    gamma         = 0.1,               # Minimum loss reduction to split
    reg_alpha     = 0.1,               # L1 regularization
    reg_lambda    = 1.5                # L2 regularization
)
```

Accuracy is measured using **5-Fold Stratified Cross Validation** to give a reliable, unbiased estimate across different data splits.

---

## Results (V3 Model)

### Cross-Validation (True Generalization Accuracy)
| Fold | Accuracy |
|---|---|
| Fold 1 | 84% |
| Fold 2 | 85% |
| Fold 3 | 85% |
| Fold 4 | 81% |
| Fold 5 | 79% |
| **Mean** | **82.56% ± 2.23%** |

### Per-Class Metrics (on full dataset)

| Class | Precision | Recall | F1-Score | Support |
|---|---|---|---|---|
| `combine_both` | 0.99 | 0.98 | 0.99 | 304 |
| `keep_incoming` | 1.00 | 1.00 | 1.00 | 12 |
| `keep_local` | 0.97 | 0.99 | 0.98 | 213 |
| **Overall Accuracy** | | | **98.30%** | 529 |

### Feature Importance

| Rank | Feature | Importance |
|---|---|---|
| 1 | `Primary_File_Type` | 0.1205 |
| 2 | `Local_Incoming_Ratio` | 0.1181 |
| 3 | `Lines_Changed_Local` | 0.1129 |
| 4 | `Author_Match` | 0.1057 |
| 5 | `Total_Lines_Changed` | 0.0989 |
| 6 | `Conflict_Chunk_Count` | 0.0731 |
| 7 | `Incoming_Conflict_Lines` | 0.0705 |
| 8 | `Avg_Chunk_Size` | 0.0693 |
| 9 | `Local_Conflict_Lines` | 0.0658 |
| 10 | `Time_Diff_Hours` | 0.0557 |
| 11 | `Lines_Changed_Incoming` | 0.0555 |
| 12 | `Conflicting_Files_Count` | 0.0540 |

> The `Local_Incoming_Ratio` and `Primary_File_Type` being top predictors makes strong intuitive sense — config files and documentation are almost always resolved differently than source code, and the ratio of lines on each conflict side strongly indicates which version the developer kept.

---

## How to Reproduce

### 1. Clone the source repositories
```cmd
mkdir MergeDataset && cd MergeDataset
git clone https://github.com/dropwizard/dropwizard.git
git clone https://github.com/jbehave/jbehave-core.git
git clone https://github.com/zanata/zanata-server.git
git clone https://github.com/apache/grails-core.git
```

### 2. Install dependencies
```cmd
pip install pandas scikit-learn xgboost imbalanced-learn
```

### 3. Extract features
```cmd
python extract_features_v3.py
```
> ⚠️ This will take 10–30 minutes as it replays thousands of historical git merges.

### 4. Train the model
```cmd
python train_model_v3.py
```

---

## Project Structure

```
MergeDataset/
│
├── extract_features_v3.py     # V3 feature extraction pipeline (git mining + conflict analysis)
├── train_model_v3.py          # V3 XGBoost training with SMOTE + 5-fold CV
├── ml_features_v3.csv         # Extracted dataset (529 conflict rows, 12 features + label)
│
├── extract_features.py        # V1 - basic extraction (kept for reference)
├── train_model.py             # V1 - basic training (kept for reference)
├── train_model_v2.py          # V2 - class weighting, stratified split (kept for reference)
│
└── README.md
```

---

## Further Improvements

### 1. Expand the Dataset
The current dataset has 529 rows mined from 4 repositories. Mining from 10–15 repositories would give 2,000–3,000 rows, significantly improving model robustness and reducing variance across folds.

### 2. Add NLP Features (Text-Based)
Currently, all features are numerical. Adding text-based features by analyzing the actual conflict content using NLP could dramatically improve accuracy:
- **TF-IDF similarity** between the local and incoming conflict chunks
- **Token overlap ratio** — how many code tokens are shared between both sides
- **Semantic embedding similarity** using a pre-trained CodeBERT model

### 3. Use a Deep Learning Approach (MergeBERT)
Replace XGBoost entirely with a sequence-to-sequence transformer model (like the `MergeBERT` paper) that reads the raw conflict text and generates the resolved output token by token. This approach achieves ~88%+ accuracy but requires GPU compute.

### 4. Fine-tune Hyperparameters with Optuna
Replace the manually tuned XGBoost hyperparameters with an automated Bayesian search using the `optuna` library to find the globally optimal configuration.

### 5. Deployment (DevOps/MLOps Pipeline)
- Serve predictions via a **FastAPI** REST endpoint
- Containerize with **Docker**
- Orchestrate with **Kubernetes (Minikube)**
- Monitor with **Prometheus + Grafana**

---

## Tech Stack

![Python](https://img.shields.io/badge/Python-3.12-blue)
![XGBoost](https://img.shields.io/badge/XGBoost-2.x-orange)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.x-red)
![imbalanced-learn](https://img.shields.io/badge/imbalanced--learn-SMOTE-green)
![Git](https://img.shields.io/badge/Git-Mining-lightgrey)

---

## Authors
AIML Project — CIE 1 Submission
