from app.data.ner_synthetic import STATE_PROFILES, generate_ner_training_dataset
from app.data.preprocessor import DELAY_FEATURES, RISK_FEATURES


def test_ner_dataset_is_balanced_complete_and_model_compatible() -> None:
    dataset = generate_ner_training_dataset(n_samples=800, seed=26002)

    assert len(dataset) == 800
    assert dataset.isna().sum().sum() == 0
    assert set(dataset["state"]) == set(STATE_PROFILES)
    assert set(dataset["state"].value_counts()) == {100}
    assert set(RISK_FEATURES).issubset(dataset.columns)
    assert set(DELAY_FEATURES).issubset(dataset.columns)
    assert set(dataset["disrupted"]).issubset({0, 1})
    assert (dataset["data_mode"] == "SIMULATED").all()
    assert dataset["latitude"].between(21.0, 30.5).all()
    assert dataset["longitude"].between(87.5, 98.5).all()


def test_ner_dataset_is_reproducible_for_the_same_seed() -> None:
    first = generate_ner_training_dataset(n_samples=800, seed=42)
    second = generate_ner_training_dataset(n_samples=800, seed=42)

    assert first.equals(second)
