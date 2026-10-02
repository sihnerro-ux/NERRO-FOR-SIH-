"""Generate the reproducible NER-wide prototype datasets.

Usage:
    python -m scripts.generate_ner_dataset
    python -m scripts.generate_ner_dataset --samples 24000 --seed 26002
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.data.ner_synthetic import write_ner_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate explicitly synthetic NER logistics data")
    parser.add_argument("--samples", type=int, default=16000)
    parser.add_argument("--seed", type=int, default=26002)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "generated")
    args = parser.parse_args()
    manifest = write_ner_dataset(args.output, n_samples=args.samples, seed=args.seed)
    print(f"Generated {manifest['row_count']} rows across {len(manifest['state_counts'])} states and {manifest['corridor_count']} corridors.")
    print(f"Disrupted ratio: {manifest['disrupted_ratio']:.2%}")
    print(f"Mean delay: {manifest['mean_delay_minutes']:.2f} minutes")
    print(f"Output: {args.output.resolve()}")


if __name__ == "__main__":
    main()
