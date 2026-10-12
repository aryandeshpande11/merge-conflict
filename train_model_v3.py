import pandas as pd
import xgboost as xgb
import numpy as np
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
from sklearn.utils.class_weight import compute_sample_weight
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

def manual_oversample(X, y):
    """
    Replaces SMOTE with pure pandas random oversampling.
    Upsamples minority classes to match the majority class count.
    """
    df = X.copy()
    df['__label__'] = y
    max_count = df['__label__'].value_counts().max()
    
    balanced_chunks = []
    for label_val in df['__label__'].unique():
        chunk = df[df['__label__'] == label_val]
        oversampled = chunk.sample(max_count, replace=True, random_state=42)
        balanced_chunks.append(oversampled)
    
    balanced = pd.concat(balanced_chunks).sample(frac=1, random_state=42).reset_index(drop=True)
    X_res = balanced[FEATURE_COLS]
    y_res = balanced['__label__'].values
    return X_res, y_res

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

    # Manual oversampling (no imblearn/DLL dependency)
    print("\nApplying manual oversampling to balance classes...")
    X_res, y_res = manual_oversample(X, y)
    print(f"After oversampling: {len(X_res)} rows (was {len(X)})")

    # XGBoost V3 with tuned hyperparameters
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
        random_state=42
    )

    # 5-Fold Cross Validation
    print("\nRunning 5-Fold Cross Validation...")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(model, X_res, y_res, cv=skf, scoring='accuracy')
    print(f"CV Accuracy per fold: {[f'{s:.2f}' for s in cv_scores]}")
    print(f"Mean CV Accuracy: {cv_scores.mean()*100:.2f}% (+/- {cv_scores.std()*100:.2f}%)")

    # Train on full balanced dataset
    print("\nTraining final model on full balanced dataset...")
    model.fit(X_res, y_res)

    # Final Evaluation on ORIGINAL data
    print("\n--- Final Evaluation (on original real-world distribution) ---")
    y_pred = model.predict(X)
    print(f"Overall Accuracy: {accuracy_score(y, y_pred) * 100:.2f}%\n")
    print("Per-Class Metrics:")
    print(classification_report(y, y_pred, labels=range(len(le.classes_)), target_names=le.classes_, zero_division=0))

    # Feature Importance
    print("\n--- Feature Importance ---")
    importance = dict(zip(FEATURE_COLS, model.feature_importances_))
    for feat, imp in sorted(importance.items(), key=lambda x: -x[1]):
        print(f"  {feat}: {imp:.4f}")

    # Save model
    with open('xgboost_merge_model_v3.pkl', 'wb') as f:
        pickle.dump({'model': model, 'encoder': le, 'features': FEATURE_COLS}, f)
    print("\nV3 Model saved as 'xgboost_merge_model_v3.pkl'!")

if __name__ == "__main__":
    main()
