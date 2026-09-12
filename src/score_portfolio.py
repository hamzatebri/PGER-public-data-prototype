from __future__ import annotations

import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "public_procurement_exposure_2022_2024.csv"
OUTPUT = ROOT / "data" / "processed" / "public_procurement_exposure_scored.csv"
PROFILE = ROOT / "data" / "processed" / "scoring_definition.txt"


def percentile(series: pd.Series) -> pd.Series:
    return series.rank(method="average", pct=True).fillna(0.0)


def main() -> int:
    frame = pd.read_csv(INPUT, parse_dates=["publication_date"], dayfirst=True)
    frame["contract_value_eur"] = pd.to_numeric(frame["contract_value_eur"], errors="coerce").fillna(0.0)

    frame["value_percentile"] = percentile(frame["contract_value_eur"])
    frame["authority_awardee_share_percentile"] = percentile(frame["authority_awardee_value_share"])
    frame["authority_awardee_notice_share_percentile"] = percentile(frame["authority_awardee_notice_share"])
    frame["review_priority_score"] = (
        0.50 * frame["value_percentile"]
        + 0.30 * frame["authority_awardee_share_percentile"]
        + 0.20 * frame["authority_awardee_notice_share_percentile"]
    ).round(6)
    frame["review_priority_band"] = pd.cut(
        frame["review_priority_score"],
        bins=[-0.01, 0.50, 0.80, 1.00],
        labels=["Routine review", "Focused review", "Priority review"],
    )
    frame["score_definition"] = "0.50 contract-value percentile + 0.30 authority-awardee awarded-value-share percentile + 0.20 authority-awardee notice-share percentile"
    frame.to_csv(OUTPUT, index=False, encoding="utf-8")

    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    PROFILE.write_text(
        "\n".join(
            [
                "PGER review-priority score definition",
                f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
                "Purpose: order observed public procurement exposures for earlier review.",
                "Components: 50% contract-value percentile, 30% authority-awardee awarded-value-share percentile, 20% authority-awardee notice-share percentile.",
                "Denominators: the value share is the awardee entity's awarded value divided by the observed authority's awarded value; the notice share is the entity's notice count divided by the authority's notice count.",
                "Interpretation: a higher score indicates a higher review priority within this declared portfolio.",
                "Use: the score orders records inside this public portfolio; a business decision also needs current contract and operational information.",
                f"Output SHA-256: {digest}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print("Built", OUTPUT)
    print("Rows:", len(frame), "SHA256:", digest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
