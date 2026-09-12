# GDELT DOC Usage Policy

## Why the integration is separate

GDELT states that its hosted DOC and Context APIs are rate limited to protect
the underlying search clusters. It recommends the downloadable Web NGrams 3.0
dataset for repeated or high-volume queries. PGER needs only a small service
availability check, so downloading the much larger continuous dataset would
add complexity without improving the submitted analysis.

## Request used by PGER

- Endpoint: `https://api.gdeltproject.org/api/v2/doc/doc`
- Mode: `artlist`
- Output: JSON
- Scope: one exact research query, one result, newest first, previous week
- Authentication: no key required
- Frequency: at most one request in 24 hours
- Automatic retry after HTTP 429: none

The five keyed discovery services perform the normal three-query refresh.
GDELT is not called from that loop. The latest credential-free GDELT health
result is stored in `data/live_refresh/live_service_health_YYYYMMDD.json` and
shown separately in the dashboard.

## Response handling

- HTTP 200 with valid JSON: save the check as available.
- HTTP 429: record the public quota response and stop; do not retry in a loop.
- Non-JSON response, timeout or connection error: record the short error and
  leave the previous candidate snapshot unchanged.
- No recent saved check: show that a separate check is required rather than
  labelling the unqueried service as failed.

## Official documentation

- DOC 2.0 parameters and article-list mode:
  `https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/`
- Rate limits and the Web NGrams recommendation:
  `https://blog.gdeltproject.org/ukraine-api-rate-limiting-web-ngrams-3-0/`
- Explanation of hosted API quotas and HTTP 429 responses:
  `https://blog.gdeltproject.org/behind-the-scenes-api-quotas-the-impact-of-a-fraction-of-a-qps/`
