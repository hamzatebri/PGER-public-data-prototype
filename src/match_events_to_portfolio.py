"""Candidate event-context matching layer.

Links the frozen official external-event registry (`external_events.csv`) to
the frozen BOE procurement portfolio (`public_procurement_exposure_scored.csv`)
using only geography, category, and time rules fixed in
`docs/EVENT_MATCHING_CROSSWALK.md` before this module was run. It never reads
or matches on awardee identity, and it never modifies `review_priority_score`.

A notice becomes a candidate for an event-source check only when its
publication date falls within the pre-specified event window and it satisfies
the relevant category and geographic-scope rule. The flag records a
time-aligned category and scope proxy for human review. It does not establish
the awardee's country, transport route or operational exposure.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCORED = ROOT / "data" / "processed" / "public_procurement_exposure_scored.csv"
EVENTS = ROOT / "data" / "processed" / "external_events.csv"
MATCHES_OUT = ROOT / "data" / "processed" / "event_portfolio_matches.csv"
WIDE_OUT = ROOT / "data" / "processed" / "public_procurement_exposure_scored_with_event_context.csv"
MANIFEST_OUT = ROOT / "docs" / "EVENT_MATCHING_RELEASE_MANIFEST.json"

CROSSWALK_VERSION = "v1-international-scope-only-temporal-window"

# Declared release rules. Changes require regenerated results and a new manifest.
GEOGRAPHY_SCOPE = {
    "EVT-2022-001": "national",
    "EVT-2023-001": "international_only",
    "EVT-2024-001": "international_only",
    "EVT-2024-002": "international_only",
}

CATEGORY_RULES = {
    "EVT-2022-001": {
        "rule": "trade_restriction_sectoral_scope",
        "sector_groups": {"Petroleum, fuel, electricity and other energy sources"},
        "cpv_prefixes": set(),
    },
    "EVT-2023-001": {
        "rule": "logistics_transport_category",
        "sector_groups": {"Transport equipment and auxiliary products"},
        "cpv_prefixes": {"34", "60", "61", "62", "63", "64"},
    },
    "EVT-2024-001": {
        "rule": "logistics_transport_category",
        "sector_groups": {"Transport equipment and auxiliary products"},
        "cpv_prefixes": {"34", "60", "61", "62", "63", "64"},
    },
    "EVT-2024-002": {
        "rule": "logistics_transport_category",
        "sector_groups": {"Transport equipment and auxiliary products"},
        "cpv_prefixes": {"34", "60", "61", "62", "63", "64"},
    },
}


@dataclass
class EventRecord:
    event_id: str
    published_date: str
    source_name: str
    source_url: str
    geography: str
    affected_category: str
    evidence_summary: str
    event_campaign_id: str
    campaign_start_date: str
    campaign_end_date: str
    campaign_validity_source_url: str


def load_events() -> list[EventRecord]:
    with EVENTS.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [
        EventRecord(
            event_id=row["event_id"],
            published_date=row["published_date"],
            source_name=row["source_name"],
            source_url=row["source_url"],
            geography=row["geography"],
            affected_category=row["affected_category"],
            evidence_summary=row["evidence_summary"],
            event_campaign_id=row["event_campaign_id"],
            campaign_start_date=row["campaign_start_date"],
            campaign_end_date=row["campaign_end_date"],
            campaign_validity_source_url=row["campaign_validity_source_url"],
        )
        for row in rows
    ]


def load_scored() -> list[dict[str, str]]:
    with SCORED.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def geography_matches(region: str, scope: str) -> bool:
    """Exact-equality only. No substring/partial matching against combined
    multi-region strings (e.g. "Castilla y Leon, Cataluna, Andalucia,
    Internacional" does NOT count as international scope)."""
    trimmed = (region or "").strip()
    if scope == "national":
        return True
    if scope == "international_only":
        return trimmed == "Internacional"
    return False


def category_matches(sector_group: str, cpv_code: str, rule: dict) -> bool:
    cpv2 = (cpv_code or "").zfill(8)[:2]
    return sector_group in rule["sector_groups"] or cpv2 in rule["cpv_prefixes"]


def temporal_matches(record_date: str, campaign_start: str, campaign_end: str) -> bool:
    try:
        d = datetime.strptime(record_date, "%Y-%m-%d").date()
        start = datetime.strptime(campaign_start, "%Y-%m-%d").date()
        end = datetime.strptime(campaign_end, "%Y-%m-%d").date()
    except ValueError:
        return False
    return start <= d <= end


def build_matches(scored_rows: list[dict[str, str]], events: list[EventRecord]) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    for row in scored_rows:
        for event in events:
            scope = GEOGRAPHY_SCOPE[event.event_id]
            rule = CATEGORY_RULES[event.event_id]
            if not geography_matches(row["contracting_authority_region"], scope):
                continue
            if not category_matches(row["sector_group"], row["cpv_code"], rule):
                continue
            if not temporal_matches(row["publication_date"], event.campaign_start_date, event.campaign_end_date):
                continue
            matches.append(
                {
                    "event_id": event.event_id,
                    "event_campaign_id": event.event_campaign_id,
                    "exposure_id": row["exposure_id"],
                    "contract_id": row["contract_id"],
                    "matching_rule": rule["rule"],
                    "geography_basis": scope,
                    "category_proxy": event.affected_category,
                    "source_url": event.source_url,
                    "published_date": event.published_date,
                    "evidence_summary": event.evidence_summary,
                }
            )
    return matches


def summarize_onto_scored(scored_rows: list[dict[str, str]], matches: list[dict[str, str]]) -> list[dict[str, str]]:
    by_exposure: dict[str, list[dict[str, str]]] = {}
    for match in matches:
        by_exposure.setdefault(match["exposure_id"], []).append(match)

    wide_rows: list[dict[str, str]] = []
    for row in scored_rows:
        out = dict(row)
        exposure_matches = by_exposure.get(row["exposure_id"], [])
        campaign_ids = sorted({m["event_campaign_id"] for m in exposure_matches})
        if exposure_matches:
            out["candidate_event_context_flag"] = "1"
            out["candidate_campaign_count"] = str(len(campaign_ids))
            out["candidate_campaign_ids"] = ";".join(campaign_ids)
            out["candidate_event_category_proxy"] = ";".join(sorted({m["category_proxy"] for m in exposure_matches}))
            out["candidate_event_matching_rule"] = ";".join(sorted({m["matching_rule"] for m in exposure_matches}))
            out["candidate_event_source_urls"] = ";".join(sorted({m["source_url"] for m in exposure_matches}))
            out["candidate_event_published_dates"] = ";".join(sorted({m["published_date"] for m in exposure_matches}))
            out["candidate_event_explanation"] = (
                "This notice falls within the category, scope proxy and time window of "
                f"{len(campaign_ids)} official external-event campaign(s): {', '.join(campaign_ids)}. "
                "This is a candidate context match for source checking, not confirmed operational exposure. "
                "The original source and matching rule remain visible for review."
            )
        else:
            out["candidate_event_context_flag"] = "0"
            out["candidate_campaign_count"] = "0"
            out["candidate_campaign_ids"] = ""
            out["candidate_event_category_proxy"] = ""
            out["candidate_event_matching_rule"] = ""
            out["candidate_event_source_urls"] = ""
            out["candidate_event_published_dates"] = ""
            out["candidate_event_explanation"] = ""
        wide_rows.append(out)
    return wide_rows


def write_manifest(scored_rows: list[dict[str, str]], matches: list[dict[str, str]]) -> None:
    campaign_counts: dict[str, int] = {}
    for match in matches:
        campaign_counts.setdefault(match["event_campaign_id"], set()).add(match["exposure_id"])  # type: ignore[arg-type]
    campaign_counts_final = {k: len(v) for k, v in campaign_counts.items()}  # type: ignore[arg-type]
    union_exposures = {m["exposure_id"] for m in matches}

    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "crosswalk_version": CROSSWALK_VERSION,
        "boe_input_sha256": hashlib.sha256(SCORED.read_bytes()).hexdigest(),
        "events_input_sha256": hashlib.sha256(EVENTS.read_bytes()).hexdigest(),
        "total_portfolio_rows": len(scored_rows),
        "union_matched_exposures": len(union_exposures),
        "union_matched_share": round(len(union_exposures) / len(scored_rows), 6) if scored_rows else 0,
        "matches_by_campaign": campaign_counts_final,
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest  # type: ignore[return-value]


def main() -> int:
    scored_rows = load_scored()
    events = load_events()
    original_hash_before = hashlib.sha256(SCORED.read_bytes()).hexdigest()

    matches = build_matches(scored_rows, events)
    wide_rows = summarize_onto_scored(scored_rows, matches)

    match_fieldnames = [
        "event_id", "event_campaign_id", "exposure_id", "contract_id", "matching_rule",
        "geography_basis", "category_proxy", "source_url", "published_date", "evidence_summary",
    ]
    with MATCHES_OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=match_fieldnames)
        writer.writeheader()
        writer.writerows(matches)

    wide_fieldnames = list(wide_rows[0].keys()) if wide_rows else []
    with WIDE_OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=wide_fieldnames)
        writer.writeheader()
        writer.writerows(wide_rows)

    manifest = write_manifest(scored_rows, matches)

    original_hash_after = hashlib.sha256(SCORED.read_bytes()).hexdigest()
    assert original_hash_before == original_hash_after, "Frozen scored file must never be modified by this module."

    print("Matches (long):", len(matches))
    print("Union matched exposures:", manifest["union_matched_exposures"], "/", manifest["total_portfolio_rows"])
    print("By campaign:", manifest["matches_by_campaign"])
    print("Original scored file SHA-256 unchanged:", original_hash_after == original_hash_before)
    return 0


if __name__ == "__main__":
    sys.exit(main())
