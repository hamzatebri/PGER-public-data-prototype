# Evidence Policy

## Accepted evidence

The main portfolio uses awarded public-procurement records from the BOE dataset released at Zenodo record 18712463. This is a secondary public dataset containing observed fields such as contracting institution, date, procedure, CPV information, awarded value, awardee name, and the BOE source link.

The analytical unit is a public-procurement exposure: an awarded contract characterised by its contracting authority, awardee, category, value, timing, and available geography. The awardee is an economic operator in a public contract. It is not automatically treated as a verified upstream supplier, importer, manufacturer, or private-SME supplier.

## Rejected evidence for headline findings

Synthetic, generated, manually constructed, or unverified company-risk fields cannot support claims about real supplier risk. They may be retained for debugging or historical comparison, but they must not appear as current results, headline figures, or validation evidence.

## Terminology rule

Use `procurement exposure`, `awardee`, `buyer-awardee relationship`, and `review priority`. Avoid presenting a public contract as proof of a private supply-chain dependency. Do not infer supplier country, route, lead time, inventory, backup availability, sanctions, or failure likelihood from an awardee name.

## Evaluation rule

Development and validation data may be used for refinement. The final test set must remain unseen until the configuration is frozen and must be evaluated once. Improvements suggested by final-test errors belong in future work unless a new independent test set is created.

The current 14-record event-family exercise is a selected development sample, not a final test set. It checks whether the three definitions and structured output can be applied to those examples. No accuracy claim is made for new records.
