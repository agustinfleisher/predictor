"""
Modular daily stock prediction toolkit.

The package exposes helpers for fetching data, engineering features,
building labeled datasets, training/evaluating models, ensembling,
and walk-forward backtesting.
"""

from . import backtester, backtesting, base_models, data, datasets, ensemble, features, metrics, models, regimes, training

__all__ = [
    "data",
    "datasets",
    "features",
    "models",
    "training",
    "ensemble",
    "backtesting",
    "backtester",
    "regimes",
    "base_models",
    "metrics",
]
