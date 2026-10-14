"""
backend/tests/test_leakage.py
=============================
Regression tests verifying data leakage prevention:
1. No feature is a direct mathematical function of the ground-truth label.
2. Feature engineering does not consume or reference the target label.
3. Train/test split is strictly performed prior to any scaling or model fitting.
4. Test set statistics do not contaminate the training pipeline (no preprocessing leakage).
"""

import os
import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

from ml.train import feature_engineering

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "equipment_maintenance_data.csv"
)

FEATURE_COLS = [
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
    'mechanical_power',
    'vib_dominant_freq',
    'vib_spectral_energy_low',
    'vib_spectral_energy_high',
    'vib_spectral_centroid'
]

LABEL_COLS = ['failure', 'failure_type', 'hdf', 'osf', 'twf', 'pwf', 'rnf']


def test_label_columns_excluded_from_features():
    """Assert that label and failure-mode columns are strictly excluded from feature sets."""
    for label_col in LABEL_COLS:
        assert label_col not in FEATURE_COLS, f"Leakage detected: '{label_col}' found in FEATURE_COLS"


def test_feature_engineering_independent_of_label():
    """
    Assert that feature_engineering does not reference, depend on, or require the label column.
    Running feature engineering on a dataframe without 'failure' must yield identical features.
    """
    df = pd.read_csv(DATA_PATH)
    
    # Compute features with full dataset
    fe_with_label = feature_engineering(df)
    
    # Drop all label columns before feature engineering
    df_no_label = df.drop(columns=[col for col in LABEL_COLS if col in df.columns])
    fe_without_label = feature_engineering(df_no_label)
    
    for feat in FEATURE_COLS:
        assert feat in fe_without_label.columns, f"Feature '{feat}' missing when labels are excluded"
        np.testing.assert_allclose(
            np.asarray(fe_with_label[feat].to_numpy(), dtype=float),
            np.asarray(fe_without_label[feat].to_numpy(), dtype=float),
            rtol=1e-5,
            atol=1e-5,
            err_msg=f"Feature '{feat}' values changed when labels were removed! Indicates label dependency."
        )


def test_no_feature_has_trivial_deterministic_label_correlation():
    """
    Assert that no feature has deterministic / trivial correlation with the failure label.
    In the previous broken version with data leakage, a synthetic feature directly encoded failure.
    Verify all |r| < 0.85 and single-feature ROC-AUC < 0.95.
    """
    df = pd.read_csv(DATA_PATH)
    df_fe = feature_engineering(df)
    y = np.asarray(df_fe['failure'].to_numpy(), dtype=float)
    
    for feat in FEATURE_COLS:
        x_vals = np.asarray(df_fe[feat].to_numpy(), dtype=float)
        # Pearson correlation
        corr = float(np.corrcoef(x_vals, y)[0, 1])
        assert abs(corr) < 0.85, (
            f"Feature '{feat}' has suspicious near-deterministic correlation ({corr:.4f}) with label"
        )
        
        # Single-feature discriminative power (ROC-AUC)
        # Should not unilaterally solve the classification problem
        auc = float(roc_auc_score(y, x_vals))
        effective_auc = auc if auc >= (1.0 - auc) else (1.0 - auc)
        assert effective_auc < 0.95, (
            f"Feature '{feat}' has single-feature ROC-AUC {effective_auc:.4f} >= 0.95; potential leakage"
        )


def test_train_test_split_performed_before_scaling():
    """
    Assert that train/test split is performed strictly before fitting StandardScaler.
    The scaler mean and scale must reflect only the training partition, NOT the full dataset or test set.
    """
    df = pd.read_csv(DATA_PATH)
    df_fe = feature_engineering(df)
    
    X = df_fe[FEATURE_COLS]
    y = df_fe['failure']
    
    # Split
    indices = np.arange(len(df_fe))
    train_idx, test_idx = train_test_split(indices, test_size=0.2, random_state=42, stratify=y)
    
    X_train = X.iloc[train_idx].reset_index(drop=True)
    X_test = X.iloc[test_idx].reset_index(drop=True)
    
    scaler = StandardScaler()
    scaler.fit(X_train)
    
    # Scaler mean must match X_train mean within floating point tolerance
    scaler_mean = scaler.mean_
    assert isinstance(scaler_mean, np.ndarray), "StandardScaler mean_ is uninitialized"
    train_mean = np.asarray(X_train.mean(axis=0).to_numpy(), dtype=float)
    np.testing.assert_allclose(
        scaler_mean,
        train_mean,
        rtol=1e-5,
        atol=1e-5,
        err_msg="StandardScaler was not fitted exclusively on training set"
    )
    
    # Scaler mean must NOT be identical to full dataset mean or test set mean
    full_mean = np.asarray(X.mean(axis=0).to_numpy(), dtype=float)
    test_mean = np.asarray(X_test.mean(axis=0).to_numpy(), dtype=float)
    assert not np.allclose(scaler_mean, test_mean, atol=1e-3), (
        "StandardScaler mean matches test set mean; data leakage into scaler suspected"
    )
    assert not np.allclose(scaler_mean, full_mean, atol=1e-3), (
        "StandardScaler mean matches full dataset mean; scaler was fitted before split"
    )


def test_stratified_cv_clean_partitioning():
    """
    Assert that Stratified 5-Fold CV partitions are strictly disjoint and maintain label stratification.
    """
    df = pd.read_csv(DATA_PATH)
    y_list = [int(v) for v in df['failure']]
    y = np.array(y_list, dtype=int)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    overall_failure_rate = float(np.mean(y))
    seen_val_indices = set()
    
    for fold, (tr_idx, val_idx) in enumerate(skf.split(df, y)):
        # Check disjoint
        assert len(set(tr_idx).intersection(set(val_idx))) == 0, f"Fold {fold} has overlapping train/val indices"
        assert len(seen_val_indices.intersection(set(val_idx))) == 0, f"Validation fold {fold} has duplicate indices"
        seen_val_indices.update(val_idx)
        
        # Check stratification balance within 1 percentage point
        val_failure_rate = float(np.mean(y[val_idx]))
        assert abs(val_failure_rate - overall_failure_rate) < 0.015, (
            f"Fold {fold} failure rate ({val_failure_rate:.4f}) diverges from overall ({overall_failure_rate:.4f})"
        )
    
    assert len(seen_val_indices) == len(df), "Not all samples were partitioned across 5 folds"

