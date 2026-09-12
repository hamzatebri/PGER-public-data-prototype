"""Run low-volume health checks without repeatedly calling GDELT DOC."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import requests

from live_evidence_discovery import (
    GNEWS_API_KEY,
    GUARDIAN_API_KEY,
    LM_BASE_URL,
    NEWSDATA_API_KEY,
    NEWSAPI_KEY,
    OUT_DIR,
    QUERY_FN,
    TAVILY_API_KEY,
    classify_local,
    safe_error,
)


KEYS = {
    "tavily": TAVILY_API_KEY,
    "guardian": "" if GUARDIAN_API_KEY == "test" else GUARDIAN_API_KEY,
    "newsapi": NEWSAPI_KEY,
    "gnews": GNEWS_API_KEY,
    "newsdata": NEWSDATA_API_KEY,
    "gdelt": "no_key_required",
}


def recent_gdelt_check(max_age_hours: int = 24) -> tuple[dict | None, str | None]:
    """Reuse the latest GDELT result during the cooldown window."""
    now = datetime.now(timezone.utc)
    for path in sorted(OUT_DIR.glob("live_service_health_*.json"), reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            generated = datetime.fromisoformat(payload["generated_utc"])
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            continue
        item = payload.get("services", {}).get("gdelt")
        if isinstance(item, dict) and now - generated <= timedelta(hours=max_age_hours):
            return item, payload["generated_utc"]
    return None, None


def main() -> int:
    query = '"Red Sea" shipping disruption'
    checks: dict[str, dict[str, object]] = {}
    for provider, query_fn in QUERY_FN.items():
        if not KEYS[provider]:
            checks[provider] = {
                "configured": False,
                "ok": False,
                "result_count": 0,
                "error": "not configured",
            }
            continue
        if provider == "gdelt":
            cached, checked_at = recent_gdelt_check()
            if cached is not None:
                checks[provider] = {
                    **cached,
                    "status": "cached_recent_check",
                    "checked_at": checked_at,
                }
                continue
        results, error = query_fn(query, max_results=1)
        checks[provider] = {
            "configured": True,
            "ok": error is None,
            "result_count": len(results),
            "error": error,
            "status": "checked_now",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    try:
        model_response = requests.get(f"{LM_BASE_URL}/models", timeout=10)
        model_response.raise_for_status()
        family = classify_local("Cargo ship attacked in the Red Sea")
        checks["lm_studio"] = {
            "configured": True,
            "ok": family == "conflict_security",
            "result_count": 1,
            "error": None if family == "conflict_security" else f"unexpected label: {family}",
        }
    except Exception as exc:  # noqa: BLE001 - local service health check
        checks["lm_studio"] = {
            "configured": True,
            "ok": False,
            "result_count": 0,
            "error": safe_error(exc),
        }

    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "request_policy": (
            "one result requested per keyed provider; GDELT is checked at most once "
            "per 24 hours; credentials omitted"
        ),
        "services": checks,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUT_DIR / f"live_service_health_{datetime.now(timezone.utc):%Y%m%d}.json"
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(checks, indent=2))
    print(f"Saved credential-free health report to {output}")
    configured_failures = [
        name for name, item in checks.items() if item["configured"] and not item["ok"]
    ]
    return 1 if configured_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
