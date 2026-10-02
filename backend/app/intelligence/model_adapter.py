"""Safe adapter around the submitted ML artefacts.

Predictions are advisory only: a model can raise a risk band or estimate a
delay, but never changes road accessibility to BLOCKED. That state requires a
verified field or control-room report.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.models import RoadSegment


ROOT_DIR = Path(__file__).resolve().parents[3]
MODEL_DIR = ROOT_DIR / "SIH Model" / "nerro_ml" / "trained_models"
ACTIVE_MODEL_POINTER = MODEL_DIR / "active_model.json"
# The pointer is read at service startup; uvicorn reloads when this adapter changes.
RISK_FEATURES = [
    "rainfall_mm", "slope_deg", "elevation_m", "past_incident_count",
    "is_monsoon", "weather_severity", "road_condition", "traffic_density",
]
DELAY_FEATURES = [
    "distance_km", "traffic_density", "rainfall_mm", "road_condition",
    "historical_avg_minutes", "active_incidents",
]


@dataclass(frozen=True)
class Advisory:
    probability: float
    band: str
    delay_minutes: float


class ModelAdapter:
    def __init__(self) -> None:
        self.risk_model = None
        self.delay_model = None
        self.status = "UNAVAILABLE"
        self.detail = "ML artefacts have not been loaded."
        self.version = "unavailable"
        self.data_mode = "UNKNOWN"
        self._load()

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _resolve_artifacts(self) -> tuple[Path, Path]:
        if not ACTIVE_MODEL_POINTER.exists():
            self.version = "legacy-submitted"
            return MODEL_DIR / "risk_classifier.pkl", MODEL_DIR / "delay_regressor.pkl"

        pointer = json.loads(ACTIVE_MODEL_POINTER.read_text(encoding="utf-8"))
        version = str(pointer["version"])
        version_dir = (MODEL_DIR / "versions" / version).resolve()
        versions_root = (MODEL_DIR / "versions").resolve()
        if versions_root not in version_dir.parents:
            raise ValueError("Invalid active model version path")
        report = json.loads((version_dir / "training_report.json").read_text(encoding="utf-8"))
        if report["status"] != "VALIDATED_PROTOTYPE":
            raise ValueError("Active model did not pass its validation gate")
        for key in ("risk_classifier", "delay_regressor"):
            artifact = report["artifacts"][key]
            path = version_dir / artifact["file"]
            if self._sha256(path) != artifact["sha256"]:
                raise ValueError(f"Checksum mismatch for {key}")
        self.version = version
        self.data_mode = str(report.get("data_mode", "UNKNOWN"))
        return version_dir / "risk_classifier.pkl", version_dir / "delay_regressor.pkl"

    def _load(self) -> None:
        try:
            import joblib

            risk_path, delay_path = self._resolve_artifacts()
            self.risk_model = joblib.load(risk_path)
            self.delay_model = joblib.load(delay_path)
            self.status = "AVAILABLE"
            self.detail = f"Model {self.version} loaded for advisory inference ({self.data_mode} data)."
        except Exception as exc:  # service stays usable even when artefacts are unavailable
            self.status = "UNAVAILABLE"
            self.detail = f"ML advisory unavailable: {type(exc).__name__}"
            self.risk_model = None
            self.delay_model = None

    @staticmethod
    def _road_condition(value: str) -> int:
        return {"GOOD": 1, "FAIR": 2, "POOR": 3}.get(value.upper(), 2)

    @staticmethod
    def _weather_severity(rainfall: float) -> int:
        if rainfall >= 100:
            return 5
        if rainfall >= 75:
            return 4
        if rainfall >= 45:
            return 3
        if rainfall >= 20:
            return 2
        return 1

    @staticmethod
    def _band(probability: float) -> str:
        if probability < 0.25:
            return "LOW"
        if probability < 0.55:
            return "MODERATE"
        if probability < 0.80:
            return "HIGH"
        return "CRITICAL"

    def assess(self, road: RoadSegment, incident_count: int) -> Advisory | None:
        return self.assess_features(
            distance_km=road.distance_km,
            rainfall_mm=road.rainfall_mm_24h,
            slope_deg=road.slope_degrees,
            elevation_m=300 + road.slope_degrees * 25,
            incident_count=incident_count,
            road_condition=road.road_condition,
        )

    def assess_features(
        self,
        *,
        distance_km: float,
        rainfall_mm: float,
        slope_deg: float,
        elevation_m: float,
        incident_count: int,
        road_condition: str = "FAIR",
        traffic_density: float = 0.4,
    ) -> Advisory | None:
        if self.status != "AVAILABLE" or self.risk_model is None or self.delay_model is None:
            return None
        try:
            import pandas as pd

            condition = self._road_condition(road_condition)
            historical_minutes = distance_km / (48 if condition == 1 else 34 if condition == 2 else 24) * 60
            is_monsoon = int(datetime.now(UTC).month in {5, 6, 7, 8, 9, 10})
            risk_features = pd.DataFrame([[
                rainfall_mm, slope_deg, elevation_m,
                incident_count, is_monsoon, self._weather_severity(rainfall_mm),
                condition, traffic_density,
            ]], columns=RISK_FEATURES)
            delay_features = pd.DataFrame([[
                distance_km, traffic_density, rainfall_mm, condition,
                historical_minutes, incident_count,
            ]], columns=DELAY_FEATURES)
            probability = float(self.risk_model.predict_proba(risk_features)[0][1])
            delay = max(0.0, float(self.delay_model.predict(delay_features)[0]))
            return Advisory(probability=probability, band=self._band(probability), delay_minutes=delay)
        except Exception as exc:
            self.status = "DEGRADED"
            self.detail = f"ML advisory inference failed: {type(exc).__name__}"
            return None


model_adapter = ModelAdapter()
