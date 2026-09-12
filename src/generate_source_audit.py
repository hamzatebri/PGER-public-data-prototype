"""Create a compact, reproducible audit of the files used in the submission."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "source_audit.json"
FILES = {
    "data/raw/boe_procurement/licitaciones_contrataciones_BOE_2014_2024.csv": {"sep": ","},
    "data/raw/ebae_sample/SampleFile.EBAE20T422T2_01.csv": {"sep": ";"},
    "data/raw/ebae_sample/User_guide_BELab.EBAE20T422T2_01_en.pdf": {},
    "data/raw/external_evidence/EVT-2022-001_council_eu_sanctions_extract.txt": {},
    "data/raw/external_evidence/EVT-2023-001_panama_canal_advisory.pdf": {},
    "data/raw/external_evidence/EVT-2024-001_imo_red_sea_statement.html": {},
    "data/raw/external_evidence/EVT-2024-002_imo_red_sea_resolution.html": {},
    "data/processed/public_procurement_exposure_scored.csv": {"sep": ","},
    "data/processed/external_events.csv": {"sep": ","},
    "data/processed/event_portfolio_matches.csv": {"sep": ","},
    "data/processed/public_procurement_exposure_scored_with_event_context.csv": {"sep": ","},
    "data/processed/score_sensitivity.csv": {"sep": ","},
    "data/processed/event_window_sensitivity.csv": {"sep": ","},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_file(relative_path: str, options: dict[str, str]) -> dict[str, object]:
    path = ROOT / relative_path
    if not path.exists():
        raise FileNotFoundError(relative_path)
    record: dict[str, object] = {
        "file": relative_path,
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    }
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path, sep=options["sep"], dtype=str, low_memory=False)
        record["content"] = {
            "format": "csv",
            "delimiter": options["sep"],
            "rows": int(len(frame)),
            "columns": frame.columns.tolist(),
            "missing_by_column": {key: int(value) for key, value in frame.isna().sum().items()},
            "duplicate_full_rows": int(frame.duplicated().sum()),
        }
    else:
        record["content"] = {"format": path.suffix.lower().lstrip(".")}
    return record


def main() -> None:
    audit = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Submission source and processed-output identity check",
        "files": [inspect_file(path, options) for path, options in FILES.items()],
    }
    OUTPUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(audit['files'])} verified files")


if __name__ == "__main__":
    main()
