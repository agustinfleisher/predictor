"""
Training and evaluation utilities for the daily stock models.
"""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)

from . import datasets, models


def evaluate_classification(y_true: pd.Series, y_pred: np.ndarray, y_proba=None) -> Dict[str, float]:
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred),
    }
    if y_proba is not None and y_proba.ndim > 1 and y_proba.shape[1] > 1:
        metrics["roc_auc"] = roc_auc_score(y_true, y_proba[:, 1])
        metrics["log_loss"] = log_loss(y_true, y_proba)
    return metrics


def evaluate_regression(y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
    return {
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": r2_score(y_true, y_pred),
    }


def train_evaluate(
    features: pd.DataFrame,
    model_kind: str,
    task: str,
    test_size: float = 0.2,
    horizon: int = 1,
) -> Tuple[object, Dict[str, float]]:
    """
    Prepare labels, split chronologically, fit model, and compute metrics.
    """
    labeled = datasets.add_targets(features, horizon=horizon, task=task)
    labeled = labeled.dropna(subset=["target"])
    train_df, test_df = datasets.time_series_split(labeled, test_size=test_size)

    X_train, y_train = datasets.build_xy(train_df, target_column="target")
    X_test, y_test = datasets.build_xy(test_df, target_column="target")

    model = models.make_model(model_kind, task=task)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = None
    if task == "classification" and hasattr(model, "predict_proba"):
        y_proba = model.predict_proba(X_test)

    metrics = (
        evaluate_classification(y_test, y_pred, y_proba=y_proba)
        if task == "classification"
        else evaluate_regression(y_test, y_pred)
    )
    return model, metrics
