"""
Factory functions for supported models and simple model selection helpers.
"""

from __future__ import annotations

from typing import Callable, Dict, Iterable, Literal, Sequence, Tuple

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import accuracy_score, mean_squared_error, roc_auc_score
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

Task = Literal["classification", "regression"]


def _logistic():
    return Pipeline([("scaler", StandardScaler()), ("model", LogisticRegression(max_iter=1000, class_weight="balanced"))])


def _random_forest_cls():
    return RandomForestClassifier(n_estimators=300, max_depth=None, random_state=42, n_jobs=-1)


def _random_forest_reg():
    return RandomForestRegressor(n_estimators=300, max_depth=None, random_state=42, n_jobs=-1)


def _gboost_cls():
    return GradientBoostingClassifier(n_estimators=200, learning_rate=0.05, max_depth=3, random_state=42)


def _gboost_reg():
    return GradientBoostingRegressor(n_estimators=200, learning_rate=0.05, max_depth=3, random_state=42)


def _mlp_cls():
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "model",
                MLPClassifier(
                    hidden_layer_sizes=(64, 32),
                    activation="relu",
                    learning_rate_init=1e-3,
                    max_iter=300,
                    early_stopping=True,
                    random_state=42,
                ),
            ),
        ]
    )


def _mlp_reg():
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "model",
                MLPRegressor(
                    hidden_layer_sizes=(64, 32),
                    activation="relu",
                    learning_rate_init=1e-3,
                    max_iter=400,
                    early_stopping=True,
                    random_state=42,
                ),
            ),
        ]
    )


def _linear():
    return Pipeline([("scaler", StandardScaler()), ("model", LinearRegression())])


MODEL_REGISTRY: Dict[str, Dict[Task, Callable[[], object]]] = {
    "logistic": {"classification": _logistic},
    "random_forest": {"classification": _random_forest_cls, "regression": _random_forest_reg},
    "gboost": {"classification": _gboost_cls, "regression": _gboost_reg},
    "mlp": {"classification": _mlp_cls, "regression": _mlp_reg},
    "linear": {"regression": _linear},
}


def make_model(kind: str, task: Task):
    """
    Create a model instance for the requested kind/task.
    """
    kind = kind.lower()
    task = task.lower()
    if kind not in MODEL_REGISTRY or task not in MODEL_REGISTRY[kind]:
        raise ValueError(f"Unsupported model kind '{kind}' for task '{task}'.")
    return MODEL_REGISTRY[kind][task]()


def supported_models(task: Task | None = None) -> list[str]:
    if task is None:
        return sorted(MODEL_REGISTRY.keys())
    return sorted([k for k, v in MODEL_REGISTRY.items() if task in v])


def select_best_model(
    model_kinds: Iterable[str],
    task: Task,
    X_train,
    y_train,
    X_val,
    y_val,
    scorer: Callable[[np.ndarray, np.ndarray], float] | None = None,
) -> Tuple[str, object, float]:
    """
    Fit candidate models and choose the best on a validation set.

    Default scorer: ROC AUC (if proba available) or accuracy for classification;
    negative RMSE for regression.
    """
    task = task.lower()
    best_kind, best_model, best_score = None, None, -np.inf

    for kind in model_kinds:
        model = make_model(kind, task)
        model.fit(X_train, y_train)

        if scorer is not None:
            score = scorer(model, X_val, y_val)
        else:
            if task == "classification":
                if hasattr(model, "predict_proba"):
                    proba = model.predict_proba(X_val)
                    score = roc_auc_score(y_val, proba[:, -1])
                else:
                    preds = model.predict(X_val)
                    score = accuracy_score(y_val, preds)
            else:
                preds = model.predict(X_val)
                rmse = np.sqrt(mean_squared_error(y_val, preds))
                score = -rmse  # higher is better

        if score > best_score:
            best_kind, best_model, best_score = kind, model, score

    if best_model is None:
        raise ValueError("No models were successfully evaluated.")
    return best_kind, best_model, best_score
