# Procurement Geopolitical Event Review (PGER)

PGER is a reproducible Business Intelligence and Data Analytics prototype for organising public-procurement notices into a transparent review queue. It combines a structural priority score with a separate, source-linked view of relevant external events so that a reviewer can see both the portfolio context and the evidence that may justify a closer check.

This repository contains the executed end-to-end notebook, Streamlit dashboard, processed evidence, source records, pipeline code, figures, and automated checks. The thesis document and private API credentials are intentionally excluded.

## What the project does

1. Downloads and verifies a frozen Spanish public-procurement dataset published on Zenodo.
2. Cleans the 2014-2024 source and applies the declared 2022-2024 analytical scope.
3. Creates one reproducible row per unique published contracting notice.
4. Calculates a visible structural review-priority score from contract value and concentration measures.
5. Keeps documented external-event context separate from that structural score.
6. Presents the resulting evidence through one executed notebook and a source-linked dashboard.

The score orders records for review; it is not a probability of disruption. The event layer helps a reviewer find source-linked context and does not silently change the structural score.

## Main evidence

| Item | Current frozen result |
|---|---:|
| Raw source rows | 97,154 |
| Eligible rows before duplicate-link removal | 26,036 |
| Unique notices in the final portfolio | 24,765 |
| Frozen official external-event records | 4 |
| Distinct notices linked to candidate event context | 51 |
| Executed notebook | 1 |

Detailed definitions, source links, filtering decisions, and file checksums are recorded in [docs/SOURCE_REGISTER.md](docs/SOURCE_REGISTER.md) and [docs/source_audit.json](docs/source_audit.json).

## Repository structure

| Path | Purpose |
|---|---|
| `notebook/` | One executed notebook covering ingestion, cleaning, transformation, analysis, visualisation, live-source checks, and dashboard launch |
| `dashboard/` | Streamlit review interface and Windows launcher |
| `src/` | Reproducible data, scoring, event-matching, sensitivity, discovery, and validation scripts |
| `data/processed/` | Frozen files used by the notebook, dashboard, and reported figures |
| `data/raw/external_evidence/` | Retained official source records for the frozen event registry |
| `data/evaluation/` | Researcher-labelled development material for the local-model feasibility check |
| `docs/` | Source register, evidence rules, event crosswalk, and audit records |
| `figures/` | Current exported analytical and dashboard figures |
| `tests/` | Automated checks for scope, scoring, matching, and evidence integrity |

## Quick start

Python 3.11 or newer is recommended.

```powershell
git clone https://github.com/hamzatebri/PGER-public-data-prototype.git
cd PGER-public-data-prototype
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run dashboard/dashboard.py
```

Open `http://localhost:8501` if the browser does not open automatically. The dashboard reads the committed processed evidence, so the raw BOE file is not required for this quick start.

## Reproduce from the raw source

The large raw CSV is not committed. The downloader retrieves the exact Version 3 file from [Zenodo](https://zenodo.org/records/18712463) and verifies its size, published MD5 checksum, and project SHA-256 checksum before the pipeline reads it.

```powershell
python src/download_boe_dataset.py
python src/build_portfolio.py
python src/score_portfolio.py
python src/match_events_to_portfolio.py
python src/analyse_sensitivity.py
python src/generate_source_audit.py
python -m pytest -q
```

Open `notebook/Hamza_Tebri_PGER_TFG_End_to_End.ipynb` to inspect the already executed analysis. To rebuild that notebook after reproducing the data, run `python src/build_end_to_end_notebook.py` and execute it from top to bottom.

## Supplementary APIs and local model

The services below support an optional live-discovery demonstration. They help PGER find recent reports, compare coverage across providers, and assign candidate reports to a simple event family for human review. They are supplementary: their output is never read by `score_portfolio.py`, never changes the frozen structural review-priority score, and is not used to recalculate the reported thesis results.

| Service | What it provides | How PGER uses it | Access and project setting |
|---|---|---|---|
| [Tavily Search API](https://docs.tavily.com/documentation/api-reference/endpoint/search) | Web search results with a title and source URL | Sends each of the three event-family queries to `POST https://api.tavily.com/search` and retains up to three candidate results per query | API key in `TAVILY_API_KEY` |
| [The Guardian Open Platform](https://open-platform.theguardian.com/documentation/search) | Searchable Guardian articles with titles, publication dates, and direct URLs | Searches the Content API, requests the newest results, and retains up to three candidates per event-family query | Developer key in `GUARDIAN_API_KEY`; the public value `test` is treated as unconfigured |
| [NewsAPI Everything](https://newsapi.org/docs/endpoints/everything) | Recent and historical article metadata from multiple publishers | Searches `/v2/everything`, sorts by publication date, and retains up to three candidates per event-family query | API key in `NEWSAPI_KEY` |
| [GNews Search API](https://docs.gnews.io/endpoints/search-endpoint) | News article titles, publication dates, and URLs from the GNews index | Searches `/api/v4/search` and retains up to three candidates per event-family query | API key in `GNEWS_API_KEY` |
| [NewsData.io Latest News API](https://newsdata.io/documentation) | Recent English-language article metadata | Searches `/api/1/latest` in English and retains up to three candidates per event-family query | API key in `NEWSDATA_API_KEY` |
| [GDELT DOC 2.0 API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/) | A credential-free search of global news coverage | Runs one narrow, one-result health query separately from the normal batch. The result is reused for 24 hours to respect the public endpoint's limits | No key required; endpoint and cooldown rules are documented in `docs/GDELT_USAGE_POLICY.md` |
| [LM Studio local API](https://lmstudio.ai/docs/developer/rest) | Local model inference through an OpenAI-compatible HTTP interface | Sends each deduplicated candidate title to `openai/gpt-oss-20b` at `/v1/chat/completions`. The model returns one structured label: trade policy, logistics and transport, conflict and security, or not relevant | Local server in `LM_STUDIO_BASE_URL`; model name in `LM_STUDIO_MODEL`; no external article text or private label is sent to a cloud model |

### How the optional refresh works

`src/live_evidence_discovery.py` uses the same three fixed searches for every routine provider: EU sanctions and procurement restrictions, Panama Canal transit constraints, and Red Sea shipping attacks. This keeps the provider comparison consistent rather than changing the question for each source.

The script then removes repeated links using a canonical URL, sends each remaining title to the local model, and saves a credential-free snapshot in `data/live_refresh/live_candidates_<date>.csv`. It also saves `live_provider_status_<date>.json`, which records whether each provider was configured, how many queries succeeded, how many candidates it returned, and any safe error status without storing credentials or request URLs containing keys.

`src/check_live_services.py` provides a low-volume health check. It requests only one result from each configured news provider, checks the LM Studio model with one known example, and calls GDELT at most once in a 24-hour period. The dashboard reads the saved files and presents this information as a separate demonstration panel, not as frozen evidence or a scoring input.

### Configure and run the supplementary services

```powershell
Copy-Item .env.example .env
python src/check_live_services.py
python src/live_evidence_discovery.py
python src/evaluate_local_llm.py
```

Add only the credentials you choose to share to the local `.env` file. Git ignores that file. LM Studio is expected at `http://127.0.0.1:1234/v1` with `openai/gpt-oss-20b` loaded when the local-model exercise is run.

## Data sources

- [BOE public-procurement release, Version 3](https://zenodo.org/records/18712463), the main portfolio source.
- [Banco de España EBAE sample](https://doi.org/10.48719/BELab.EBAE20T422T2_01), a separate anonymised firm-survey ingestion example.
- [GDELT DOC 2.0 API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/), used only for a low-volume optional availability check.

The event registry also preserves direct links to the official Council of the European Union, Panama Canal Authority, and International Maritime Organization records used in the frozen analysis.

## Evidence boundary

The public records document buyer-awardee contracting notices, not complete private-company supply chains. PGER supports prioritisation and source checking; a real operational deployment would require authorised company purchasing data and human review.
