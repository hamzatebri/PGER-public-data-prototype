"""Run the local event-family development exercise.

The request contains only public event text. Labels are never sent to the
model. The retained comparison checks the definitions and output format; it is
not a general performance estimate.
"""

from __future__ import annotations

import json
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from sklearn.metrics import confusion_matrix


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
LABELS = ROOT / "data" / "evaluation" / "researcher_event_labels.csv"
OUTPUT = ROOT / "outputs" / "evaluation" / "local_llm_evaluation.json"
BASE_URL = os.environ.get("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
MODEL = os.environ.get("LM_STUDIO_MODEL", "openai/gpt-oss-20b")
CLASSES = ["trade_policy", "logistics_transport", "conflict_security"]
PROMPT_VERSION = "event-family-v1"

SYSTEM_PROMPT = """Classify one public event into exactly one event family.

Definitions:
- trade_policy: sanctions, tariffs, export controls, import restrictions, or trade regulation.
- logistics_transport: non-violent transport capacity, route, port, canal, shipping, or transit constraints.
- conflict_security: attacks, piracy, war, armed conflict, military action, or physical security threats.

When an event mentions both an attack and shipping, choose conflict_security because the attack is the main cause.
Return only JSON matching the requested schema."""


def classify(title: str, summary: str) -> str:
    payload = {
        "model": MODEL,
        "temperature": 0,
        "seed": 42,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Title: {title}\nSummary: {summary}"},
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
    response = requests.post(
        f"{BASE_URL}/chat/completions",
        json=payload,
        headers={"Authorization": "Bearer lm-studio"},
        timeout=180,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    value = json.loads(content)["event_family"]
    if value not in CLASSES:
        raise ValueError(f"Unsupported model output: {value}")
    return value


def main() -> None:
    labels = pd.read_csv(LABELS, dtype=str).fillna("")
    if not labels["label_event_family"].isin(CLASSES).all():
        raise ValueError("The frozen annotation file contains an unsupported event family.")

    labels["local_llm_prediction"] = [
        classify(row.record_title, row.plain_summary) for row in labels.itertuples()
    ]
    target = labels["label_event_family"].tolist()
    prediction = labels["local_llm_prediction"].tolist()
    matrix = confusion_matrix(target, prediction, labels=CLASSES)
    agreement_count = sum(expected == observed for expected, observed in zip(target, prediction))
    result = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "labels_sha256": hashlib.sha256(LABELS.read_bytes()).hexdigest(),
        "sample_size": len(labels),
        "exercise_type": "development_sample",
        "annotation_status": "researcher-created labels for selected official records",
        "model": MODEL,
        "backend": "LM Studio local server at 127.0.0.1:1234",
        "prompt_version": PROMPT_VERSION,
        "temperature": 0,
        "seed": 42,
        "labels_sent_to_model": False,
        "classes": CLASSES,
        "agreement_count": agreement_count,
        "confusion_matrix": matrix.tolist(),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    labels.to_csv(OUTPUT.with_suffix(".csv"), index=False)
    print(f"Evaluated {len(labels)} public records with {MODEL}")
    print(f"Model labels matching the prepared labels: {agreement_count} of {len(labels)} selected examples")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
