# NER Model Training and Validation

This pipeline trains the risk classifier and delay regressor using the
NER-wide synthetic dataset. It does **not** overwrite the model currently used
by the application.

## Run

From `SIH Model/nerro_ml`:

```powershell
python -m scripts.train_ner --version ner-synthetic-v1
```

The version is written to:

```text
trained_models/versions/ner-synthetic-v1/
  risk_classifier.pkl
  delay_regressor.pkl
  training_report.json
```

## Validation design

- At least one complete corridor from every NER state is held out, preventing
  observations from the same corridor appearing in both training and
  validation while guaranteeing eight-state validation coverage.
- Candidate models are ranked on the unseen corridors.
- Risk results include macro-F1 and accuracy.
- Delay results include RMSE, MAE and R-squared.
- The report includes separate metrics by state and held-out corridor.
- The selected models are refitted on the full dataset after evaluation.
- SHA-256 checksums make the saved artifacts traceable.

## Safety boundary

An artifact marked `VALIDATED_PROTOTYPE` passed synthetic-data quality gates;
it is not validated for operational deployment. Promotion into the live backend
is a separate, explicit step. Real historical observations and field validation
are required before production use.

For the prototype, activate a version with:

```powershell
python -m scripts.activate_ner_model ner-synthetic-v2-all-state
```

This changes only `trained_models/active_model.json`; it does not overwrite any
model artifact. Restart the backend after changing the active pointer. The model
remains advisory-only: verified field/control-room reports alone can close roads.
