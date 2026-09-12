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

## Optional live services

The frozen thesis evidence does not depend on live APIs. Optional discovery checks can use Tavily, The Guardian, NewsAPI, GNews, NewsData.io, GDELT, and a local LM Studio server.

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
