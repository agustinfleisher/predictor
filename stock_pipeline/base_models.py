"""
Base model factories that return untrained model instances.

Models are scikit-learn compatible unless otherwise requested.
"""

from __future__ import annotations

from typing import Literal

from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

Task = Literal["classification", "regression"]


def make_logistic(max_iter: int = 1000, class_weight: str | None = "balanced") -> Pipeline:
    """
    Logistic regression pipeline with standardization (classification only).
    """
    return Pipeline([("scaler", StandardScaler()), ("model", LogisticRegression(max_iter=max_iter, class_weight=class_weight))])


def make_random_forest(
    task: Task,
    n_estimators: int = 300,
    max_depth: int | None = None,
    random_state: int = 42,
    n_jobs: int = -1,
):
    """
    Random forest for classification or regression.
    """
    if task == "classification":
        return RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=random_state, n_jobs=n_jobs)
    return RandomForestRegressor(n_estimators=n_estimators, max_depth=max_depth, random_state=random_state, n_jobs=n_jobs)


def make_gradient_boosting(
    task: Task,
    n_estimators: int = 200,
    learning_rate: float = 0.05,
    max_depth: int = 3,
    random_state: int = 42,
):
    """
    Gradient boosting trees for classification or regression.
    """
    if task == "classification":
        return GradientBoostingClassifier(
            n_estimators=n_estimators, learning_rate=learning_rate, max_depth=max_depth, random_state=random_state
        )
    return GradientBoostingRegressor(
        n_estimators=n_estimators, learning_rate=learning_rate, max_depth=max_depth, random_state=random_state
    )


def make_mlp(
    task: Task,
    hidden_layers: tuple[int, ...] = (64, 32),
    learning_rate_init: float = 1e-3,
    max_iter: int = 300,
    random_state: int = 42,
) -> Pipeline:
    """
    Simple feedforward neural net (MLP) with standardization.
    """
    if task == "classification":
        model = MLPClassifier(
            hidden_layer_sizes=hidden_layers,
            activation="relu",
            learning_rate_init=learning_rate_init,
            max_iter=max_iter,
            early_stopping=True,
            random_state=random_state,
        )
    else:
        model = MLPRegressor(
            hidden_layer_sizes=hidden_layers,
            activation="relu",
            learning_rate_init=learning_rate_init,
            max_iter=max_iter,
            early_stopping=True,
            random_state=random_state,
        )
    return Pipeline([("scaler", StandardScaler()), ("model", model)])
