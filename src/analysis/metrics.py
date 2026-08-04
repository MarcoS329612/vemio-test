"""Forecast error metrics.

Metric choice is a business decision, not a default (standard 04). The rationale
for each is stated here so the report can cite it rather than re-argue it.
"""

from __future__ import annotations

import numpy as np


def mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - predicted)))


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def wape(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Weighted absolute percentage error: Σ|e| / Σ|y|.

    Preferred over MAPE for replenishment. MAPE divides by each week's actual,
    so a quiet week with 20 units can contribute a 300% error and dominate the
    average, and it rewards systematic under-forecasting because the error of an
    over-forecast is unbounded while an under-forecast caps at 100%. WAPE
    weights every unit equally, which is how stock-out and overstock costs are
    actually incurred.
    """
    denominator = float(np.sum(np.abs(actual)))
    if denominator == 0:
        return float("nan")
    return float(np.sum(np.abs(actual - predicted)) / denominator)


def bias(actual: np.ndarray, predicted: np.ndarray) -> float:
    """Signed relative error. Negative = under-forecast = stock-out risk."""
    denominator = float(np.sum(np.abs(actual)))
    if denominator == 0:
        return float("nan")
    return float(np.sum(predicted - actual) / denominator)


def mase(
    actual: np.ndarray, predicted: np.ndarray, train: np.ndarray, season: int = 1
) -> float:
    """Mean absolute scaled error: MAE relative to a naive forecast on the training set.

    Scale-free, so it answers the one question a stakeholder actually asks:
    is this better than doing nothing? Below 1 means yes.
    """
    if len(train) <= season:
        return float("nan")
    naive_errors = np.abs(train[season:] - train[:-season])
    scale = float(np.mean(naive_errors))
    if scale == 0:
        return float("nan")
    return mae(actual, predicted) / scale


def summary(
    actual: np.ndarray, predicted: np.ndarray, train: np.ndarray, season: int = 1
) -> dict[str, float]:
    return {
        "WAPE": round(wape(actual, predicted), 4),
        "MAE": round(mae(actual, predicted), 1),
        "RMSE": round(rmse(actual, predicted), 1),
        "MASE": round(mase(actual, predicted, train, season), 3),
        "bias": round(bias(actual, predicted), 4),
    }
