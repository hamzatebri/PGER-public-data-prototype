# Public-Event Development Sample Protocol

## Purpose

This file documents the 14 selected official records used to check whether the three PGER event-family definitions and the structured local-model output work as intended. The sample is separate from the BOE portfolio, the structural score and the four-record event-context registry.

## Files

`data/evaluation/public_event_development_sample.csv` contains the source fields used in the exercise. `data/evaluation/researcher_event_labels.csv` contains the researcher's completed labels. The source records do not contain a PGER score or model output.

## Label definitions

| Column | Allowed values | Definition |
|---|---|---|
| `label_relevant_to_observed_portfolio` | `yes`, `no`, `unclear` | Whether the source could justify reviewing at least one category in the declared public portfolio. |
| `label_event_family` | `trade_policy`, `logistics_transport`, `conflict_security`, `other`, `unclear` | The main event type stated by the source. |
| `label_category_proxy` | BOE sector group, `cross_category`, `none`, `unclear` | The closest public procurement category, without inferring a private supply relationship. |
| `label_confidence` | `high`, `medium`, `low` | The researcher's confidence after checking the original source. |
| `reviewer_notes` | Free text | The source detail that supports the label. |

## Interpretation

The records were selected to cover the three defined event families and do not include an irrelevant control class. The model comparison therefore demonstrates development-sample consistency only. A performance estimate requires a new independently sampled dataset, an irrelevant class, independent labels and a final test partition that remains unseen until the method is fixed.
