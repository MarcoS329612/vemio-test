"""Weekly demand forecasting (Challenge A).

Everything here is temporally honest by construction: models receive only the
training array, and evaluation uses rolling origins rather than one lucky split
(standard 04).
"""

from __future__ import annotations

import warnings
from collections.abc import Callable

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from statsmodels.tsa.holtwinters import ExponentialSmoothing

SEASON = 52  # weeks

Model = Callable[[np.ndarray, int, np.ndarray], np.ndarray]


# --------------------------------------------------------------------- models


def naive_last(train: np.ndarray, horizon: int, weeks: np.ndarray) -> np.ndarray:
    """Persistence: tomorrow looks like today."""
    return np.repeat(train[-1], horizon)


def moving_average_4(train: np.ndarray, horizon: int, weeks: np.ndarray) -> np.ndarray:
    """Flat forecast at the mean of the last four weeks."""
    return np.repeat(float(np.mean(train[-4:])), horizon)


def seasonal_naive(train: np.ndarray, horizon: int, weeks: np.ndarray) -> np.ndarray:
    """Repeat the same week of last year. Falls back to the 4-week mean if the
    history is shorter than a full season."""
    if len(train) < SEASON:
        return moving_average_4(train, horizon, weeks)
    tail = train[-SEASON:]
    return np.array([tail[i % SEASON] for i in range(horizon)], dtype=float)


def ets_damped(train: np.ndarray, horizon: int, weeks: np.ndarray) -> np.ndarray:
    """Exponential smoothing with a damped additive trend.

    Seasonality is deliberately not modelled here: a weekly seasonal period of
    52 needs at least two full cycles, and this history has ~1.4. Asking for it
    would fit noise and call it a season.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            fitted = ExponentialSmoothing(
                train, trend="add", damped_trend=True, seasonal=None,
                initialization_method="estimated",
            ).fit(optimized=True)
            return np.asarray(fitted.forecast(horizon), dtype=float)
        except Exception:
            return moving_average_4(train, horizon, weeks)


def _fourier(week_of_year: np.ndarray, order: int) -> np.ndarray:
    angle = 2 * np.pi * week_of_year / 52.0
    return np.column_stack(
        [f(k * angle) for k in range(1, order + 1) for f in (np.sin, np.cos)]
    )


def _design(weeks: np.ndarray, order: int, origin: float) -> np.ndarray:
    trend = ((weeks - origin) / 52.0).reshape(-1, 1)
    return np.hstack([trend, _fourier(weeks, order)])


def harmonic_ridge(
    train: np.ndarray, horizon: int, weeks: np.ndarray, order: int = 2
) -> np.ndarray:
    """Ridge on a linear trend plus Fourier terms for the annual cycle.

    Deterministic in the future — no lagged inputs — so there is nothing to
    recursively feed back and nothing that could accidentally see a test-period
    value. Ridge rather than OLS because 72 observations against 5 correlated
    seasonal regressors overfits readily.
    """
    origin = float(weeks[0])
    x_train = _design(weeks, order, origin)
    future_weeks = weeks[-1] + np.arange(1, horizon + 1)
    x_future = _design(future_weeks, order, origin)

    model = Ridge(alpha=1.0)
    model.fit(x_train, np.log1p(train))
    return np.expm1(model.predict(x_future)).clip(min=0.0)


def damped_drift(
    train: np.ndarray, horizon: int, weeks: np.ndarray, phi: float = 0.85, window: int = 8
) -> np.ndarray:
    """Recent level plus a geometrically damped continuation of the recent slope.

    Added because every level-only model under-forecast by 13–30% on the rolling
    origins: the series drift upward and a flat forecast cannot follow. Damping
    stops that slope being extrapolated indefinitely, which is the failure mode
    of an undamped trend on a 12-week horizon.
    """
    if len(train) < window + 1:
        return moving_average_4(train, horizon, weeks)
    level = float(np.mean(train[-4:]))
    recent, earlier = np.mean(train[-window // 2:]), np.mean(train[-window: -window // 2])
    slope = (recent - earlier) / (window / 2)
    damping = np.cumsum(phi ** np.arange(1, horizon + 1))
    return np.clip(level + slope * damping, 0.0, None)


def ensemble(train: np.ndarray, horizon: int, weeks: np.ndarray) -> np.ndarray:
    """Mean of the moving average, damped drift and ETS forecasts.

    Combining forecasts that fail differently is the cheapest reliable
    improvement in forecasting practice — no single component has to be right.
    """
    parts = [
        moving_average_4(train, horizon, weeks),
        damped_drift(train, horizon, weeks),
        ets_damped(train, horizon, weeks),
    ]
    return np.mean(np.vstack(parts), axis=0)


MODELS: dict[str, Model] = {
    "naive (last week)": naive_last,
    "moving average (4w)": moving_average_4,
    "seasonal naive (52w)": seasonal_naive,
    "ETS (damped trend)": ets_damped,
    "harmonic ridge": harmonic_ridge,
    "damped drift": damped_drift,
    "ensemble (MA + drift + ETS)": ensemble,
}

BASELINES = ("naive (last week)", "moving average (4w)", "seasonal naive (52w)")


# ----------------------------------------------------------------- evaluation


def rolling_origins(
    n_observations: int, horizon: int, n_origins: int, step: int = 3
) -> list[int]:
    """Expanding-window origins, latest first, each leaving a full horizon behind.

    Rolling origins rather than one split: a single holdout measures how a model
    did on one particular quarter, which is a claim about that quarter, not
    about the model.
    """
    last = n_observations - horizon
    origins = [last - i * step for i in range(n_origins)]
    return sorted(o for o in origins if o >= 2 * horizon)


def evaluate(
    units: np.ndarray,
    week_of_year: np.ndarray,
    horizon: int,
    n_origins: int = 5,
    step: int = 3,
) -> pd.DataFrame:
    """Score every model across rolling origins. One row per model per origin."""
    rows = []
    for origin in rolling_origins(len(units), horizon, n_origins, step):
        train, test = units[:origin], units[origin : origin + horizon]
        train_weeks = week_of_year[:origin]
        if len(test) < horizon:
            continue
        for name, model in MODELS.items():
            predicted = np.asarray(model(train, horizon, train_weeks), dtype=float)
            from . import metrics  # local import keeps the module dependency-light

            rows.append(
                {
                    "model": name,
                    "origin_week": origin,
                    "train_weeks": len(train),
                    **metrics.summary(test, predicted, train, season=1),
                }
            )
    return pd.DataFrame(rows)


def aggregate_scores(scores: pd.DataFrame) -> pd.DataFrame:
    """Average each model across origins, ordered by WAPE.

    ``skill_vs_best_baseline`` is the column that decides whether a candidate
    earns its complexity: below 1.0 means it beat every baseline, above means it
    did not. MASE here is scaled by the *one-step* naive error on the training
    set, so values above 1 are expected at a 12-week horizon — it compares
    models and SKUs, it does not certify adequacy on its own.
    """
    out = (
        scores.groupby("model")
        .agg(
            origins=("origin_week", "nunique"),
            WAPE=("WAPE", "mean"),
            MAE=("MAE", "mean"),
            RMSE=("RMSE", "mean"),
            MASE=("MASE", "mean"),
            bias=("bias", "mean"),
        )
        .round(4)
        .reset_index()
    )
    best_baseline = out.loc[out["model"].isin(BASELINES), "WAPE"].min()
    out["skill_vs_best_baseline"] = (out["WAPE"] / best_baseline).round(3)
    return out.sort_values("WAPE").reset_index(drop=True)


def forecast_forward(
    units: np.ndarray, week_of_year: np.ndarray, horizon: int, model_name: str
) -> np.ndarray:
    """Refit the chosen model on the full history and project forward."""
    return np.asarray(
        MODELS[model_name](units, horizon, week_of_year), dtype=float
    ).clip(min=0.0)
