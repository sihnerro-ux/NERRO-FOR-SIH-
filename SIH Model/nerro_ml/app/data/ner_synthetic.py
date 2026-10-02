"""Reproducible NER-wide synthetic operational and ML training data.

This dataset is explicitly synthetic.  It is designed for prototype integration,
schema validation and model-pipeline testing, not for operational claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class StateProfile:
    centre_lat: float
    centre_lon: float
    rainfall_multiplier: float
    elevation_range: tuple[float, float]
    slope_range: tuple[float, float]
    incident_rate: float
    traffic_alpha: float
    traffic_beta: float
    road_condition_probabilities: tuple[float, float, float]
    susceptibility: float


STATE_PROFILES: dict[str, StateProfile] = {
    "Assam": StateProfile(26.20, 92.94, 1.10, (20, 650), (0, 16), 1.3, 2.8, 4.5, (0.42, 0.40, 0.18), 0.05),
    "Arunachal Pradesh": StateProfile(27.55, 93.85, 1.25, (150, 4500), (7, 43), 2.0, 1.7, 5.5, (0.25, 0.43, 0.32), 0.45),
    "Manipur": StateProfile(24.75, 93.90, 1.05, (200, 2600), (4, 34), 1.6, 2.2, 5.0, (0.32, 0.43, 0.25), 0.25),
    "Meghalaya": StateProfile(25.47, 91.37, 1.50, (40, 2000), (5, 38), 2.1, 2.0, 5.2, (0.28, 0.44, 0.28), 0.50),
    "Mizoram": StateProfile(23.32, 92.84, 1.30, (80, 1900), (8, 40), 1.9, 1.8, 5.5, (0.25, 0.43, 0.32), 0.45),
    "Nagaland": StateProfile(26.16, 94.56, 1.18, (100, 3000), (6, 39), 1.8, 2.0, 5.0, (0.27, 0.45, 0.28), 0.38),
    "Sikkim": StateProfile(27.53, 88.51, 1.35, (280, 5200), (10, 45), 2.2, 1.8, 5.4, (0.30, 0.42, 0.28), 0.55),
    "Tripura": StateProfile(23.84, 91.28, 1.12, (10, 950), (1, 23), 1.2, 2.4, 4.8, (0.38, 0.43, 0.19), 0.12),
}


# state, corridor id, origin, destination, nominal distance, road class
NER_CORRIDORS = [
    ("Assam", "AS-NH27-GHY-JOR", "Guwahati", "Jorhat", 305, "NATIONAL_HIGHWAY"),
    ("Assam", "AS-NH27-JOR-DIB", "Jorhat", "Dibrugarh", 140, "NATIONAL_HIGHWAY"),
    ("Assam", "AS-NH15-GHY-TEZ", "Guwahati", "Tezpur", 180, "NATIONAL_HIGHWAY"),
    ("Assam", "AS-NH27-GHY-SIL", "Guwahati", "Silchar", 340, "NATIONAL_HIGHWAY"),
    ("Assam", "AS-SH-DIB-TIN", "Dibrugarh", "Tinsukia", 50, "STATE_HIGHWAY"),
    ("Arunachal Pradesh", "AR-NH13-ITA-PAS", "Itanagar", "Pasighat", 265, "NATIONAL_HIGHWAY"),
    ("Arunachal Pradesh", "AR-NH13-BOM-TAW", "Bomdila", "Tawang", 175, "NATIONAL_HIGHWAY"),
    ("Arunachal Pradesh", "AR-SH-ITA-ZIR", "Itanagar", "Ziro", 110, "STATE_HIGHWAY"),
    ("Arunachal Pradesh", "AR-FR-TEZ-TAW", "Tezpur", "Tawang", 325, "FRONTIER_ROAD"),
    ("Meghalaya", "ML-NH06-GHY-SHL", "Guwahati", "Shillong", 100, "NATIONAL_HIGHWAY"),
    ("Meghalaya", "ML-SH-SHL-SOH", "Shillong", "Sohra", 55, "STATE_HIGHWAY"),
    ("Meghalaya", "ML-NH127B-SHL-TUR", "Shillong", "Tura", 310, "NATIONAL_HIGHWAY"),
    ("Meghalaya", "ML-DR-TUR-BAG", "Tura", "Baghmara", 115, "DISTRICT_ROAD"),
    ("Manipur", "MN-NH02-IMP-MOR", "Imphal", "Moreh", 110, "NATIONAL_HIGHWAY"),
    ("Manipur", "MN-NH37-IMP-JIR", "Imphal", "Jiribam", 220, "NATIONAL_HIGHWAY"),
    ("Manipur", "MN-NH02-IMP-SEN", "Imphal", "Senapati", 65, "NATIONAL_HIGHWAY"),
    ("Manipur", "MN-SH-IMP-CCP", "Imphal", "Churachandpur", 63, "STATE_HIGHWAY"),
    ("Mizoram", "MZ-NH306-SIL-AIZ", "Silchar", "Aizawl", 170, "NATIONAL_HIGHWAY"),
    ("Mizoram", "MZ-NH54-AIZ-LUN", "Aizawl", "Lunglei", 170, "NATIONAL_HIGHWAY"),
    ("Mizoram", "MZ-SH-LUN-SIA", "Lunglei", "Siaha", 165, "STATE_HIGHWAY"),
    ("Nagaland", "NL-NH29-DIM-KOH", "Dimapur", "Kohima", 74, "NATIONAL_HIGHWAY"),
    ("Nagaland", "NL-NH02-KOH-MOK", "Kohima", "Mokokchung", 150, "NATIONAL_HIGHWAY"),
    ("Nagaland", "NL-SH-MOK-MON", "Mokokchung", "Mon", 180, "STATE_HIGHWAY"),
    ("Sikkim", "SK-NH10-SIL-GAN", "Siliguri", "Gangtok", 115, "NATIONAL_HIGHWAY"),
    ("Sikkim", "SK-NH710-GAN-NAM", "Gangtok", "Namchi", 80, "NATIONAL_HIGHWAY"),
    ("Sikkim", "SK-SH-GAN-MAN", "Gangtok", "Mangan", 65, "STATE_HIGHWAY"),
    ("Tripura", "TR-NH08-AGA-DHA", "Agartala", "Dharmanagar", 185, "NATIONAL_HIGHWAY"),
    ("Tripura", "TR-NH08-AGA-UDA", "Agartala", "Udaipur", 55, "NATIONAL_HIGHWAY"),
    ("Tripura", "TR-SH-UDA-SAB", "Udaipur", "Sabroom", 75, "STATE_HIGHWAY"),
]


def _weather_severity(rainfall: np.ndarray) -> np.ndarray:
    return np.select(
        [rainfall >= 100, rainfall >= 75, rainfall >= 45, rainfall >= 20],
        [5, 4, 3, 2],
        default=1,
    ).astype(int)


def generate_ner_training_dataset(n_samples: int = 16000, seed: int = 26002) -> pd.DataFrame:
    """Generate balanced, state-aware synthetic observations for all eight NER states."""
    if n_samples < len(STATE_PROFILES) * 100:
        raise ValueError("Use at least 100 observations per NER state")

    rng = np.random.default_rng(seed)
    state_names = list(STATE_PROFILES)
    selected_states = np.resize(np.array(state_names), n_samples)
    rng.shuffle(selected_states)
    start = datetime(2021, 1, 1, tzinfo=UTC)
    records: list[dict] = []

    corridors_by_state = {
        state: [corridor for corridor in NER_CORRIDORS if corridor[0] == state]
        for state in state_names
    }

    for index, state in enumerate(selected_states):
        profile = STATE_PROFILES[str(state)]
        corridor = corridors_by_state[str(state)][int(rng.integers(0, len(corridors_by_state[str(state)])))]
        _, corridor_id, origin, destination, nominal_distance, road_class = corridor
        observed_at = start + timedelta(hours=int(rng.integers(0, 5 * 365 * 24)))
        month = observed_at.month
        is_monsoon = int(month in {5, 6, 7, 8, 9, 10})

        rainfall = float(rng.gamma(2.7, 17.0) * profile.rainfall_multiplier * (rng.uniform(1.35, 2.15) if is_monsoon else 1.0))
        rainfall = min(rainfall, 420.0)
        elevation = float(rng.uniform(*profile.elevation_range))
        slope = float(rng.uniform(*profile.slope_range))
        road_condition = int(rng.choice([1, 2, 3], p=profile.road_condition_probabilities))
        traffic_density = float(rng.beta(profile.traffic_alpha, profile.traffic_beta))
        past_incidents = int(rng.poisson(profile.incident_rate + rainfall / 140))
        active_incidents = int(rng.poisson(0.18 + rainfall / 170 + past_incidents * 0.08))
        verified_incidents = int(rng.binomial(active_incidents, 0.68)) if active_incidents else 0
        weather_severity = int(_weather_severity(np.array([rainfall]))[0])
        distance = float(nominal_distance * rng.uniform(0.18, 1.05))

        road_speed = {"NATIONAL_HIGHWAY": 45, "STATE_HIGHWAY": 34, "DISTRICT_ROAD": 25, "FRONTIER_ROAD": 22}[road_class]
        historical_average = distance / road_speed * 60
        slowdown = max(0.17, 1 - 0.34 * traffic_density - 0.0022 * rainfall - 0.11 * (road_condition - 1) - 0.004 * slope)
        actual_travel = historical_average / slowdown + active_incidents * rng.uniform(9, 38) + rng.normal(0, 5)
        delay = float(np.clip(actual_travel - historical_average, 0, 1500))

        observable_risk_logit = (
            0.012 * rainfall + 0.045 * slope + 0.00045 * elevation
            + 0.31 * past_incidents + 0.75 * is_monsoon + 0.28 * weather_severity
            + 0.28 * (road_condition - 1) + 0.45 * traffic_density
            + 0.38 * verified_incidents + profile.susceptibility - 5.25
        )
        # Recorded features should explain most of the target while retaining
        # some uncertainty for unobserved local conditions.
        risk_logit = 1.35 * observable_risk_logit + rng.normal(0, 0.45)
        disruption_probability = 1 / (1 + np.exp(-risk_logit))
        disrupted = int(rng.random() < disruption_probability)
        confirmed_closure = int(disrupted and verified_incidents > 0 and disruption_probability > 0.78)

        records.append({
            "record_id": f"NER-SYN-{index + 1:06d}",
            "observed_at": observed_at.isoformat(),
            "state": str(state),
            "corridor_id": corridor_id,
            "origin": origin,
            "destination": destination,
            "road_class": road_class,
            "latitude": round(float(np.clip(profile.centre_lat + rng.normal(0, 0.42), 21.0, 30.5)), 6),
            "longitude": round(float(np.clip(profile.centre_lon + rng.normal(0, 0.55), 87.5, 98.5)), 6),
            "rainfall_mm": round(rainfall, 1),
            "slope_deg": round(slope, 2),
            "elevation_m": round(elevation, 1),
            "past_incident_count": past_incidents,
            "is_monsoon": is_monsoon,
            "weather_severity": weather_severity,
            "road_condition": road_condition,
            "traffic_density": round(traffic_density, 3),
            "distance_km": round(distance, 1),
            "historical_avg_minutes": round(historical_average, 1),
            "active_incidents": active_incidents,
            "verified_incidents": verified_incidents,
            "actual_travel_minutes": round(max(5, actual_travel), 1),
            "delay_minutes": round(delay, 1),
            "disrupted": disrupted,
            "confirmed_closure": confirmed_closure,
            "weather_source": "SYNTHETIC_OPEN_METEO_LIKE",
            "incident_source": "SYNTHETIC_FIELD_REPORTS",
            "data_mode": "SIMULATED",
        })

    return pd.DataFrame.from_records(records)


def write_ner_dataset(output_dir: Path, n_samples: int = 16000, seed: int = 26002) -> dict:
    """Write unified, risk and delay CSVs plus a provenance manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset = generate_ner_training_dataset(n_samples=n_samples, seed=seed)
    risk_columns = [
        "record_id", "observed_at", "state", "corridor_id", "origin", "destination",
        "latitude", "longitude", "road_class", "rainfall_mm", "slope_deg", "elevation_m",
        "past_incident_count", "is_monsoon", "weather_severity", "road_condition",
        "traffic_density", "verified_incidents", "disrupted", "confirmed_closure", "data_mode",
    ]
    delay_columns = [
        "record_id", "observed_at", "state", "corridor_id", "origin", "destination",
        "latitude", "longitude", "road_class", "distance_km", "traffic_density", "rainfall_mm",
        "road_condition", "historical_avg_minutes", "active_incidents", "actual_travel_minutes",
        "delay_minutes", "data_mode",
    ]
    unified_path = output_dir / "ner_operational_training.csv"
    risk_path = output_dir / "ner_risk_training.csv"
    delay_path = output_dir / "ner_delay_training.csv"
    dataset.to_csv(unified_path, index=False)
    dataset[risk_columns].to_csv(risk_path, index=False)
    dataset[delay_columns].to_csv(delay_path, index=False)

    manifest = {
        "problem_statement_id": 26002,
        "generator_version": "ner-synthetic-v2",
        "generated_at": datetime.now(UTC).isoformat(),
        "data_mode": "SIMULATED",
        "operational_use": False,
        "seed": seed,
        "row_count": len(dataset),
        "state_counts": dataset["state"].value_counts().sort_index().to_dict(),
        "corridor_count": int(dataset["corridor_id"].nunique()),
        "disrupted_ratio": round(float(dataset["disrupted"].mean()), 4),
        "confirmed_closure_ratio": round(float(dataset["confirmed_closure"].mean()), 4),
        "mean_delay_minutes": round(float(dataset["delay_minutes"].mean()), 2),
        "files": [unified_path.name, risk_path.name, delay_path.name],
        "warning": "Synthetic prototype data. Replace with validated historical NER observations before operational use.",
    }
    (output_dir / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
