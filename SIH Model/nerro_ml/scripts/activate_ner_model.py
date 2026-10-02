"""Activate a validated model version through a reversible pointer file."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_ROOT = PROJECT_ROOT / "trained_models"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    args = parser.parse_args()

    version_dir = (MODEL_ROOT / "versions" / args.version).resolve()
    versions_root = (MODEL_ROOT / "versions").resolve()
    if versions_root not in version_dir.parents:
        raise SystemExit("Invalid model version path.")
    report_path = version_dir / "training_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "VALIDATED_PROTOTYPE":
        raise SystemExit("Refusing activation: model did not pass its quality gates.")
    for key in ("risk_classifier", "delay_regressor"):
        artifact = report["artifacts"][key]
        artifact_path = version_dir / artifact["file"]
        if sha256(artifact_path) != artifact["sha256"]:
            raise SystemExit(f"Refusing activation: checksum mismatch for {key}.")

    pointer_path = MODEL_ROOT / "active_model.json"
    previous = None
    if pointer_path.exists():
        previous = json.loads(pointer_path.read_text(encoding="utf-8")).get("version")
    pointer = {
        "version": args.version,
        "previous_version": previous,
        "activated_at": datetime.now(UTC).isoformat(),
        "data_mode": report.get("data_mode", "UNKNOWN"),
        "operational_use": False,
        "report_sha256": sha256(report_path),
    }
    pointer_path.write_text(json.dumps(pointer, indent=2), encoding="utf-8")
    print(f"Activated advisory model: {args.version}")
    print(f"Pointer: {pointer_path.resolve()}")
    print("Safety: synthetic model remains advisory-only and cannot block roads.")


if __name__ == "__main__":
    main()
