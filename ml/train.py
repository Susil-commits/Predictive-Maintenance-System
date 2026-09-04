import os
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix
)
from xgboost import XGBClassifier
import shap
import mlflow
import mlflow.sklearn
import mlflow.xgboost

def determine_next_version(metadata_path: str) -> str:
    """
    Computes the next incremental model version: v1 -> v2 -> v3 ...
    """
    if not os.path.exists(metadata_path):
        return "v1"
    try:
        with open(metadata_path, "r") as f:
            meta = json.load(f)
            curr = str(meta.get("version", "v0"))
            if curr.startswith("v") and curr[1:].isdigit():
                return f"v{int(curr[1:]) + 1}"
            elif curr == "1.0.0":
                return "v2"
            else:
                return "v2"
    except Exception:
        return "v1"

ML_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(os.path.dirname(ML_DIR), "data", "equipment_maintenance_data.csv")

def feature_engineering(df):
    """
    Computes domain-specific interaction features for equipment failure prediction.
    """
    df = df.copy()
    # Thermal-mechanical stress
    df['temp_pressure_index'] = (df['temperature'] * df['pressure']) / 100.0
    # Cumulative fatigue index
    df['vibration_wear_index'] = df['vibration'] * (df['operating_hours'] / 1000.0)
    # Dynamic harmonic load
    df['rpm_vibration_ratio'] = (df['rpm'] * df['vibration']) / 1000.0
    return df

def run_pipeline():
    print("=" * 60)
    print("PREDICTIVE MAINTENANCE ML TRAINING PIPELINE")
    print("=" * 60)
    
    # 1. Load Data
    if not os.path.exists(DATA_PATH):
        from dataset_loader import download_and_prepare_dataset
        df = download_and_prepare_dataset()
    else:
        df = pd.read_csv(DATA_PATH)
        
    print(f"Loaded {len(df)} records. Features: {list(df.columns)}")
    
    # 2. EDA & Visualizations
    print("\n[EDA] Class distribution:")
    failure_counts = df['failure'].value_counts()
    print(failure_counts)
    print(f"Failure percentage: {df['failure'].mean() * 100:.2f}%")
    
    plt.figure(figsize=(12, 8))
    plt.subplot(2, 2, 1)
    sns.countplot(x='failure', data=df, palette='Blues')
    plt.title("Class Distribution (0 = Normal, 1 = Risk)")
    
    plt.subplot(2, 2, 2)
    sns.boxplot(x='failure', y='temperature', data=df, palette='OrRd')
    plt.title("Temperature vs Failure")
    
    plt.subplot(2, 2, 3)
    sns.boxplot(x='failure', y='vibration', data=df, palette='Purples')
    plt.title("Vibration vs Failure")
    
    plt.subplot(2, 2, 4)
    corr = df.corr()
    sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f")
    plt.title("Correlation Matrix")
    
    plt.tight_layout()
    eda_plot_path = os.path.join(ML_DIR, "eda_summary.png")
    plt.savefig(eda_plot_path, dpi=150)
    plt.close()
    print(f"[EDA] Saved plot to {eda_plot_path}")
    
    # 3. Feature Engineering
    df_fe = feature_engineering(df)
    
    feature_cols = [
        'temperature',
        'rpm',
        'pressure',
        'vibration',
        'operating_hours',
        'temp_pressure_index',
        'vibration_wear_index',
        'rpm_vibration_ratio'
    ]
    
    X = df_fe[feature_cols]
    y = df_fe['failure']
    
    # Train / Test split (stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Calculate scale_pos_weight for XGBoost
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    pos_weight = float(neg_count / max(pos_count, 1))
    
    # 4. Model Training Sequence
    # Baseline: Logistic Regression
    print("\n--- Training Model 1: Logistic Regression (Baseline) ---")
    lr = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
    lr.fit(X_train_scaled, y_train)
    y_pred_lr = lr.predict(X_test_scaled)
    y_prob_lr = lr.predict_proba(X_test_scaled)[:, 1]
    lr_roc = roc_auc_score(y_test, y_prob_lr)
    lr_f1 = f1_score(y_test, y_pred_lr)
    print(f"Logistic Regression -> ROC-AUC: {lr_roc:.4f}, F1: {lr_f1:.4f}")
    
    # Model 2: Random Forest
    print("\n--- Training Model 2: Random Forest ---")
    rf = RandomForestClassifier(
        n_estimators=150,
        max_depth=8,
        min_samples_split=4,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    y_prob_rf = rf.predict_proba(X_test)[:, 1]
    rf_roc = roc_auc_score(y_test, y_prob_rf)
    rf_f1 = f1_score(y_test, y_pred_rf)
    print(f"Random Forest -> ROC-AUC: {rf_roc:.4f}, F1: {rf_f1:.4f}")
    
    # Model 3: XGBoost (Final Production Model)
    print("\n--- Training Model 3: XGBoost (Final Model) ---")
    xgb = XGBClassifier(
        n_estimators=180,
        max_depth=5,
        learning_rate=0.06,
        scale_pos_weight=pos_weight * 0.85,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        eval_metric='logloss'
    )
    xgb.fit(X_train, y_train)
    y_pred_xgb = xgb.predict(X_test)
    y_prob_xgb = xgb.predict_proba(X_test)[:, 1]
    xgb_roc = roc_auc_score(y_test, y_prob_xgb)
    xgb_f1 = f1_score(y_test, y_pred_xgb)
    xgb_prec = precision_score(y_test, y_pred_xgb)
    xgb_rec = recall_score(y_test, y_pred_xgb)
    
    print(f"XGBoost -> ROC-AUC: {xgb_roc:.4f}, F1: {xgb_f1:.4f}, Precision: {xgb_prec:.4f}, Recall: {xgb_rec:.4f}")
    print("\nXGBoost Detailed Classification Report:")
    print(classification_report(y_test, y_pred_xgb, target_names=['Normal', 'Failure Risk']))
    
    # 5. SHAP Explainer
    print("\n--- Initializing SHAP TreeExplainer ---")
    explainer = shap.TreeExplainer(xgb)
    shap_values = explainer.shap_values(X_test)
    
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X_test, feature_names=feature_cols, show=False)
    shap_plot_path = os.path.join(ML_DIR, "shap_summary.png")
    plt.tight_layout()
    plt.savefig(shap_plot_path, dpi=150)
    plt.close()
    print(f"Saved SHAP summary plot to {shap_plot_path}")
    
    # 6. Test sample prediction verification
    sample_input = pd.DataFrame([{
        "temperature": 92.4,
        "rpm": 2800,
        "pressure": 31.5,
        "vibration": 0.64,
        "operating_hours": 4820
    }])
    sample_fe = feature_engineering(sample_input)[feature_cols]
    sample_prob = float(xgb.predict_proba(sample_fe)[0, 1])
    sample_risk = "HIGH" if sample_prob >= 0.50 else "LOW"
    sample_shap = explainer.shap_values(sample_fe)[0]
    
    factors = sorted(
        [{"feature": f, "impact": float(val)} for f, val in zip(feature_cols, sample_shap)],
        key=lambda x: abs(x["impact"]),
        reverse=True
    )
    
    print("\n[VERIFICATION] Target Test Input:")
    print(sample_input.to_dict(orient='records')[0])
    print(f"Result -> Risk: {sample_risk}, Probability: {sample_prob:.2%}")
    print("Top factors from SHAP:")
    for i, factor in enumerate(factors[:4], 1):
        print(f"  {i}. {factor['feature']}: {factor['impact']:+.3f}")
    
    # 7. Save Model Artifacts, Reference Stats, and Log with MLflow
    model_file = os.path.join(ML_DIR, "model.pkl")
    scaler_file = os.path.join(ML_DIR, "scaler.pkl")
    metadata_file = os.path.join(ML_DIR, "model_info.json")
    ref_stats_file = os.path.join(ML_DIR, "reference_stats.json")
    
    next_version = determine_next_version(metadata_file)
    print(f"\n[Versioning] Promoting model version to: {next_version}")
    
    # Save local joblib files for low-latency production fallback
    joblib.dump(xgb, model_file)
    joblib.dump(scaler, scaler_file)
    
    # Compute baseline reference distribution for production drift detection
    base_features = ['temperature', 'rpm', 'pressure', 'vibration', 'operating_hours']
    features_stats = {}
    for feat in base_features:
        series = df[feat]
        quantiles = np.linspace(0, 1, 11)
        bin_edges = np.unique(np.percentile(series, quantiles * 100))
        counts, _ = np.histogram(series, bins=bin_edges)
        expected_pct = (counts / len(series)).tolist()
        features_stats[feat] = {
            "mean": round(float(series.mean()), 4),
            "std": round(float(series.std()), 4),
            "min": round(float(series.min()), 4),
            "max": round(float(series.max()), 4),
            "bin_edges": [round(float(b), 4) for b in bin_edges],
            "expected_pct": [round(float(p), 4) for p in expected_pct]
        }
    
    reference_stats = {
        "model_version": next_version,
        "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sample_count": len(df),
        "features": features_stats
    }
    with open(ref_stats_file, "w") as f:
        json.dump(reference_stats, f, indent=2)
    print(f"Saved drift reference statistics to {ref_stats_file}")

    # Configure MLflow tracking (SQLite database supports the full MLflow Model Registry)
    db_path = os.path.abspath(os.path.join(os.path.dirname(ML_DIR), "mlflow.db"))
    default_tracking_uri = f"sqlite:///{db_path.replace(os.sep, '/')}"
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", default_tracking_uri)
    os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
    mlflow.set_tracking_uri(tracking_uri)
    experiment_name = "Predictive-Maintenance-System"
    try:
        mlflow.set_experiment(experiment_name)
    except Exception as exp_err:
        print(f"[MLflow] Experiment setup note: {exp_err}")

    mlflow_run_id = None
    with mlflow.start_run(run_name=f"PMS_Training_{next_version}") as run:
        mlflow_run_id = run.info.run_id
        print(f"[MLflow] Active Run ID: {mlflow_run_id}")
        print(f"[MLflow] Tracking URI: {tracking_uri}")
        
        # A. Log Parameters
        mlflow.log_params({
            "model_type": "XGBoostClassifier",
            "model_version": next_version,
            "n_estimators": 180,
            "max_depth": 5,
            "learning_rate": 0.06,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "scale_pos_weight": round(pos_weight * 0.85, 4),
            "random_state": 42,
            "eval_metric": "logloss",
            "rf_n_estimators": 150,
            "rf_max_depth": 8,
            "lr_max_iter": 1000,
            "training_samples": len(X_train),
            "test_samples": len(X_test)
        })
        
        # B. Log Metrics
        mlflow.log_metrics({
            "xgb_roc_auc": round(float(xgb_roc), 4),
            "xgb_f1_score": round(float(xgb_f1), 4),
            "xgb_precision": round(float(xgb_prec), 4),
            "xgb_recall": round(float(xgb_rec), 4),
            "baseline_lr_roc": round(float(lr_roc), 4),
            "baseline_lr_f1": round(float(lr_f1), 4),
            "random_forest_roc": round(float(rf_roc), 4),
            "random_forest_f1": round(float(rf_f1), 4)
        })
        
        # C. Log Artifacts
        if os.path.exists(eda_plot_path):
            mlflow.log_artifact(eda_plot_path, artifact_path="eda")
        if os.path.exists(shap_plot_path):
            mlflow.log_artifact(shap_plot_path, artifact_path="explainability")
        if os.path.exists(scaler_file):
            mlflow.log_artifact(scaler_file, artifact_path="preprocessing")
        if os.path.exists(ref_stats_file):
            mlflow.log_artifact(ref_stats_file, artifact_path="drift_baseline")
            
        # D. Log Model and Register with MLflow Model Registry
        try:
            mlflow.xgboost.log_model(
                xgb_model=xgb,
                artifact_path="model",
                registered_model_name="PMS-XGBoost"
            )
            print("[MLflow] Model registered as 'PMS-XGBoost' in Model Registry")
        except Exception as reg_err:
            print(f"[MLflow] Model registry registration note: {reg_err}")

    # Update model metadata JSON with version and MLflow run ID
    model_metadata = {
        "model_name": "XGBoost Classifier",
        "version": next_version,
        "mlflow_run_id": mlflow_run_id,
        "mlflow_experiment": experiment_name,
        "trained_date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dataset_source": "UCI AI4I 2020 Predictive Maintenance Dataset",
        "total_training_samples": len(X_train),
        "total_test_samples": len(X_test),
        "metrics": {
            "roc_auc": round(float(xgb_roc), 4),
            "f1_score": round(float(xgb_f1), 4),
            "precision": round(float(xgb_prec), 4),
            "recall": round(float(xgb_rec), 4),
            "baseline_lr_roc": round(float(lr_roc), 4),
            "random_forest_roc": round(float(rf_roc), 4)
        },
        "feature_names": feature_cols,
        "base_features": base_features
    }
    
    with open(metadata_file, "w") as f:
        json.dump(model_metadata, f, indent=2)
        
    print(f"\nSaved model to {model_file}")
    print(f"Saved scaler to {scaler_file}")
    print(f"Saved metadata to {metadata_file}")
    print("Training pipeline and MLOps tracking completed successfully!")

if __name__ == "__main__":
    run_pipeline()
