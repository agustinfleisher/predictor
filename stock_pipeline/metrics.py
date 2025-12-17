"""
Performance metrics utilities for classification and regression.
"""

from __future__ import annotations

from typing import Dict

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


def classification_metrics(y_true: pd.Series, y_pred: np.ndarray, y_proba=None) -> Dict[str, float]:
    """
    Compute common classification metrics; includes ROC AUC and log loss when probabilities provided.
    """
    out = {
        "accuracy": accuracy_score(y_true, y_pred),
        "f1": f1_score(y_true, y_pred),
    }
    if y_proba is not None and y_proba.ndim > 1 and y_proba.shape[1] > 1:
        out["roc_auc"] = roc_auc_score(y_true, y_proba[:, -1])
        out["log_loss"] = log_loss(y_true, y_proba)
    return out


def regression_metrics(y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Compute common regression metrics.
    """
    return {
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": r2_score(y_true, y_pred),
    }
