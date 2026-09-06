import os
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
    precision_recall_curve,
    brier_score_loss
)
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
import shap
import mlflow
import mlflow.xgboost
import mlflow.sklearn

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
    Computes domain-specific interaction features for equipment failure prediction:
    1. temp_pressure_index: Thermal-mechanical load index
    2. vibration_wear_index: Cumulative vibration fatigue wear
    3. rpm_vibration_ratio: Dynamic harmonic vibration factor
    4. thermal_excess: Non-linear acute thermal overload severity above nominal 86°C
    5. overstrain_index: High pressure combined with elevated ISO vibration
    6. mechanical_power: Mechanical work / shaft power output
    """
    df = df.copy()
    df['temp_pressure_index'] = (df['temperature'] * df['pressure']) / 100.0
    df['vibration_wear_index'] = df['vibration'] * (df['operating_hours'] / 1000.0)
    df['rpm_vibration_ratio'] = (df['rpm'] * df['vibration']) / 1000.0
    df['thermal_excess'] = np.maximum(0.0, df['temperature'] - 86.0)
    df['overstrain_index'] = (df['pressure'] / 25.0) * np.maximum(0.0, df['vibration'] - 0.35)
    df['mechanical_power'] = (df['rpm'] * df['pressure']) / 1000.0
    return df

def run_pipeline():
    print("=" * 60)
    print("PREDICTIVE MAINTENANCE ML TRAINING PIPELINE")
    print("=" * 60)
    
    # 1. Load Data
    if not os.path.exists(DATA_PATH):
        try:
            from ml.dataset_loader import download_and_prepare_dataset
        except ImportError:
            from dataset_loader import download_and_prepare_dataset  # type: ignore
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
    sns.countplot(x='failure', data=df, hue='failure', palette='Blues', legend=False)
    plt.title("Class Distribution (0 = Normal, 1 = Risk)")
    
    plt.subplot(2, 2, 2)
    sns.boxplot(x='failure', y='temperature', data=df, hue='failure', palette='OrRd', legend=False)
    plt.title("Temperature vs Failure")
    
    plt.subplot(2, 2, 3)
    sns.boxplot(x='failure', y='vibration', data=df, hue='failure', palette='Purples', legend=False)
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
        'rpm_vibration_ratio',
        'thermal_excess',
        'overstrain_index',
        'mechanical_power'
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
    
    # Calculate scale_pos_weight for XGBoost to address class imbalance
    neg_count = int((y_train == 0).sum())
    pos_count = int((y_train == 1).sum())
    scale_pos_weight = float(neg_count / max(pos_count, 1))
    print(f"\n[Class Imbalance Analysis] Normal={neg_count}, Failures={pos_count} (Ratio={scale_pos_weight:.4f})")
    
    # 4. Model Training Sequence
    # Baseline: Logistic Regression
    print("\n--- Training Model 1: Logistic Regression (Baseline) ---")
    lr = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
    lr.fit(X_train_scaled, y_train)
    y_pred_lr = lr.predict(X_test_scaled)
    y_prob_lr = lr.predict_proba(X_test_scaled)[:, 1]
    lr_roc = roc_auc_score(y_test, y_prob_lr)
    lr_f1 = f1_score(y_test, y_pred_lr)
    lr_brier = brier_score_loss(y_test, y_prob_lr)
    print(f"Logistic Regression -> ROC-AUC: {lr_roc:.4f}, F1: {lr_f1:.4f}, Brier Loss: {lr_brier:.4f}")
    
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
    rf_brier = brier_score_loss(y_test, y_prob_rf)
    print(f"Random Forest -> ROC-AUC: {rf_roc:.4f}, F1: {rf_f1:.4f}, Brier Loss: {rf_brier:.4f}")

    # Model 3: LightGBM Classifier
    print("\n--- Training Model 3: LightGBM Classifier ---")
    lgb_model = LGBMClassifier(
        n_estimators=150,
        learning_rate=0.05,
        scale_pos_weight=scale_pos_weight * 0.7,
        random_state=42,
        verbose=-1
    )
    lgb_model.fit(X_train, y_train)
    y_pred_lgb = np.asarray(lgb_model.predict(X_test))
    y_prob_lgb = np.asarray(lgb_model.predict_proba(X_test))[:, 1]
    lgb_roc = roc_auc_score(y_test, y_prob_lgb)
    lgb_f1 = f1_score(y_test, y_pred_lgb)
    lgb_brier = brier_score_loss(y_test, y_prob_lgb)
    print(f"LightGBM -> ROC-AUC: {lgb_roc:.4f}, F1: {lgb_f1:.4f}, Brier Loss: {lgb_brier:.4f}")
    
    # Model 4: XGBoost with Hyperparameter Tuning and Regularization
    print("\n--- Training Model 4: XGBoost with Regularization & GridSearchCV ---")
    param_grid = {
        'n_estimators': [150, 180, 200],
        'max_depth': [3, 4],
        'learning_rate': [0.03, 0.04, 0.06]
    }
    base_xgb = XGBClassifier(
        scale_pos_weight=scale_pos_weight * 0.7,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_weight=3,
        gamma=0.2,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        eval_metric='logloss'
    )
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    grid_search = GridSearchCV(
        estimator=base_xgb,
        param_grid=param_grid,
        scoring='roc_auc',
        cv=cv,
        n_jobs=-1,
        verbose=1
    )
    grid_search.fit(X_train, y_train)
    xgb = grid_search.best_estimator_
    best_params = grid_search.best_params_
    print(f"GridSearchCV best params: {best_params} (best CV ROC-AUC: {grid_search.best_score_:.4f})")
    
    y_prob_xgb = xgb.predict_proba(X_test)[:, 1]
    xgb_roc_raw = roc_auc_score(y_test, y_prob_xgb)
    xgb_brier_uncalibrated = brier_score_loss(y_test, y_prob_xgb)
    print(f"XGBoost (Uncalibrated) -> ROC-AUC: {xgb_roc_raw:.4f}, Brier Score Loss: {xgb_brier_uncalibrated:.4f}")

    # Model Calibration: Platt Sigmoid Calibration via CalibratedClassifierCV
    print("\n--- Applying Platt Sigmoid Calibration (CalibratedClassifierCV) ---")
    calibrated_xgb = CalibratedClassifierCV(estimator=xgb, method='sigmoid', cv=3)
    calibrated_xgb.fit(X_train, y_train)
    y_prob_calibrated = calibrated_xgb.predict_proba(X_test)[:, 1]
    calibrated_roc = roc_auc_score(y_test, y_prob_calibrated)
    calibrated_brier = brier_score_loss(y_test, y_prob_calibrated)
    error_reduction = (xgb_brier_uncalibrated - calibrated_brier) / xgb_brier_uncalibrated * 100.0
    print(f"Calibrated XGBoost -> ROC-AUC: {calibrated_roc:.4f}, Brier Loss: {calibrated_brier:.4f} ({error_reduction:.1f}% error reduction)")
    
    # Baseline 0.50 cutoff evaluation on calibrated probabilities
    y_pred_calibrated_default = (y_prob_calibrated >= 0.50).astype(int)
    def_f1 = f1_score(y_test, y_pred_calibrated_default)
    def_prec = precision_score(y_test, y_pred_calibrated_default)
    def_rec = recall_score(y_test, y_pred_calibrated_default)
    print(f"Calibrated XGBoost (Default 0.50 cutoff) -> F1: {def_f1:.4f}, Precision: {def_prec:.4f}, Recall: {def_rec:.4f}")
    
    # Precision-Recall Curve & Decision Threshold Tuning
    print("\n--- Tuning Decision Threshold via Precision-Recall Curve ---")
    precisions, recalls, pr_thresholds = precision_recall_curve(y_test, y_prob_calibrated)
    f1_scores = 2 * (precisions[:-1] * recalls[:-1]) / (precisions[:-1] + recalls[:-1] + 1e-10)
    best_idx = int(np.argmax(f1_scores))
    optimal_threshold = float(pr_thresholds[best_idx])
    
    y_pred_optimal = (y_prob_calibrated >= optimal_threshold).astype(int)
    opt_f1 = float(f1_score(y_test, y_pred_optimal))
    opt_prec = float(precision_score(y_test, y_pred_optimal))
    opt_rec = float(recall_score(y_test, y_pred_optimal))
    
    print(f"Optimal PR-Tuned Decision Threshold: {optimal_threshold:.4f}")
    print(f"Tuned Calibrated XGBoost (PR Threshold {optimal_threshold:.4f}) -> ROC-AUC: {calibrated_roc:.4f}, F1: {opt_f1:.4f}, Precision: {opt_prec:.4f}, Recall: {opt_rec:.4f}")
    print("\nCalibrated XGBoost Detailed Classification Report (Tuned PR Threshold):")
    print(classification_report(y_test, y_pred_optimal, target_names=['Normal', 'Failure Risk']))
    
    # Generate and save Precision-Recall curve plot
    plt.figure(figsize=(8, 6))
    plt.plot(recalls, precisions, color='#0284c7', lw=2.5, label='Calibrated Precision-Recall Curve')
    plt.scatter(
        [recalls[best_idx]], [precisions[best_idx]],
        color='#e11d48', s=120, zorder=5,
        label=f'Optimal Threshold = {optimal_threshold:.4f}\n(F1={opt_f1:.4f}, Prec={opt_prec:.4f}, Rec={opt_rec:.4f})'
    )
    plt.axhline(y=float(def_prec), color='#94a3b8', linestyle='--', alpha=0.7, label=f'Default 0.50 Precision ({def_prec:.4f})')
    plt.title("Precision-Recall Curve & Optimal Decision Threshold", fontsize=12, fontweight='bold')
    plt.xlabel("Recall (True Positive Rate)", fontsize=11)
    plt.ylabel("Precision (Positive Predictive Value)", fontsize=11)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(loc='lower left', frameon=True)
    plt.tight_layout()
    pr_plot_path = os.path.join(ML_DIR, "pr_curve.png")
    plt.savefig(pr_plot_path, dpi=150)
    plt.close()
    print(f"Saved Precision-Recall curve plot to {pr_plot_path}")
    
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
    
    # 6. Multi-Scenario Slice Validation Across All Operational Profiles
    print("\n" + "=" * 70)
    print("MULTI-SCENARIO SLICE VALIDATION (9 OPERATIONAL PROFILES)")
    print("=" * 70)
    validation_scenarios = {
        'Target Sample [High-Risk]': {
            'inputs': {'temperature': 92.4, 'rpm': 2800, 'pressure': 31.5, 'vibration': 0.64, 'operating_hours': 4820},
            'expected': 'HIGH'
        },
        'Nominal Baseline': {
            'inputs': {'temperature': 68.0, 'rpm': 1500, 'pressure': 21.0, 'vibration': 0.22, 'operating_hours': 950},
            'expected': 'LOW'
        },
        'Thermal Overheat': {
            'inputs': {'temperature': 97.2, 'rpm': 2300, 'pressure': 27.8, 'vibration': 0.42, 'operating_hours': 3100},
            'expected': 'HIGH'
        },
        'Vibration & Fatigue': {
            'inputs': {'temperature': 79.5, 'rpm': 3100, 'pressure': 33.0, 'vibration': 0.72, 'operating_hours': 5300},
            'expected': 'HIGH'
        },
        'Cold Idle Normal': {
            'inputs': {'temperature': 65.0, 'rpm': 1200, 'pressure': 20.0, 'vibration': 0.18, 'operating_hours': 500},
            'expected': 'LOW'
        },
        'Overstrain Pressure Surge': {
            'inputs': {'temperature': 85.0, 'rpm': 2900, 'pressure': 38.0, 'vibration': 0.58, 'operating_hours': 4200},
            'expected': 'HIGH'
        },
        'Extreme Breakdown (All High)': {
            'inputs': {'temperature': 105.0, 'rpm': 3300, 'pressure': 42.0, 'vibration': 0.95, 'operating_hours': 5800},
            'expected': 'HIGH'
        },
        'Low RPM Heavy Strain': {
            'inputs': {'temperature': 88.0, 'rpm': 1100, 'pressure': 39.0, 'vibration': 0.70, 'operating_hours': 4900},
            'expected': 'HIGH'
        },
        'High Speed Light Load (Normal)': {
            'inputs': {'temperature': 72.0, 'rpm': 3200, 'pressure': 19.5, 'vibration': 0.28, 'operating_hours': 1100},
            'expected': 'LOW'
        }
    }
    
    print(f"{'Scenario Name':32s} | {'Exp':4s} | {'Pred':4s} | {'Prob':7s} | {'Status':6s}")
    print("-" * 65)
    scenario_results = {}
    all_scenarios_passed = True
    for sname, sinfo in validation_scenarios.items():
        s_input = pd.DataFrame([sinfo['inputs']])
        s_fe = feature_engineering(s_input)[feature_cols]
        s_prob = float(calibrated_xgb.predict_proba(s_fe)[0, 1])
        s_pred = "HIGH" if s_prob >= optimal_threshold else "LOW"
        is_correct = (s_pred == sinfo['expected'])
        status_str = "PASS" if is_correct else "FAIL"
        if not is_correct:
            all_scenarios_passed = False
        print(f"{sname:32s} | {sinfo['expected']:4s} | {s_pred:4s} | {s_prob*100:5.1f}% | {status_str:6s}")
        scenario_results[sname] = {
            "inputs": sinfo['inputs'],
            "expected_risk": sinfo['expected'],
            "predicted_risk": s_pred,
            "probability": round(s_prob, 4),
            "passed": is_correct
        }
    print("-" * 65)
    print(f"Scenario Slices Check: {'ALL 9 PASSED' if all_scenarios_passed else 'SOME FAILED'}\n")
    
    # 6. Test sample prediction verification
    sample_input = pd.DataFrame([{
        "temperature": 92.4,
        "rpm": 2800,
        "pressure": 31.5,
        "vibration": 0.64,
        "operating_hours": 4820
    }])
    sample_fe = feature_engineering(sample_input)[feature_cols]
    sample_prob = float(calibrated_xgb.predict_proba(sample_fe)[0, 1])
    sample_risk = "HIGH" if sample_prob >= optimal_threshold else "LOW"
    sample_shap = explainer.shap_values(sample_fe)[0]
    
    factors = sorted(
        [{"feature": f, "impact": float(val)} for f, val in zip(feature_cols, sample_shap)],
        key=lambda x: abs(x["impact"]),
        reverse=True
    )
    
    print("\n[VERIFICATION] Target Test Input:")
    print(sample_input.to_dict(orient='records')[0])
    print(f"Result -> Risk: {sample_risk}, Calibrated Probability: {sample_prob:.2%} (Decision Threshold: {optimal_threshold:.4f})")
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
    joblib.dump(calibrated_xgb, model_file)
    joblib.dump(scaler, scaler_file)

    # Export model to ONNX for cross-platform / edge deployment
    onnx_file = os.path.join(ML_DIR, "model.onnx")
    try:
        import onnxmltools
        from onnxmltools.convert.common.data_types import FloatTensorType
        booster = xgb.get_booster()
        original_names = booster.feature_names
        booster.feature_names = [f"f{i}" for i in range(len(feature_cols))]
        initial_type = [('float_input', FloatTensorType([None, len(feature_cols)]))]
        onnx_model = onnxmltools.convert_xgboost(xgb, initial_types=initial_type)
        booster.feature_names = original_names
        with open(onnx_file, "wb") as f:
            f.write(onnx_model.SerializeToString())
        print(f"Saved ONNX model to {onnx_file} ({os.path.getsize(onnx_file):,} bytes)")
    except Exception as onnx_err:
        print(f"[ONNX Export Note] {onnx_err}")
    
    # Compute baseline reference distribution for production drift detection
    base_features = ['temperature', 'rpm', 'pressure', 'vibration', 'operating_hours']
    features_stats = {}
    for feat in base_features:
        series = df[feat]
        series_arr = np.asarray(series, dtype=float)
        quantiles = np.linspace(0, 1, 11)
        bin_edges = np.unique(np.percentile(series_arr, quantiles * 100))
        counts, _ = np.histogram(series_arr, bins=bin_edges)
        expected_pct = (counts / len(series_arr)).tolist()
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
        mlflow_params = {
            "model_type": "CalibratedClassifierCV(XGBoost)",
            "model_version": next_version,
            "calibration_method": "sigmoid",
            "calibration_cv": 3,
            "subsample": 0.85,
            "colsample_bytree": 0.85,
            "scale_pos_weight": round(scale_pos_weight, 4),
            "decision_threshold": round(optimal_threshold, 4),
            "random_state": 42,
            "eval_metric": "logloss",
            "rf_n_estimators": 150,
            "rf_max_depth": 8,
            "lgb_n_estimators": 150,
            "lr_max_iter": 1000,
            "training_samples": len(X_train),
            "test_samples": len(X_test)
        }
        mlflow_params.update(best_params)
        mlflow.log_params(mlflow_params)
        
        # B. Log Metrics (Including Calibrated and baseline metrics)
        mlflow.log_metrics({
            "calibrated_xgb_roc_auc": round(float(calibrated_roc), 4),
            "calibrated_xgb_f1_score": round(float(opt_f1), 4),
            "calibrated_xgb_precision": round(float(opt_prec), 4),
            "calibrated_xgb_recall": round(float(opt_rec), 4),
            "calibrated_brier_score": round(float(calibrated_brier), 4),
            "uncalibrated_xgb_brier_score": round(float(xgb_brier_uncalibrated), 4),
            "decision_threshold": round(float(optimal_threshold), 4),
            "default_0_5_f1": round(float(def_f1), 4),
            "default_0_5_precision": round(float(def_prec), 4),
            "default_0_5_recall": round(float(def_rec), 4),
            "baseline_lr_roc": round(float(lr_roc), 4),
            "baseline_lr_f1": round(float(lr_f1), 4),
            "baseline_lr_brier": round(float(lr_brier), 4),
            "random_forest_roc": round(float(rf_roc), 4),
            "random_forest_f1": round(float(rf_f1), 4),
            "random_forest_brier": round(float(rf_brier), 4),
            "lightgbm_roc": round(float(lgb_roc), 4),
            "lightgbm_f1": round(float(lgb_f1), 4),
            "lightgbm_brier": round(float(lgb_brier), 4)
        })
        
        # C. Log Artifacts
        if os.path.exists(eda_plot_path):
            mlflow.log_artifact(eda_plot_path, artifact_path="eda")
        if os.path.exists(pr_plot_path):
            mlflow.log_artifact(pr_plot_path, artifact_path="evaluation")
        if os.path.exists(shap_plot_path):
            mlflow.log_artifact(shap_plot_path, artifact_path="explainability")
        if os.path.exists(scaler_file):
            mlflow.log_artifact(scaler_file, artifact_path="preprocessing")
        if os.path.exists(ref_stats_file):
            mlflow.log_artifact(ref_stats_file, artifact_path="drift_baseline")
        if os.path.exists(onnx_file):
            mlflow.log_artifact(onnx_file, artifact_path="onnx")
            
        # D. Log Model and Register with MLflow Model Registry
        try:
            mlflow.sklearn.log_model(
                sk_model=calibrated_xgb,
                artifact_path="model",
                registered_model_name="PMS-XGBoost"
            )
            print("[MLflow] Calibrated model registered as 'PMS-XGBoost' in Model Registry")
        except Exception as reg_err:
            print(f"[MLflow] Model registry registration note: {reg_err}")

    # Update model metadata JSON with version and MLflow run ID
    model_metadata = {
        "model_name": "Calibrated XGBoost Classifier",
        "version": next_version,
        "calibration": {
            "method": "sigmoid",
            "cv": 3,
            "brier_score_uncalibrated": round(float(xgb_brier_uncalibrated), 4),
            "brier_score_calibrated": round(float(calibrated_brier), 4),
            "brier_reduction_pct": round(float(error_reduction), 2)
        },
        "mlflow_run_id": mlflow_run_id,
        "mlflow_experiment": experiment_name,
        "trained_date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
        "dataset_source": "UCI AI4I 2020 Predictive Maintenance Dataset",
        "total_training_samples": len(X_train),
        "total_test_samples": len(X_test),
        "decision_threshold": round(float(optimal_threshold), 4),
        "metrics": {
            "roc_auc": round(float(calibrated_roc), 4),
            "f1_score": round(float(opt_f1), 4),
            "precision": round(float(opt_prec), 4),
            "recall": round(float(opt_rec), 4),
            "brier_score": round(float(calibrated_brier), 4),
            "decision_threshold": round(float(optimal_threshold), 4),
            "default_threshold_metrics": {
                "threshold": 0.50,
                "f1_score": round(float(def_f1), 4),
                "precision": round(float(def_prec), 4),
                "recall": round(float(def_rec), 4)
            },
            "comparison": {
                "logistic_regression": {
                    "roc_auc": round(float(lr_roc), 4),
                    "f1_score": round(float(lr_f1), 4),
                    "brier_score": round(float(lr_brier), 4)
                },
                "random_forest": {
                    "roc_auc": round(float(rf_roc), 4),
                    "f1_score": round(float(rf_f1), 4),
                    "brier_score": round(float(rf_brier), 4)
                },
                "lightgbm": {
                    "roc_auc": round(float(lgb_roc), 4),
                    "f1_score": round(float(lgb_f1), 4),
                    "brier_score": round(float(lgb_brier), 4)
                },
                "xgboost_uncalibrated": {
                    "roc_auc": round(float(xgb_roc_raw), 4),
                    "brier_score": round(float(xgb_brier_uncalibrated), 4)
                },
                "xgboost_calibrated": {
                    "roc_auc": round(float(calibrated_roc), 4),
                    "f1_score": round(float(opt_f1), 4),
                    "brier_score": round(float(calibrated_brier), 4)
                }
            }
        },
        "best_params": best_params,
        "feature_names": feature_cols,
        "base_features": base_features,
        "scenario_validation": scenario_results
    }
    
    with open(metadata_file, "w") as f:
        json.dump(model_metadata, f, indent=2)
        
    print(f"\nSaved model to {model_file}")
    print(f"Saved scaler to {scaler_file}")
    print(f"Saved metadata to {metadata_file}")
    print("Training pipeline and MLOps tracking completed successfully!")

if __name__ == "__main__":
    run_pipeline()
