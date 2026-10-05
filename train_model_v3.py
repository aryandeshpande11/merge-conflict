import pandas as pd
import xgboost as xgb
import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
from sklearn.utils.class_weight import compute_sample_weight
from imblearn.over_sampling import SMOTE
import pickle
import warnings
warnings.filterwarnings('ignore')

FEATURE_COLS = [
    'Conflicting_Files_Count',
    'Author_Match',
    'Lines_Changed_Local',
    'Lines_Changed_Incoming',
    'Total_Lines_Changed',
    'Conflict_Chunk_Count',
    'Avg_Chunk_Size',
    'Local_Conflict_Lines',
    'Incoming_Conflict_Lines',
    'Local_Incoming_Ratio',
    'Primary_File_Type',
    'Time_Diff_Hours'
]

def main():
    print("Loading V3 dataset...")
    df = pd.read_csv('ml_features_v3.csv')
    df = df[df['Resolution_Label'] != 'unknown']
    df = df.fillna(0)

    print(f"Total rows: {len(df)}")
    print("\nLabel Distribution:")
    print(df['Resolution_Label'].value_counts())

    X = df[FEATURE_COLS]
    le = LabelEncoder()
    y = le.fit_transform(df['Resolution_Label'])
    print(f"\nClasses: {le.classes_}")

    # --- SMOTE: Oversample minority classes so all 3 classes are balanced ---
    print("\nApplying SMOTE to balance classes...")
    try:
        sm = SMOTE(random_state=42, k_neighbors=min(3, df['Resolution_Label'].value_counts().min() - 1))
        X_res, y_res = sm.fit_resample(X, y)
        print(f"After SMOTE: {len(X_res)} rows (was {len(X)})")
    except Exception as e:
        print(f"SMOTE skipped ({e}), using original data.")
        X_res, y_res = X, y

    # --- XGBoost V3 with better hyperparameters ---
    model = xgb.XGBClassifier(
        objective='multi:softprob',
        num_class=len(le.classes_),
        eval_metric='mlogloss',
        max_depth=6,
        learning_rate=0.05,
        n_estimators=300,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        reg_alpha=0.1,
        reg_lambda=1.5,
        random_state=42,
        use_label_encoder=False
    )

    # --- Cross Validation (5-fold) for more reliable accuracy ---
    print("\nRunning 5-Fold Cross Validation...")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X_res, y_res, cv=skf, scoring='accuracy')
    print(f"CV Accuracy per fold: {[f'{s:.2f}' for s in cv_scores]}")
    print(f"Mean CV Accuracy: {cv_scores.mean()*100:.2f}% (+/- {cv_scores.std()*100:.2f}%)")

    # --- Train on full balanced dataset for final model ---
    print("\nTraining final model on full balanced dataset...")
    model.fit(X_res, y_res)

    # --- Final Evaluation on ORIGINAL (unbalanced) data ---
    print("\n--- Final Evaluation (on original real-world distribution) ---")
    y_pred = model.predict(X)
    print(f"Overall Accuracy: {accuracy_score(y, y_pred) * 100:.2f}%\n")
    print("Per-Class Metrics:")
    print(classification_report(y, y_pred, labels=range(len(le.classes_)), target_names=le.classes_, zero_division=0))

    # --- Feature Importance ---
    print("\n--- Feature Importance (what the model uses most) ---")
    importance = dict(zip(FEATURE_COLS, model.feature_importances_))
    for feat, imp in sorted(importance.items(), key=lambda x: -x[1]):
        print(f"  {feat}: {imp:.4f}")

    import os
    import json

    # Save pickle model
    with open('xgboost_merge_model_v3.pkl', 'wb') as f:
        pickle.dump({'model': model, 'encoder': le, 'features': FEATURE_COLS}, f)
    print("\nV3 Model saved as 'xgboost_merge_model_v3.pkl'!")

    # Save native XGBoost JSON model and metadata for FastAPI backend
    models_dir = os.path.join('backend', 'models')
    os.makedirs(models_dir, exist_ok=True)
    json_model_path = os.path.join(models_dir, 'merge_conflict_model.json')
    model.save_model(json_model_path)
    print(f"Native XGBoost JSON model saved as '{json_model_path}'!")

    metadata = {
        "model": "XGBoost",
        "version": "v3",
        "features": FEATURE_COLS,
        "classes": list(le.classes_),
        "algorithm": "XGBoost",
        "hyperparameters": {
            "objective": "multi:softprob",
            "num_class": len(le.classes_),
            "max_depth": 6,
            "learning_rate": 0.05,
            "n_estimators": 300,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 3,
            "gamma": 0.1,
            "reg_alpha": 0.1,
            "reg_lambda": 1.5
        },
        "metrics": {
            "cross_validation_accuracy": f"{cv_scores.mean()*100:.2f}% ± {cv_scores.std()*100:.2f}%",
            "cv_scores": [round(float(s), 4) for s in cv_scores],
            "full_dataset_accuracy": f"{accuracy_score(y, y_pred) * 100:.2f}%"
        },
        "class_mapping": {int(i): str(c) for i, c in enumerate(le.classes_)}
    }
    metadata_path = os.path.join(models_dir, 'model_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Model metadata saved as '{metadata_path}'!")

if __name__ == "__main__":
    main()
