"""Generates template-based synthetic captions with guaranteed-correct entity
labels, supplementing the real-corpus weak-labeled set.

Why: the real corpus (Waterfront/social-media-captions-20k) skews toward one
hashtag-heavy sports-fan community and is sparse in the routine/location
language this app actually targets (streets, times-of-day, recurring
activities). These synthetic examples are 100% correctly labeled by
construction -- no regex noise -- so they're folded into *training* only,
never into eval: the hand-corrected gold set stays the sole source of truth
for how well the model actually performs.

Usage (from backend/ml_training/):
    venv/Scripts/python.exe -m ner.generate_synthetic
"""

from __future__ import annotations

import itertools
import json
import random
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BACKEND_ROOT))
from app.services.entity_extraction import (  # noqa: E402
    ACTIVITY_KEYWORDS,
    BUSINESSES,
    KNOWN_STREETS,
    TIME_KEYWORDS,
)

from ner.label_schema import entities_to_bio  # noqa: E402

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "ner" / "synthetic.jsonl"
N_EXAMPLES = 2000
SEED = 42

TEMPLATES = [
    "Grabbing {activity} on {street} this {time}",
    "{time} {activity} at {business} on {street}",
    "Another {time} at {business}, same {activity} as always",
    "Caught the {activity} near {street} {time}",
    "{business} run before {activity}, {time} routine",
    "Heading to {street} for {activity} {time}",
    "{time} walk past {business}, grabbing {activity}",
    "Same {street} corner, same {time} {activity}",
]


def _generate(n: int) -> list[dict]:
    rng = random.Random(SEED)
    combos = list(itertools.product(TEMPLATES, KNOWN_STREETS, BUSINESSES, list(TIME_KEYWORDS), ACTIVITY_KEYWORDS))
    rng.shuffle(combos)

    rows = []
    for template, street, business, time_kw, activity in combos[:n]:
        text = template.format(
            activity=activity,
            street=street.title(),
            business=business.title(),
            time=time_kw,
        )
        entities = {
            "streets": [street.title()],
            "businesses": [business.title()],
            "times": [time_kw],
            "activities": [activity],
        }
        words, tags = entities_to_bio(text, entities)
        if not words:
            continue
        rows.append({"text": text, "tokens": words, "tags": tags})
    return rows


def main() -> None:
    rows = _generate(N_EXAMPLES)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"Wrote {len(rows)} synthetic examples -> {OUT_PATH}")
    print("(No LANDMARK examples here -- entity_extraction.py has no concrete")
    print(" place-name list to template from, only suffix patterns. LANDMARK")
    print(" training signal currently comes only from the real corpus.)")


if __name__ == "__main__":
    main()
