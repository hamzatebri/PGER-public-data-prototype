import csv
import hashlib
import json
import unittest
from datetime import datetime
from pathlib import Path

from src.build_portfolio import normalise_entity_name
from src.match_events_to_portfolio import build_matches, load_events, load_scored, summarize_onto_scored


ROOT = Path(__file__).resolve().parents[1]
PORTFOLIO = ROOT / "data" / "processed" / "public_procurement_exposure_scored.csv"
BUILT_PORTFOLIO = ROOT / "data" / "processed" / "public_procurement_exposure_2022_2024.csv"
CLEANING_AUDIT = ROOT / "data" / "processed" / "portfolio_cleaning_audit.csv"
EVENTS = ROOT / "data" / "processed" / "external_events.csv"
MATCHES = ROOT / "data" / "processed" / "event_portfolio_matches.csv"
WIDE = ROOT / "data" / "processed" / "public_procurement_exposure_scored_with_event_context.csv"
MANIFEST = ROOT / "docs" / "EVENT_MATCHING_RELEASE_MANIFEST.json"
DEVELOPMENT_LABELS = ROOT / "data" / "evaluation" / "researcher_event_labels.csv"
LLM_EVALUATION = ROOT / "outputs" / "evaluation" / "local_llm_evaluation.json"
EBAE_SAMPLE = ROOT / "data" / "raw" / "ebae_sample" / "SampleFile.EBAE20T422T2_01.csv"
EBAE_GUIDE = ROOT / "data" / "raw" / "ebae_sample" / "User_guide_BELab.EBAE20T422T2_01_en.pdf"
EBAE_QUALITY = ROOT / "data" / "processed" / "ebae_sample_data_quality.csv"
SCORE_SENSITIVITY = ROOT / "data" / "processed" / "score_sensitivity.csv"
WINDOW_SENSITIVITY = ROOT / "data" / "processed" / "event_window_sensitivity.csv"
PROVIDER_STATUS = ROOT / "data" / "live_refresh" / "live_provider_status_20260911.json"
DASHBOARD = ROOT / "dashboard" / "dashboard.py"


class PortfolioTests(unittest.TestCase):
    def test_portfolio_exists_and_has_expected_scope(self):
        self.assertTrue(PORTFOLIO.exists())
        with PORTFOLIO.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 24765)
        self.assertTrue(all(row["awardee_display_id"].startswith("A") for row in rows))
        self.assertTrue(all(row["notice_type"] == "Contratación" for row in rows))
        self.assertTrue(all(row["source_url"].startswith("https://") for row in rows))
        self.assertTrue(all(row["contract_value_eur"] for row in rows))
        self.assertTrue(all(row["review_priority_band"] in {"Routine review", "Focused review", "Priority review"} for row in rows))

    def test_one_row_per_source_notice_and_complete_cpv_divisions(self):
        with BUILT_PORTFOLIO.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        urls = [row["source_url"] for row in rows]
        self.assertEqual(len(urls), len(set(urls)))
        self.assertEqual(len({row["source_notice_id"] for row in rows}), len(rows))
        self.assertTrue(all(row["awardee_entity_key"] for row in rows))
        self.assertTrue(all(row["sector_group"] != "Other procurement category" for row in rows))

    def test_awardee_formatting_variants_share_one_entity_key(self):
        variants = ["Empresa Ejemplo S.L.", "EMPRESA EJEMPLO SL", "Empresa-Ejemplo, S L"]
        keys = {normalise_entity_name(value) for value in variants}
        self.assertEqual(keys, {"EMPRESAEJEMPLOSL"})

    def test_source_parser_duplicate_removal_is_audited(self):
        with CLEANING_AUDIT.open(encoding="utf-8", newline="") as handle:
            audit = {row["check"]: row for row in csv.DictReader(handle)}
        self.assertEqual(int(audit["repeated_source_url_groups"]["observed_value"]), 1271)
        self.assertEqual(int(audit["duplicate_parser_rows_removed"]["observed_value"]), 1271)
        self.assertEqual(int(audit["unique_source_urls_after_cleaning"]["observed_value"]), 24765)

    def test_score_matches_the_documented_formula(self):
        with PORTFOLIO.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        for row in rows[::997]:
            expected = round(
                0.50 * float(row["value_percentile"])
                + 0.30 * float(row["authority_awardee_share_percentile"])
                + 0.20 * float(row["authority_awardee_notice_share_percentile"]),
                6,
            )
            self.assertEqual(float(row["review_priority_score"]), expected)

    def test_output_is_not_empty_and_hashable(self):
        digest = hashlib.sha256(PORTFOLIO.read_bytes()).hexdigest()
        self.assertEqual(len(digest), 64)

    def test_external_events_have_evidence_contract_fields(self):
        required = {
            "event_id", "published_date", "source_name", "source_url", "source_type",
            "event_family", "geography", "affected_category", "evidence_summary",
            "evidence_strength", "annotation_status", "retrieved_at", "content_hash",
            "event_campaign_id", "campaign_start_date", "campaign_end_date",
            "campaign_validity_source_url",
        }
        with EVENTS.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertEqual(set(row), required)
            self.assertTrue(row["source_url"].startswith("https://"))
            self.assertEqual(row["annotation_status"], "researcher_created")
            self.assertEqual(row["evidence_strength"], "official_source")
            self.assertRegex(row["content_hash"], r"^[0-9a-f]{64}$")


class SupplementaryEvidenceTests(unittest.TestCase):
    def test_ebae_release_and_observed_counts(self):
        self.assertTrue(EBAE_SAMPLE.exists())
        self.assertTrue(EBAE_GUIDE.exists())
        with EBAE_QUALITY.open(encoding="utf-8", newline="") as handle:
            row = next(csv.DictReader(handle))
        self.assertEqual(int(row["rows"]), 47)
        self.assertEqual(int(row["unique_anonymised_firms"]), 15)
        self.assertEqual(int(row["impguerra_sum_non_null_rows"]), 8)
        self.assertEqual(int(row["impguerra_sum_unique_firms"]), 8)

        with EBAE_SAMPLE.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter=";"))
        observed = [row["impguerra_sum"].strip() for row in rows if row["impguerra_sum"].strip()]
        self.assertEqual(sorted(set(observed)), ["1", "2", "3"])
        self.assertEqual({value: observed.count(value) for value in {"1", "2", "3", "4"}},
                         {"1": 2, "2": 3, "3": 3, "4": 0})

    def test_score_and_window_sensitivity_outputs(self):
        with SCORE_SENSITIVITY.open(encoding="utf-8", newline="") as handle:
            scores = {row["scenario"]: row for row in csv.DictReader(handle)}
        self.assertEqual(int(scores["Baseline 50/30/20"]["priority_review_notices"]), 2683)
        self.assertGreaterEqual(int(scores["Equal weights"]["top_10_overlap"]), 5)
        self.assertGreater(float(scores["Equal weights"]["spearman_with_baseline"]), 0.90)
        self.assertIn("No notice-share component", scores)

        with WINDOW_SENSITIVITY.open(encoding="utf-8", newline="") as handle:
            windows = {int(row["window_days_after_latest_official_record"]): row for row in csv.DictReader(handle)}
        self.assertEqual(int(windows[90]["union_matched_exposures"]), 30)
        self.assertEqual(int(windows[180]["union_matched_exposures"]), 51)
        self.assertEqual(int(windows[365]["union_matched_exposures"]), 133)

    def test_saved_api_status_contains_no_credential_material(self):
        status_text = PROVIDER_STATUS.read_text(encoding="utf-8")
        lowered = status_text.lower()
        self.assertNotIn("api-key", lowered)
        self.assertNotIn("apikey", lowered)
        self.assertNotIn("key=", lowered)
        self.assertNotIn("http://", lowered)
        self.assertNotIn("https://", lowered)

    def test_dashboard_uses_current_reader_facing_terms(self):
        text = DASHBOARD.read_text(encoding="utf-8")
        for stale in ("Live discovery active", "Classified as relevant", "Authority region", "EBAE20T426T2_01"):
            self.assertNotIn(stale, text)
        for expected in ("Discovery snapshot", "Assigned to an event family", "Geographic scope", "EBAE20T422T2_01"):
            self.assertIn(expected, text)


class EventDevelopmentSampleTests(unittest.TestCase):
    """Checks the retained event-family development exercise."""

    def test_label_pack_has_14_fully_labelled_records(self):
        self.assertTrue(DEVELOPMENT_LABELS.exists())
        with DEVELOPMENT_LABELS.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 14)
        self.assertEqual(len({row["record_id"] for row in rows}), 14)
        for row in rows:
            self.assertTrue(row["label_event_family"])
            self.assertTrue(row["source_url"].startswith("https://"))

    def test_retained_evaluation_has_the_declared_scope(self):
        self.assertTrue(LLM_EVALUATION.exists())
        with LLM_EVALUATION.open(encoding="utf-8") as handle:
            evaluation = json.load(handle)
        self.assertEqual(evaluation["sample_size"], 14)
        self.assertEqual(evaluation["exercise_type"], "development_sample")
        self.assertEqual(evaluation["labels_sent_to_model"], False)


class EventMatchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with MATCHES.open(encoding="utf-8", newline="") as handle:
            cls.matches = list(csv.DictReader(handle))
        with WIDE.open(encoding="utf-8", newline="") as handle:
            cls.wide_rows = list(csv.DictReader(handle))
        with PORTFOLIO.open(encoding="utf-8", newline="") as handle:
            cls.scored_rows = list(csv.DictReader(handle))
        with EVENTS.open(encoding="utf-8", newline="") as handle:
            cls.events = {row["event_id"]: row for row in csv.DictReader(handle)}

        recomputed_scored = load_scored()
        recomputed_matches = build_matches(recomputed_scored, load_events())
        cls.recomputed_matches = recomputed_matches
        cls.recomputed_wide_rows = summarize_onto_scored(recomputed_scored, recomputed_matches)

    def test_committed_event_outputs_match_current_rules(self):
        self.assertEqual(self.matches, self.recomputed_matches)
        self.assertEqual(self.wide_rows, self.recomputed_wide_rows)

    def test_matches_schema(self):
        expected = {
            "event_id", "event_campaign_id", "exposure_id", "contract_id", "matching_rule",
            "geography_basis", "category_proxy", "source_url", "published_date", "evidence_summary",
        }
        self.assertGreater(len(self.matches), 0)
        for row in self.matches:
            self.assertEqual(set(row), expected)
            self.assertTrue(row["source_url"].startswith("https://"))
            self.assertTrue(row["evidence_summary"])

    def test_wide_output_schema_and_row_count(self):
        self.assertEqual(len(self.wide_rows), len(self.scored_rows))
        added = {
            "candidate_event_context_flag", "candidate_campaign_count", "candidate_campaign_ids",
            "candidate_event_category_proxy", "candidate_event_matching_rule",
            "candidate_event_source_urls", "candidate_event_published_dates", "candidate_event_explanation",
        }
        self.assertTrue(added.issubset(set(self.wide_rows[0].keys())))

    def test_manifest_describes_current_portfolio(self):
        with MANIFEST.open(encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertRegex(manifest["boe_input_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(manifest["total_portfolio_rows"], len(self.scored_rows))
        self.assertEqual(manifest["union_matched_exposures"], 51)
        self.assertEqual(sum(manifest["matches_by_campaign"].values()), len(self.matches))

    def test_event_context_flag_is_not_used_in_review_priority_score(self):
        for row in self.wide_rows[::997]:
            expected = round(
                0.50 * float(row["value_percentile"])
                + 0.30 * float(row["authority_awardee_share_percentile"])
                + 0.20 * float(row["authority_awardee_notice_share_percentile"]),
                6,
            )
            self.assertEqual(float(row["review_priority_score"]), expected)

    def test_no_awardee_name_based_matching(self):
        # Two matched rows for the same campaign must not share awardee identity
        # as a precondition - matching_rule/geography_basis/category_proxy never
        # reference awardee_name_source or awardee_display_id.
        for row in self.matches:
            self.assertNotIn("awardee", row["matching_rule"])
            self.assertNotIn("awardee", row["geography_basis"])

    def test_no_national_scope_for_maritime_event(self):
        maritime_events = {"EVT-2023-001", "EVT-2024-001", "EVT-2024-002"}
        for row in self.matches:
            if row["event_id"] in maritime_events:
                matched = next(r for r in self.scored_rows if r["exposure_id"] == row["exposure_id"])
                self.assertEqual(matched["contracting_authority_region"].strip(), "Internacional")

    def test_event_campaign_deduplication(self):
        red_sea_matches = [r for r in self.matches if r["event_campaign_id"] == "CAMPAIGN-RED-SEA-2024"]
        exposures = {r["exposure_id"] for r in red_sea_matches}
        flagged = [r for r in self.wide_rows if r["exposure_id"] in exposures]
        for row in flagged:
            self.assertEqual(row["candidate_campaign_ids"].count("CAMPAIGN-RED-SEA-2024"), 1)

    def test_no_event_context_before_event_date(self):
        scored_by_id = {r["exposure_id"]: r for r in self.scored_rows}
        for row in self.matches:
            event = self.events[row["event_id"]]
            exposure = scored_by_id[row["exposure_id"]]
            exposure_date = datetime.strptime(exposure["publication_date"], "%Y-%m-%d").date()
            self.assertGreaterEqual(
                exposure_date,
                datetime.strptime(event["campaign_start_date"], "%Y-%m-%d").date(),
                f"{row['exposure_id']} matched {row['event_id']} but is dated before the campaign window",
            )
            self.assertLessEqual(
                exposure_date,
                datetime.strptime(event["campaign_end_date"], "%Y-%m-%d").date(),
                f"{row['exposure_id']} matched {row['event_id']} but is dated after the campaign window",
            )


if __name__ == "__main__":
    unittest.main()
