from app.data.ner_synthetic import generate_ner_training_dataset
from app.training.ner_pipeline import corridor_holdout_indices


def test_corridor_holdout_has_no_route_leakage() -> None:
    dataset = generate_ner_training_dataset(n_samples=800, seed=26002)
    train_idx, test_idx = corridor_holdout_indices(dataset, seed=26002)

    train_corridors = set(dataset.iloc[train_idx]["corridor_id"])
    test_corridors = set(dataset.iloc[test_idx]["corridor_id"])

    assert train_corridors
    assert test_corridors
    assert train_corridors.isdisjoint(test_corridors)
    assert len(train_idx) + len(test_idx) == len(dataset)
    assert set(dataset.iloc[test_idx]["state"]) == set(dataset["state"])
