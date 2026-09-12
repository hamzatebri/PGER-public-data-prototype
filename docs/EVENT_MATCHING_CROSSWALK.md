# Event Matching Crosswalk (frozen before running the matching module)

This file fixes every geography, category, and temporal rule used by
`src/match_events_to_portfolio.py` **before** the module is run against the
real portfolio. No rule in this file may be added to, widened, or adjusted
after seeing a match count.

Required sentence (used identically in the module, the thesis, and the
dashboard):

> A notice becomes a candidate for an event-source check only when its
> publication date falls within the pre-specified event window and it
> satisfies the relevant category and geographic-scope rule. The flag records
> a time-aligned category and broad scope proxy for human review. It does not
> establish an awardee's country, transport route or operational exposure.

## Geography rule — exact match only, no substring matching

A record's `contracting_authority_region` value is trimmed and compared with
`==`, never `in`/substring. One combined-region string in the portfolio
(`"Castilla y León, Cataluña, Andalucía, Internacional"`) contains the word
"Internacional" alongside other regions; this is not treated as
international scope under this rule, since the rule is exact equality
against the literal value `"Internacional"`. Verified count of exact-match
rows: **111 / 24,765**.

## Category rule — explicit CPV/sector table, with an unmapped bucket

| `affected_category` source value | Sector groups matched | CPV 2-digit prefixes matched | Rule name |
|---|---|---|---|
| `energy and public procurement` | `Petroleum, fuel, electricity and other energy sources` | — | `trade_restriction_sectoral_scope` |
| `general` (Panama Canal event — category comes from the event's documented mechanism, not this field) | `Transport equipment and auxiliary products` | `34`, `60`, `61`, `62`, `63`, `64` | `logistics_transport_category` |
| `transport and logistics` (Red Sea campaign) | `Transport equipment and auxiliary products` | `34`, `60`, `61`, `62`, `63`, `64` | `logistics_transport_category` |
| anything else | *(not mapped)* | *(not mapped)* | `no_category_evidence` |

Verified CPV-prefix row counts in the frozen portfolio (24,765 rows):
`34`=718, `60`=347, `61`=0, `62`=0, `63`=266, `64`=162.

## Per-event / per-campaign table

| Event / campaign | Official source | Mechanism | Geography rule | Category rule | Temporal window | What the match contributes | What still requires case evidence |
|---|---|---|---|---|---|---|---|
| `EVT-2022-001` | Council of the European Union, 2022-04-08 | 5th EU sanctions package on Russia, including measures affecting Russian imports and public-procurement participation | National (matches all rows because the measure applies in Spain as an EU member state) | Energy sector (`trade_restriction_sectoral_scope`) | 2022-04-08 to **2022-10-05** (180-day finite window) | Adds dated official sanctions context to energy notices published during the window | Awardee-level compliance and operational effects require contract or company evidence |
| `EVT-2023-001` | Panama Canal Authority, 2023-10-30 (ADV48-2023) | Reduced transit capacity due to a precipitation deficit in the Canal watershed | **International scope only** (`Internacional` exact match) | Transport/logistics (`logistics_transport_category`), based on the documented transit-capacity mechanism | 2023-10-30 to **2024-04-27** (180-day finite window) | Adds dated official canal-capacity context to international transport and logistics notices | Use of the Panama Canal requires route or company evidence |
| `EVT-2024-001` + `EVT-2024-002` (**one campaign**, `CAMPAIGN-RED-SEA-2024`) | International Maritime Organization, 2024-01-04 and 2024-05-24 | Continuing attacks on commercial shipping in the Red Sea and Gulf of Aden | **International scope only** (`Internacional` exact match) | Transport/logistics (`logistics_transport_category`) | Campaign start 2024-01-04 to **2024-11-20** (180 days after the second official record) | Adds dated official shipping-security context to international transport and logistics notices | Route use and operational effects require route, contract or company evidence; the two updates count as one campaign |

## New `external_events.csv` fields (extends the 13-field evidence contract)

`event_campaign_id`, `campaign_start_date`, `campaign_end_date`,
`campaign_validity_source_url` — the last field distinguishes a finite,
unextended window (points at the same single source) from a documented
ongoing campaign (points at the later record that confirms continuation).
