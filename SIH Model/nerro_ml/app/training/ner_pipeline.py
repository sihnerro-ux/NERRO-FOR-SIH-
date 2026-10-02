"""Versioned training pipeline for the NER-wide prototype dataset.

Validation holds out complete corridors. This is stricter than a random row
split because observations from a validation corridor never appear in the
training partition.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    root_mean_squared_error,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier, XGBRegressor

from app.data.preprocessor import DELAY_FEATURES, RISK_FEATURES


RISK_QUALITY_GATE = {"macro_f1_min": 0.75, "accuracy_min": 0.75}
DELAY_QUALITY_GATE = {"r2_min": 0.70, "mae_max": 90.0}


def corridor_holdout_indices(
    dataset: pd.DataFrame,
    *,
    test_size: float = 0.20,
    seed: int = 26002,
) -> tuple[np.ndarray, np.ndarray]:
    """Return train/test indices with no corridor shared between partitions."""
    if not {"corridor_id", "state"}.issubset(dataset.columns):
        raise ValueError("Dataset must include state and corridor_id for validation.")
    rng = np.random.default_rng(seed)
    test_corridors: set[str] = set()
    for _, state_rows in dataset.groupby("state", sort=True):
        corridors = np.array(sorted(state_rows["corridor_id"].unique()))
        holdout_count = max(1, int(round(len(corridors) * test_size)))
        selected = rng.choice(corridors, size=holdout_count, replace=False)
        test_corridors.update(str(value) for value in selected)
    test_mask = dataset["corridor_id"].isin(test_corridors).to_numpy()
    return np.flatnonzero(~test_mask), np.flatnonzero(test_mask)


def _risk_candidates(seed: int) -> dict[str, Any]:
    return {
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=1000, random_state=seed)),
        ]),
        "RandomForest": RandomForestClassifier(
            n_estimators=200, max_depth=12, min_samples_leaf=5,
            random_state=seed, n_jobs=-1,
        ),
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=160, max_depth=4, learning_rate=0.08,
            random_state=seed,
        ),
        "XGBoost": XGBClassifier(
            n_estimators=180, max_depth=5, learning_rate=0.08,
            eval_metric="logloss", random_state=seed, n_jobs=-1,
        ),
    }


def _delay_candidates(seed: int) -> dict[str, Any]:
    return {
        "LinearRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("model", LinearRegression()),
        ]),
        "Ridge": Pipeline([
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=1.0)),
        ]),
        "RandomForest": RandomForestRegressor(
            n_estimators=200, max_depth=14, min_samples_leaf=5,
            random_state=seed, n_jobs=-1,
        ),
        "GradientBoosting": GradientBoostingRegressor(
            n_estimators=160, max_depth=5, learning_rate=0.08,
            random_state=seed,
        ),
        "XGBoost": XGBRegressor(
            n_estimators=180, max_depth=5, learning_rate=0.08,
            random_state=seed, n_jobs=-1,
        ),
    }


def _risk_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_f1": round(float(f1_score(y_true, y_pred, average="macro")), 4),
    }


def _delay_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "rmse": round(float(root_mean_squared_error(y_true, y_pred)), 2),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 2),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
    }


def _group_metrics(
    frame: pd.DataFrame,
    predictions: np.ndarray,
    *,
    target: str,
    group: str,
    metric_fn: Any,
) -> dict[str, dict[str, float]]:
    results: dict[str, dict[str, float]] = {}
    indexed_predictions = pd.Series(predictions, index=frame.index)
    for name, subset in frame.groupby(group, sort=True):
        results[str(name)] = metric_fn(
            subset[target], indexed_predictions.loc[subset.index].to_numpy()
        )
    return results


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def train_versioned_models(
    dataset_path: Path,
    output_dir: Path,
    *,
    version: str,
    seed: int = 26002,
) -> dict[str, Any]:
    """Train, validate, refit and save a compatible versioned model pair."""
    if output_dir.exists():
        raise FileExistsError(
            f"Version already exists and will not be overwritten: {output_dir}"
        )
    dataset = pd.read_csv(dataset_path)
    required = set(RISK_FEATURES + DELAY_FEATURES + [
        "disrupted", "delay_minutes", "state", "corridor_id", "data_mode"
    ])
    missing = sorted(required.difference(dataset.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")
    if set(dataset["data_mode"]) != {"SIMULATED"}:
        raise ValueError("This prototype pipeline only accepts explicitly SIMULATED data.")

    train_idx, test_idx = corridor_holdout_indices(dataset, seed=seed)
    train = dataset.iloc[train_idx].copy()
    test = dataset.iloc[test_idx].copy()

    risk_results: dict[str, dict[str, Any]] = {}
    for name, candidate in _risk_candidates(seed).items():
        candidate.fit(train[RISK_FEATURES], train["disrupted"])
        prediction = candidate.predict(test[RISK_FEATURES])
        risk_results[name] = {"model": candidate, **_risk_metrics(test["disrupted"], prediction)}
    best_risk_name = max(risk_results, key=lambda name: risk_results[name]["macro_f1"])
    best_risk = risk_results[best_risk_name]["model"]
    risk_predictions = best_risk.predict(test[RISK_FEATURES])

    delay_results: dict[str, dict[str, Any]] = {}
    for name, candidate in _delay_candidates(seed).items():
        candidate.fit(train[DELAY_FEATURES], train["delay_minutes"])
        prediction = candidate.predict(test[DELAY_FEATURES])
        delay_results[name] = {"model": candidate, **_delay_metrics(test["delay_minutes"], prediction)}
    best_delay_name = min(delay_results, key=lambda name: delay_results[name]["rmse"])
    best_delay = delay_results[best_delay_name]["model"]
    delay_predictions = best_delay.predict(test[DELAY_FEATURES])

    risk_holdout = _risk_metrics(test["disrupted"], risk_predictions)
    delay_holdout = _delay_metrics(test["delay_minutes"], delay_predictions)
    gates = {
        "risk": (
            risk_holdout["macro_f1"] >= RISK_QUALITY_GATE["macro_f1_min"]
            and risk_holdout["accuracy"] >= RISK_QUALITY_GATE["accuracy_min"]
        ),
        "delay": (
            delay_holdout["r2"] >= DELAY_QUALITY_GATE["r2_min"]
            and delay_holdout["mae"] <= DELAY_QUALITY_GATE["mae_max"]
        ),
    }

    # Refit selected estimators on all available prototype data only after the
    # untouched-corridor evaluation has been captured.
    best_risk.fit(dataset[RISK_FEATURES], dataset["disrupted"])
    best_delay.fit(dataset[DELAY_FEATURES], dataset["delay_minutes"])

    output_dir.mkdir(parents=True, exist_ok=False)
    risk_path = output_dir / "risk_classifier.pkl"
    delay_path = output_dir / "delay_regressor.pkl"
    joblib.dump(best_risk, risk_path)
    joblib.dump(best_delay, delay_path)

    report: dict[str, Any] = {
        "version": version,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "VALIDATED_PROTOTYPE" if all(gates.values()) else "QUALITY_GATE_FAILED",
        "data_mode": "SIMULATED",
        "operational_use": False,
        "dataset": {
            "path": str(dataset_path.resolve()),
            "rows": len(dataset),
            "states": int(dataset["state"].nunique()),
            "corridors": int(dataset["corridor_id"].nunique()),
        },
        "validation": {
            "strategy": "state_stratified_group_holdout_by_corridor",
            "seed": seed,
            "train_rows": len(train),
            "test_rows": len(test),
            "train_corridors": sorted(train["corridor_id"].unique().tolist()),
            "test_corridors": sorted(test["corridor_id"].unique().tolist()),
        },
        "risk_classifier": {
            "selected_model": best_risk_name,
            "features": RISK_FEATURES,
            "holdout": risk_holdout,
            "quality_gate": {**RISK_QUALITY_GATE, "passed": gates["risk"]},
            "leaderboard": [
                {"model": name, "macro_f1": values["macro_f1"], "accuracy": values["accuracy"]}
                for name, values in sorted(
                    risk_results.items(), key=lambda item: -item[1]["macro_f1"]
                )
            ],
            "by_state": _group_metrics(
                test, risk_predictions, target="disrupted", group="state", metric_fn=_risk_metrics
            ),
            "by_corridor": _group_metrics(
                test, risk_predictions, target="disrupted", group="corridor_id", metric_fn=_risk_metrics
            ),
        },
        "delay_regressor": {
            "selected_model": best_delay_name,
            "features": DELAY_FEATURES,
            "holdout": delay_holdout,
            "quality_gate": {**DELAY_QUALITY_GATE, "passed": gates["delay"]},
            "leaderboard": [
                {"model": name, "rmse": values["rmse"], "mae": values["mae"], "r2": values["r2"]}
                for name, values in sorted(
                    delay_results.items(), key=lambda item: item[1]["rmse"]
                )
            ],
            "by_state": _group_metrics(
                test, delay_predictions, target="delay_minutes", group="state", metric_fn=_delay_metrics
            ),
            "by_corridor": _group_metrics(
                test, delay_predictions, target="delay_minutes", group="corridor_id", metric_fn=_delay_metrics
            ),
        },
        "artifacts": {
            "risk_classifier": {"file": risk_path.name, "sha256": _sha256(risk_path)},
            "delay_regressor": {"file": delay_path.name, "sha256": _sha256(delay_path)},
        },
        "warning": "Validated only on synthetic prototype data; not approved for operational decisions.",
    }
    (output_dir / "training_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report
