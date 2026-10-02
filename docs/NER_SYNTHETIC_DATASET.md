# NER Synthetic Dataset Contract

This dataset supports prototype development for SIH Problem Statement 26002. It is explicitly simulated and must not be represented as observed government data.

## Coverage

- Eight North Eastern states
- 29 representative interstate, national, state, district and frontier-road corridors
- 16,000 balanced observations by default
- Five years of synthetic timestamps
- Weather, terrain, road condition, traffic, field-incident and travel-delay signals

## Generated files

`ner_operational_training.csv` is the unified source. `ner_risk_training.csv` and `ner_delay_training.csv` are model-specific projections. `dataset_manifest.json` records provenance, generation seed, state counts and label statistics.

## Risk model columns

The canonical model inputs remain `rainfall_mm`, `slope_deg`, `elevation_m`, `past_incident_count`, `is_monsoon`, `weather_severity`, `road_condition` and `traffic_density`. The target is `disrupted`.

## Delay model columns

The canonical model inputs remain `distance_km`, `traffic_density`, `rainfall_mm`, `road_condition`, `historical_avg_minutes` and `active_incidents`. The target is `delay_minutes`.

## Metadata and safety columns

State, corridor, coordinates, road class and timestamps make geographic and temporal evaluation possible. `verified_incidents` and `confirmed_closure` are retained for workflow evaluation, but a production closure decision must still come from verified authority data rather than an ML prediction.

## Generate

From `SIH Model/nerro_ml`:

```powershell
python -m scripts.generate_ner_dataset
```

Generation is deterministic for a given seed. The next phase will split data by time and corridor, train candidate models, measure state-wise performance and version the resulting artefacts.
