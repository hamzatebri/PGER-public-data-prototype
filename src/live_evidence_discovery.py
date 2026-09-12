"""Optional live evidence discovery - demonstrates genuine multi-API
integration and local-LLM triage, explicitly outside the frozen thesis
metrics. Live results never merge into frozen figures or the structural
score.

The normal refresh queries five keyed discovery sources (Tavily, Guardian Open
Platform, NewsAPI, GNews and NewsData.io) for candidate articles matching the
same three documented event families as the frozen registry. GDELT DOC 2.0 is
checked separately with one small request and its latest saved health result is
shown in the dashboard. This avoids repeated calls to GDELT's quota-limited
public endpoint. The script deduplicates canonical URLs, then classifies each
candidate with the local LM Studio model (openai/gpt-oss-20b) using the same
prompt and taxonomy as evaluate_local_llm.py.
Per-provider counts are recorded so each source's real contribution is
auditable, not merely claimed.

Output: data/live_refresh/live_candidates_<date>.csv - never read by
score_portfolio.py, match_events_to_portfolio.py, or any frozen figure
script.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "live_refresh"

# Loads ROOT/.env if present, without overriding any variable already set in the real
# environment. Keys are still read from os.environ below, never hardcoded in this file.
load_dotenv(ROOT / ".env")

# Each key is read from the environment only; no personal key is hardcoded here. The
# Guardian documentation's "test" placeholder is deliberately treated as unconfigured
# because it no longer authorises requests. A personal developer key can enable it.
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
GUARDIAN_API_KEY = os.environ.get("GUARDIAN_API_KEY", "test")
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")
GNEWS_API_KEY = os.environ.get("GNEWS_API_KEY", "")
NEWSDATA_API_KEY = os.environ.get("NEWSDATA_API_KEY", "")
LM_BASE_URL = os.environ.get("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
LM_MODEL = os.environ.get("LM_STUDIO_MODEL", "openai/gpt-oss-20b")
CLASSES = ["trade_policy", "logistics_transport", "conflict_security", "not_relevant"]

QUERIES = [
    ("trade_policy", "EU sanctions Russia public procurement restriction"),
    ("logistics_transport", "Panama Canal transit capacity restriction"),
    ("conflict_security", "Red Sea Gulf of Aden shipping attack"),
]

SYSTEM_PROMPT = """Classify one public news article into exactly one event family for a
Spanish public-procurement review dashboard.

Definitions:
- trade_policy: sanctions, tariffs, export controls, import restrictions, or trade regulation.
- logistics_transport: non-violent transport capacity, route, port, canal, shipping, or transit constraints.
- conflict_security: attacks, piracy, war, armed conflict, military action, or physical security threats.
- not_relevant: the article does not describe an official measure or a documented physical/security disruption.

Return only JSON matching the requested schema."""


def safe_error(exc: Exception) -> str:
    """Return a useful status without saving request URLs or credentials."""
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        reason = exc.response.reason or "HTTP error"
        return f"HTTP {exc.response.status_code} {reason}"
    if isinstance(exc, requests.Timeout):
        return "Request timed out"
    if isinstance(exc, requests.ConnectionError):
        return "Connection error"
    return type(exc).__name__


def canonical_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def query_tavily(query: str, max_results: int = 3) -> tuple[list[dict], str | None]:
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": TAVILY_API_KEY, "query": query, "max_results": max_results},
            timeout=20,
        )
        resp.raise_for_status()
        return [
            {"source": "tavily", "title": r.get("title", ""), "url": r["url"], "published_date": ""}
            for r in resp.json().get("results", [])
        ], None
    except Exception as exc:  # noqa: BLE001 - live source, degrade gracefully
        print(f"  [tavily] query failed: {exc}")
        return [], safe_error(exc)


def query_guardian(query: str, max_results: int = 3) -> tuple[list[dict], str | None]:
    try:
        resp = requests.get(
            "https://content.guardianapis.com/search",
            params={
                "q": query,
                "api-key": GUARDIAN_API_KEY,
                "page-size": max_results,
                "order-by": "newest",
            },
            timeout=20,
        )
        resp.raise_for_status()
        results = resp.json().get("response", {}).get("results", [])
        return [
            {
                "source": "guardian",
                "title": r.get("webTitle", ""),
                "url": r["webUrl"],
                "published_date": r.get("webPublicationDate", "")[:10],
            }
            for r in results
        ], None
    except Exception as exc:  # noqa: BLE001 - optional live source
        print(f"  [guardian] query failed: {exc}")
        return [], safe_error(exc)


def query_newsapi(query: str, max_results: int = 3) -> tuple[list[dict], str | None]:
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={"q": query, "pageSize": max_results, "sortBy": "publishedAt", "apiKey": NEWSAPI_KEY},
            timeout=20,
        )
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
        return [
            {"source": "newsapi", "title": a.get("title", "") or "", "url": a["url"], "published_date": (a.get("publishedAt") or "")[:10]}
            for a in articles
        ], None
    except Exception as exc:  # noqa: BLE001
        print(f"  [newsapi] query failed: {exc}")
        return [], safe_error(exc)


def query_gnews(query: str, max_results: int = 3) -> tuple[list[dict], str | None]:
    try:
        resp = requests.get(
            "https://gnews.io/api/v4/search",
            params={"q": query, "max": max_results, "apikey": GNEWS_API_KEY},
            timeout=20,
        )
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
        return [
            {"source": "gnews", "title": a.get("title", ""), "url": a["url"], "published_date": (a.get("publishedAt") or "")[:10]}
            for a in articles
        ], None
    except Exception as exc:  # noqa: BLE001
        print(f"  [gnews] query failed: {exc}")
        return [], safe_error(exc)


def query_newsdata(query: str, max_results: int = 3) -> tuple[list[dict], str | None]:
    try:
        resp = requests.get(
            "https://newsdata.io/api/1/latest",
            params={"q": query, "apikey": NEWSDATA_API_KEY, "language": "en"},
            timeout=20,
        )
        resp.raise_for_status()
        articles = (resp.json().get("results") or [])[:max_results]
        return [
            {"source": "newsdata", "title": a.get("title", "") or "", "url": a["link"], "published_date": (a.get("pubDate") or "")[:10]}
            for a in articles
        ], None
    except Exception as exc:  # noqa: BLE001
        print(f"  [newsdata] query failed: {exc}")
        return [], safe_error(exc)


def query_gdelt(query: str, max_results: int = 3) -> tuple[list[dict], str | None]:
    try:
        # GDELT documents rate limits on the hosted DOC API. Make exactly one
        # narrow request and never retry a 429 response automatically.
        resp = requests.get(
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={
                "query": query,
                "mode": "artlist",
                "maxrecords": max_results,
                "format": "json",
                "sort": "datedesc",
                "timespan": "1week",
            },
            headers={"User-Agent": "PGER academic prototype/1.0"},
            timeout=30,
        )
        resp.raise_for_status()
        try:
            payload = resp.json()
        except ValueError:
            raise RuntimeError("GDELT returned a non-JSON response") from None

        articles = payload.get("articles", [])
        return [
            {"source": "gdelt", "title": a.get("title", ""), "url": a["url"], "published_date": a.get("seendate", "")[:8]}
            for a in articles
        ], None
    except Exception as exc:  # noqa: BLE001
        print(f"  [gdelt] query failed: {exc}")
        return [], safe_error(exc)


def classify_local(title: str) -> str:
    payload = {
        "model": LM_MODEL,
        "temperature": 0,
        "seed": 42,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Title: {title}"},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "event_family",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {"event_family": {"type": "string", "enum": CLASSES}},
                    "required": ["event_family"],
                    "additionalProperties": False,
                },
            },
        },
    }
    resp = requests.post(
        f"{LM_BASE_URL}/chat/completions",
        json=payload,
        headers={"Authorization": "Bearer lm-studio"},
        timeout=120,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)["event_family"]


PROVIDERS = ("tavily", "guardian", "newsapi", "gnews", "newsdata", "gdelt")
ROUTINE_PROVIDERS = ("tavily", "guardian", "newsapi", "gnews", "newsdata")
QUERY_FN = {
    "tavily": query_tavily, "guardian": query_guardian, "newsapi": query_newsapi,
    "gnews": query_gnews, "newsdata": query_newsdata, "gdelt": query_gdelt,
}


def latest_saved_health(service: str) -> tuple[dict | None, str | None]:
    """Return the newest credential-free health result for one service."""
    for path in sorted(OUT_DIR.glob("live_service_health_*.json"), reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        item = payload.get("services", {}).get(service)
        if isinstance(item, dict):
            return item, item.get("checked_at") or payload.get("generated_utc")
    return None, None


PROVIDER_KEYS = {
    "tavily": TAVILY_API_KEY,
    "guardian": "" if GUARDIAN_API_KEY == "test" else GUARDIAN_API_KEY,
    "newsapi": NEWSAPI_KEY,
    "gnews": GNEWS_API_KEY,
    "newsdata": NEWSDATA_API_KEY,
    "gdelt": "no_key_required",
}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    seen: dict[str, dict] = {}
    provider_attempts = {p: 0 for p in PROVIDERS}
    provider_failures = {p: 0 for p in PROVIDERS}
    provider_last_error = {p: None for p in PROVIDERS}
    lm_attempts = 0
    lm_failures = 0
    lm_last_error: str | None = None
    for target_family, query in QUERIES:
        print(f"Querying for [{target_family}]: {query!r}")
        candidates: list[dict] = []
        for provider in ROUTINE_PROVIDERS:
            if not PROVIDER_KEYS[provider]:
                provider_last_error[provider] = "not configured"
                continue
            results, error = QUERY_FN[provider](query)
            provider_attempts[provider] += 1
            if error is not None:
                provider_failures[provider] += 1
                provider_last_error[provider] = error
            candidates += results
        for c in candidates:
            key = canonical_url(c["url"])
            if key not in seen:
                c["target_family"] = target_family
                c["canonical_url"] = key
                seen[key] = c

    print(f"Deduplicated candidates: {len(seen)}")
    rows = []
    for c in seen.values():
        lm_attempts += 1
        try:
            predicted = classify_local(c["title"])
        except Exception as exc:  # noqa: BLE001 - LM Studio may be offline
            print(f"  [lm_studio] classification failed for {c['title'][:50]!r}: {exc}")
            lm_failures += 1
            lm_last_error = safe_error(exc)
            predicted = "unavailable"
        rows.append(
            {
                "source": c["source"],
                "title": c["title"],
                "url": c["url"],
                "published_date": c.get("published_date", ""),
                "target_family_queried": c["target_family"],
                "local_llm_predicted_family": predicted,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    date_tag = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_path = OUT_DIR / f"live_candidates_{date_tag}.csv"
    import csv

    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [
            "source", "title", "url", "published_date", "target_family_queried",
            "local_llm_predicted_family", "retrieved_at",
        ])
        writer.writeheader()
        writer.writerows(rows)

    from collections import Counter
    per_provider = Counter(r["source"] for r in rows)
    print("Per-provider candidate counts (before classification):", dict(per_provider))

    status_path = OUT_DIR / f"live_provider_status_{date_tag}.json"
    status = {
        provider: {
            "configured": bool(PROVIDER_KEYS[provider]),
            "ok": provider_failures[provider] < provider_attempts[provider],
            "queries_attempted": provider_attempts[provider],
            "queries_failed": provider_failures[provider],
            "candidates_retrieved": per_provider.get(provider, 0),
            "last_error": provider_last_error[provider] if provider_failures[provider] else None,
        }
        for provider in PROVIDERS
    }
    gdelt_health, gdelt_checked_at = latest_saved_health("gdelt")
    status["gdelt"] = {
        "configured": True,
        "ok": bool(gdelt_health and gdelt_health.get("ok")),
        "status": "checked_separately" if gdelt_health else "check_required",
        "queries_attempted": 0,
        "queries_failed": 0,
        "candidates_retrieved": 0,
        "last_error": None if gdelt_health and gdelt_health.get("ok") else (
            gdelt_health.get("error") if gdelt_health else None
        ),
        "last_checked_utc": gdelt_checked_at,
        "note": (
            "Not queried during the batch refresh. GDELT DOC is checked separately "
            "with one request because its public endpoint is quota-limited."
        ),
    }
    status["lm_studio"] = {
        "configured": True,
        "ok": lm_attempts > 0 and lm_failures == 0,
        "queries_attempted": lm_attempts,
        "queries_failed": lm_failures,
        "candidates_retrieved": lm_attempts - lm_failures,
        "last_error": lm_last_error,
    }
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")

    print(f"Wrote {len(rows)} live candidates to {out_path}")
    print(f"Wrote per-provider status to {status_path}")
    print("This file is a live discovery demonstration only. It is never read by")
    print("score_portfolio.py, match_events_to_portfolio.py, or any frozen thesis figure.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
