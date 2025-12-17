"""
Lightweight ensembling and regime-switching helpers.
"""

from __future__ import annotations

from typing import Iterable, Literal, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression

Task = Literal["classification", "regression"]


def _normalize_weights(weights: Iterable[float], n: int) -> np.ndarray:
    w = np.array(list(weights)) if weights is not None else np.ones(n)
    if len(w) != n:
        raise ValueError("Weights length must match number of model outputs.")
    if w.sum() == 0:
        raise ValueError("Weights sum to zero.")
    return w / w.sum()


def weighted_average_classification(
    model_probas: Sequence[np.ndarray],
    weights: Iterable[float] | None = None,
    decision_threshold: float = 0.5,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Blend class probabilities from multiple classifiers.
    Accepts probabilities as (n_samples,) for positive class or (n_samples, n_classes).
    """
    if not model_probas:
        raise ValueError("No probabilities provided for ensembling.")
    weights = _normalize_weights(weights, len(model_probas))
    prob_arrays = []
    for p in model_probas:
        if p.ndim == 1:
            prob_arrays.append(np.column_stack([1 - p, p]))
        else:
            prob_arrays.append(p)
    probs = np.stack(prob_arrays, axis=2)
    blended = (probs * weights).sum(axis=2)
    preds = (blended[:, -1] >= decision_threshold).astype(int)
    return preds, blended


def majority_vote(labels: Sequence[np.ndarray], weights: Iterable[float] | None = None, threshold: float = 0.5) -> np.ndarray:
    """
    Majority (or weighted) vote over class labels.
    """
    if not labels:
        raise ValueError("No labels provided for voting.")
    weights = _normalize_weights(weights, len(labels))
    stacked = np.stack(labels, axis=1)
    scores = (stacked * weights).mean(axis=1)
    return (scores >= threshold).astype(int)


def weighted_average_regression(model_preds: Sequence[np.ndarray], weights: Iterable[float] | None = None) -> np.ndarray:
    """
    Weighted mean of regression outputs.
    """
    if not model_preds:
        raise ValueError("No predictions provided for ensembling.")
    weights = _normalize_weights(weights, len(model_preds))
    stacked = np.stack(model_preds, axis=1)
    return (stacked * weights).sum(axis=1)


def average_predictions(
    model_outputs: Sequence[np.ndarray],
    task: Task,
    weights: Iterable[float] | None = None,
    decision_threshold: float = 0.5,
) -> Tuple[np.ndarray, np.ndarray | None]:
    """
    Convenience wrapper to average probabilities (classification) or values (regression).
    Falls back to majority vote if given hard labels for classification.
    """
    if task == "classification":
        first = model_outputs[0]
        if np.issubdtype(first.dtype, np.floating):
            return weighted_average_classification(model_outputs, weights=weights, decision_threshold=decision_threshold)
        preds = majority_vote(model_outputs, weights=weights, threshold=decision_threshold)
        return preds, None
    preds = weighted_average_regression(model_outputs, weights=weights)
    return preds, None


def gate_by_regime(
    low_vol_output: np.ndarray,
    high_vol_output: np.ndarray,
    regime_indicator: pd.Series | np.ndarray,
    threshold: float,
) -> np.ndarray:
    """
    Switch between two model outputs depending on a regime indicator (e.g., VIX).
    """
    regime_indicator = np.asarray(regime_indicator)
    if regime_indicator.shape[0] != low_vol_output.shape[0]:
        raise ValueError("Regime indicator length must match predictions.")
    return np.where(regime_indicator < threshold, low_vol_output, high_vol_output)


def train_meta_blender(
    base_preds_train: np.ndarray,
    y_train: np.ndarray,
    task: Task,
    meta_model=None,
):
    """
    Train a simple meta-model on base model predictions.

    base_preds_train: shape (n_samples, n_models) of probabilities (classification) or values (regression).
    meta_model: optional estimator; defaults to LogisticRegression or LinearRegression.
    """
    if meta_model is None:
        meta_model = LogisticRegression(max_iter=500, class_weight="balanced") if task == "classification" else LinearRegression()
    meta_model.fit(base_preds_train, y_train)
    return meta_model


def predict_meta_blend(meta_model, base_preds_test: np.ndarray, task: Task, decision_threshold: float = 0.5):
    """
    Predict using a trained meta blender.
    """
    if task == "classification":
        if hasattr(meta_model, "predict_proba"):
            proba = meta_model.predict_proba(base_preds_test)
            preds = (proba[:, -1] >= decision_threshold).astype(int)
            return preds, proba
        preds = meta_model.predict(base_preds_test)
        return preds, None
    preds = meta_model.predict(base_preds_test)
    return preds, None
