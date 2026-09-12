"""Test how two transparent design choices affect the PGER outputs.

The structural score and the event-context flag remain separate. This module
does not optimise either one. It applies a small set of deliberately different
score weights and event-window lengths so the thesis can show how much the
reported ordering and match count depend on those choices.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO = ROOT / "data" / "processed" / "public_procurement_exposure_scored.csv"
EVENTS = ROOT / "data" / "processed" / "external_events.csv"
OUT_DIR = ROOT / "data" / "processed"

SCORE_SCENARIOS = {
    "Baseline 50/30/20": (0.50, 0.30, 0.20),
    "Equal weights": (1 / 3, 1 / 3, 1 / 3),
    "Value-heavy": (0.70, 0.20, 0.10),
    "Value-share-heavy": (0.30, 0.50, 0.20),
    "Notice-share-heavy": (0.30, 0.20, 0.50),
    "No value component": (0.00, 0.60, 0.40),
    "No value-share component": (5 / 7, 0.00, 2 / 7),
    "No notice-share component": (0.625, 0.375, 0.00),
}

GEOGRAPHY_SCOPE = {
    "EVT-2022-001": "national",
    "EVT-2023-001": "international_only",
    "EVT-2024-001": "international_only",
    "EVT-2024-002": "international_only",
}

CATEGORY_RULES = {
    "EVT-2022-001": {
        "sector_groups": {"Petroleum, fuel, electricity and other energy sources"},
        "cpv_prefixes": set(),
    },
    "EVT-2023-001": {
        "sector_groups": {"Transport equipment and auxiliary products"},
        "cpv_prefixes": {"34", "60", "61", "62", "63", "64"},
    },
    "EVT-2024-001": {
        "sector_groups": {"Transport equipment and auxiliary products"},
        "cpv_prefixes": {"34", "60", "61", "62", "63", "64"},
    },
    "EVT-2024-002": {
        "sector_groups": {"Transport equipment and auxiliary products"},
        "cpv_prefixes": {"34", "60", "61", "62", "63", "64"},
    },
}


def score_sensitivity(frame: pd.DataFrame) -> pd.DataFrame:
    """Compare fixed alternative weights with the submitted score."""
    columns = [
        "value_percentile",
        "authority_awardee_share_percentile",
        "authority_awardee_notice_share_percentile",
    ]
    baseline = frame["review_priority_score"].astype(float)
    baseline_top_10 = set(frame.nlargest(10, "review_priority_score")["exposure_id"])
    baseline_top_100 = set(frame.nlargest(100, "review_priority_score")["exposure_id"])

    rows = []
    for label, weights in SCORE_SCENARIOS.items():
        score = sum(weight * frame[column].astype(float) for weight, column in zip(weights, columns)).round(6)
        top_10 = set(frame.assign(_score=score).nlargest(10, "_score")["exposure_id"])
        top_100 = set(frame.assign(_score=score).nlargest(100, "_score")["exposure_id"])
        rows.append(
            {
                "scenario": label,
                "value_weight": round(weights[0], 6),
                "authority_awardee_value_share_weight": round(weights[1], 6),
                "authority_awardee_notice_share_weight": round(weights[2], 6),
                "spearman_with_baseline": round(
                    score.rank(method="average").corr(baseline.rank(method="average")), 6
                ),
                "top_10_overlap": len(top_10 & baseline_top_10),
                "top_10_overlap_share": round(len(top_10 & baseline_top_10) / 10, 6),
                "top_100_overlap": len(top_100 & baseline_top_100),
                "top_100_overlap_share": round(len(top_100 & baseline_top_100) / 100, 6),
                "priority_review_notices": int((score > 0.80).sum()),
            }
        )
    return pd.DataFrame(rows)


def _category_mask(frame: pd.DataFrame, event_id: str) -> pd.Series:
    rule = CATEGORY_RULES[event_id]
    cpv2 = frame["cpv_code"].astype(str).str.zfill(8).str[:2]
    return frame["sector_group"].isin(rule["sector_groups"]) | cpv2.isin(rule["cpv_prefixes"])


def _geography_mask(frame: pd.DataFrame, event_id: str) -> pd.Series:
    if GEOGRAPHY_SCOPE[event_id] == "national":
        return pd.Series(True, index=frame.index)
    return frame["contracting_authority_region"].fillna("").str.strip().eq("Internacional")


def event_window_sensitivity(frame: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Vary only the days retained after the latest official campaign record."""
    frame = frame.copy()
    frame["publication_date"] = pd.to_datetime(frame["publication_date"])
    events = events.copy()
    events["published_date"] = pd.to_datetime(events["published_date"])

    rows = []
    for days in (90, 180, 365):
        all_matches: set[str] = set()
        campaign_counts: dict[str, int] = {}
        for campaign_id, campaign in events.groupby("event_campaign_id", sort=True):
            first_event = campaign.sort_values("published_date").iloc[0]
            event_id = first_event["event_id"]
            start = campaign["published_date"].min()
            end = campaign["published_date"].max() + pd.Timedelta(days=days)
            mask = (
                _geography_mask(frame, event_id)
                & _category_mask(frame, event_id)
                & frame["publication_date"].between(start, end)
            )
            ids = set(frame.loc[mask, "exposure_id"])
            campaign_counts[campaign_id] = len(ids)
            all_matches.update(ids)

        rows.append(
            {
                "window_days_after_latest_official_record": days,
                "eu_sanctions_matches": campaign_counts.get("CAMPAIGN-EU-SANCTIONS-2022", 0),
                "panama_canal_matches": campaign_counts.get("CAMPAIGN-PANAMA-2023", 0),
                "red_sea_matches": campaign_counts.get("CAMPAIGN-RED-SEA-2024", 0),
                "union_matched_exposures": len(all_matches),
                "union_matched_share": round(len(all_matches) / len(frame), 6),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    frame = pd.read_csv(PORTFOLIO)
    events = pd.read_csv(EVENTS)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    score = score_sensitivity(frame)
    windows = event_window_sensitivity(frame, events)
    score.to_csv(OUT_DIR / "score_sensitivity.csv", index=False)
    windows.to_csv(OUT_DIR / "event_window_sensitivity.csv", index=False)

    print("Score-weight sensitivity")
    print(score.to_string(index=False))
    print("\nEvent-window sensitivity")
    print(windows.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
