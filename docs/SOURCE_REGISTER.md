# Source Register

This register identifies the files and rules behind the reported results. A
reviewer can use it with `docs/EXTERNAL_EVIDENCE_CONTRACT.md` before running
the reproduction sequence. The values below come from the current package,
not from an earlier portfolio build.

## Main empirical dataset: BOE public-procurement release

| Field | Value |
|---|---|
| Source | Muñoz Plá's dataset collected from Section V-A contracting notices in the Boletín Oficial del Estado, released via Zenodo |
| DOI | `10.5281/zenodo.18712463` |
| Creator | Manuel Muñoz Plá, Universitat Oberta de Catalunya |
| Release | Version 3, published 28 July 2026 |
| Local file | `data/raw/boe_procurement/licitaciones_contrataciones_BOE_2014_2024.csv` |
| SHA-256 | `d40c6d8318075b48a6aeba376a1b7300f5ac363aaeb8d314534bdd4918b5256e` |
| Raw row count | 97,154 (full 2014-2024 release, before scope filtering) |
| Raw schema | `Institucion`, `Organismo responsable`, `Expediente`, `Fecha`, `Tipo`, `Naturaleza`, `Objeto`, `Procedimiento`, `Ambito_geografico`, `Materias_CPV`, `Codigos_CPV`, `valor_estimado_licitacion`, `valor_oferta_adjudicada`, `nombre_adjudicatario`, `Enlace HTML` |
| Licence | CC0 |

## Official data links

| Data source | Role | Official record or access page |
|---|---|---|
| BOE public-procurement release, third Zenodo record | Main frozen analytical portfolio | `https://zenodo.org/records/18712463` |
| Banco de España EBAE microdata, release `EBAE20T422T2_01` | Supplementary anonymised firm-survey sample | `https://doi.org/10.48719/BELab.EBAE20T422T2_01` |
| GDELT DOC 2.0 API | Separate low-volume availability check for optional discovery; not an input to the frozen score | `https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/` |

The three data-access links returned a successful response on 11 September 2026. The
EBAE DOI resolves to the official Banco de España BELab page that provides
the sample file and its user guide. GDELT's rate-limit guidance is recorded in
`docs/GDELT_USAGE_POLICY.md`; it explains why the hosted DOC API is checked
separately rather than queried in a batch and is not counted as another dataset.

## Declared scope (applied by `src/build_portfolio.py`)

The sequential filter begins with 97,154 source rows. Selecting notice type
`Contratación` leaves 63,101 rows; applying the publication period from
2022-01-01 to 2024-12-31 leaves 26,040; and requiring a named awardee and a
parseable awarded value leaves 26,036. The source parser produced 1,271
repeated source links, so one award row is retained for each unique link.
The final portfolio therefore contains 24,765 unique notices. It retains 363
notices (1.5 per cent) with an explicit zero awarded value. Missing values
are not imputed. See `docs/EVIDENCE_POLICY.md` for the inclusion rationale.

## Processed outputs, in pipeline order

| Stage | File | Rows | SHA-256 |
|---|---|---|---|
| 1. Scored (pre-event-context) | `data/processed/public_procurement_exposure_scored.csv` | 24,765 | `0003450e4b14a072ca1b6861da6b2e60ef91d29eda3f5f4196bd078b86d8901c` |
| 2. External events (frozen registry) | `data/processed/external_events.csv` | 4 | `632efe2f94394b65bb889eb65f861c767ba84e0f3bbc266fdc70a7c8cb673696` |
| 3. Scored + event context (final wide file; read by the notebook, dashboard and frozen analytical figures) | `data/processed/public_procurement_exposure_scored_with_event_context.csv` | 24,765 | `6c903cf258e7c39db74811ae25308f5515311468026c78b2fd2e8a9d95cc462c` |
| 4. Event-to-portfolio matches | `data/processed/event_portfolio_matches.csv` | 52 match rows; 51 distinct notices | `df1f24c6b67cfb4014c46d4fdb9d7a759275ed59d0462cc1384069290577f0a0` |
| 5. Score-weight sensitivity | `data/processed/score_sensitivity.csv` | 8 configurations | `832bed9af3eeb77794933d2af3022d0d2e3cb589310d9278ee3a2a6819cb68a3` |
| 6. Event-window sensitivity | `data/processed/event_window_sensitivity.csv` | 3 windows | `9d1e63a6136cee632b31ef55987405019f310709dc51c94e0a60afaab6b6c3f2` |

Stage 3's schema: `exposure_id`, `source_notice_id`, `contract_id`, `notice_type`,
`contracting_authority_name`, `responsible_body`,
`contracting_authority_region`, `awardee_name_source`, `publication_date`,
`contract_value_eur`, `cpv_code`, `cpv_description`, `sector_group`,
`contract_type`, `procurement_procedure`, `object_description`,
`source_url`, `awardee_entity_key`, `awardee_display_id`, `awardee_contract_count`,
`awardee_portfolio_value_share`, `authority_awardee_value_share`,
`authority_awardee_notice_share`, `sector_portfolio_value_share`,
`data_quality_flags`, `value_percentile`,
`authority_awardee_share_percentile`,
`authority_awardee_notice_share_percentile`,
`review_priority_score`, `review_priority_band`, `score_definition`,
`candidate_event_context_flag`, `candidate_campaign_count`,
`candidate_campaign_ids`, `candidate_event_category_proxy`,
`candidate_event_matching_rule`, `candidate_event_source_urls`,
`candidate_event_published_dates`, `candidate_event_explanation`.

## How to verify

The hashes above identify the retained local files byte for byte. Git may change text line endings on another operating system. The current `source_audit.json` also provides `sha256_lf` for text files, allowing comparison after normalising CRLF to LF without changing data values.

Run `python src/build_portfolio.py`, `python src/score_portfolio.py`,
`python src/match_events_to_portfolio.py` and
`python src/generate_source_audit.py` from the project root. Then run the
tests. They check the final row count, one-row-per-source-notice rule, score
formula, event dates, category and geography rules, and input-file identity.
