"""Reads the hand-corrected for_review.csv and regenerates BIO tags from the
edited entity lists.

Reuses entities_to_bio() -- the exact same conversion function
build_weak_labels.py used -- so corrected rows are tagged with identical
logic to the weak-labeled set. This is the gold set: used both as a
fine-tuning quality boost and as the held-out eval set for the
regex-vs-model benchmark.

Usage (from backend/ml_training/):
    venv/Scripts/python.exe -m ner.apply_corrections
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from ner.label_schema import entities_to_bio

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "ner"
REVIEW_CSV = DATA_DIR / "for_review.csv"
OUT_PATH = DATA_DIR / "hand_corrected.jsonl"

COLUMN_TO_CATEGORY = {
    "streets": "streets",
    "landmarks": "places",
    "businesses": "businesses",
    "times": "times",
    "activities": "activities",
}


def _split_cell(cell: str) -> list[str]:
    return [v.strip() for v in cell.split(";") if v.strip()]


def main() -> None:
    if not REVIEW_CSV.exists():
        raise SystemExit(f"{REVIEW_CSV} not found -- run build_weak_labels.py first.")

    rows = []
    skipped = 0
    with REVIEW_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            text = row["text"]
            entities = {category: _split_cell(row[column]) for column, category in COLUMN_TO_CATEGORY.items()}
            words, tags = entities_to_bio(text, entities)
            if not words:
                skipped += 1
                continue
            rows.append({"text": text, "tokens": words, "tags": tags})

    with OUT_PATH.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    print(f"Wrote {len(rows)} hand-corrected gold examples -> {OUT_PATH}")
    if skipped:
        print(f"({skipped} rows skipped -- empty text)")


if __name__ == "__main__":
    main()
