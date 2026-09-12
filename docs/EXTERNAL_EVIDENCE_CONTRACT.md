# External Evidence Contract

Every external event used by PGER must be stored as a row with the following fields:

| Field | Rule |
|---|---|
| `event_id` | Stable identifier created once for the local extract. |
| `published_date` | Date shown by the source, not the download date. |
| `source_name` | Publisher or institution. |
| `source_url` | Direct public URL to the source item. |
| `source_type` | Official notice, intergovernmental source, company disclosure, or reputable news report. |
| `event_family` | One controlled category: conflict/security, sanctions/trade policy, logistics/transport, natural hazard, regulatory, or market/commodity. |
| `geography` | Geography explicitly supported by the source. |
| `affected_category` | Procurement category supported by the source, or `general` when no category match is justified. |
| `evidence_summary` | Short plain-language description based only on the source. |
| `evidence_strength` | `official_source`, `secondary_source`, or `context`. This describes the source item, not whether the thesis collected primary research data. |
| `annotation_status` | `researcher_created`, `second_reviewed`, or `adjudicated`; never imply independent annotation unless completed. |
| `retrieved_at` | Timestamp of local retrieval. |
| `content_hash` | SHA-256 of the retained local evidence file. The file may be the downloaded source or a documented local extract when the publisher blocks automated archiving. |
| `event_campaign_id` | Groups dated records that document the same underlying disruption/regime (e.g. two IMO updates on the same Red Sea campaign) so they are never counted as independent events. |
| `campaign_start_date` | Date of the first official record in the campaign. |
| `campaign_end_date` | End of the pre-specified matching window: either a finite window from a single notice, or a window extended from a later record that documents the campaign's continuation. Fixed before matching, per `docs/EVENT_MATCHING_CROSSWALK.md`. |
| `campaign_validity_source_url` | The specific official record that justifies `campaign_end_date` — the same notice for a finite/unextended window, or a later record for a documented extension. |

External evidence provides context for human review. A realised loss is a separate outcome and is recorded only when a source documents it. The final test partition must be frozen before any threshold or prompt changes.

A notice becomes a candidate for an event-source check only when its publication date falls within the pre-specified event window and it satisfies the relevant category and broad geographic-scope rule. The flag records a time-aligned category and scope proxy for human review. It does not establish an awardee's country, transport route or operational exposure.
