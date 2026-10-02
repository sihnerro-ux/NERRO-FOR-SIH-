"""Train versioned NER-wide prototype models without replacing active models."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.training.ner_pipeline import train_versioned_models


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="ner-synthetic-v1")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "data" / "generated" / "ner_operational_training.csv",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "trained_models" / "versions",
    )
    parser.add_argument("--seed", type=int, default=26002)
    args = parser.parse_args()

    output_dir = args.output_root / args.version
    report = train_versioned_models(
        args.dataset, output_dir, version=args.version, seed=args.seed
    )
    print(f"Version: {report['version']}")
    print(f"Status: {report['status']}")
    print(f"Validation: {report['validation']['test_rows']} rows on "
          f"{len(report['validation']['test_corridors'])} unseen corridors")
    risk = report["risk_classifier"]
    delay = report["delay_regressor"]
    print(f"Risk: {risk['selected_model']} | macro-F1={risk['holdout']['macro_f1']} "
          f"| accuracy={risk['holdout']['accuracy']}")
    print(f"Delay: {delay['selected_model']} | RMSE={delay['holdout']['rmse']} "
          f"| MAE={delay['holdout']['mae']} | R2={delay['holdout']['r2']}")
    print(f"Saved without activating: {output_dir.resolve()}")


if __name__ == "__main__":
    main()

