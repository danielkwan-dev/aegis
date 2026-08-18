"""Bootstraps weak NER training labels from the existing regex extractor.

Pulls a public Instagram-caption dataset, runs the hackathon-era regex
entity extractor (app.services.entity_extraction.extract_entities) over
each caption, and converts the matches into token-level BIO tags. This is
noisy by construction -- regex misses things and false-positives things --
which is exactly why a hand-corrected subset (for_review.csv ->
apply_corrections.py) exists as both a fine-tuning quality boost and the
real held-out eval set for the regex-vs-model benchmark.

Usage (from backend/ml_training/):
    venv/Scripts/python.exe -m ner.build_weak_labels
"""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

# Reuse the actual serving-app regex extractor -- this *is* the baseline
# we're bootstrapping from and later benchmarking against, so it must be the
# real thing, not a reimplementation that could quietly drift from it.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]  # backend/
sys.path.insert(0, str(_BACKEND_ROOT))
from app.services.entity_extraction import extract_entities  # noqa: E402

from ner.label_schema import entities_to_bio  # noqa: E402

from datasets import load_dataset  # noqa: E402

DATASET_NAME = "Waterfront/social-media-captions-20k"
SAMPLE_SIZE = 6000
REVIEW_SAMPLE_SIZE = 400
MIN_CAPTION_LEN = 15
SEED = 42

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "ner"


ASSISTANT_MARKER = "### Assistant:"


def _extract_caption(raw_text: str) -> str:
    """This dataset's `text` field is an instruction-template wrapper:
    "### Human: Write a social media photo caption based on this photo
    description: <desc>  ### Assistant: <actual caption>" -- we only want
    the caption itself, not the instruction template around it.
    """
    if ASSISTANT_MARKER not in raw_text:
        return ""
    return raw_text.split(ASSISTANT_MARKER, 1)[1].strip()


def _clean_captions() -> list[str]:
    # Text-only, modern Parquet dataset (MIT licensed) -- no image payload
    # to prune around, so a plain load is already fast.
    ds = load_dataset(DATASET_NAME, split="train")

    captions: list[str] = []
    seen: set[str] = set()
    for row in ds:
        text = _extract_caption(row.get("text") or "")
        if len(text) < MIN_CAPTION_LEN or text in seen:
            continue
        seen.add(text)
        captions.append(text)
        if len(captions) >= SAMPLE_SIZE:
            break
    return captions


def _write_review_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "text", "streets", "landmarks", "businesses", "times", "activities"])
        for i, row in enumerate(rows):
            e = row["entities"]
            writer.writerow([
                i,
                row["text"],
                "; ".join(e.get("streets", [])),
                "; ".join(e.get("places", [])),
                "; ".join(e.get("businesses", [])),
                "; ".join(e.get("times", [])),
                "; ".join(e.get("activities", [])),
            ])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Pulling captions from {DATASET_NAME} (streaming, caption column only)...")
    captions = _clean_captions()
    print(f"  {len(captions)} unique captions >= {MIN_CAPTION_LEN} chars")

    weak_labeled = []
    for text in captions:
        entities = extract_entities(text)
        words, tags = entities_to_bio(text, entities)
        if not words:
            continue
        weak_labeled.append({"text": text, "tokens": words, "tags": tags, "entities": entities})

    has_entities = [r for r in weak_labeled if any(t != "O" for t in r["tags"])]
    print(f"  {len(has_entities)} / {len(weak_labeled)} contain at least one non-O tag "
          f"({len(has_entities) / max(len(weak_labeled), 1):.1%})")

    weak_path = OUT_DIR / "weak_labeled.jsonl"
    with weak_path.open("w", encoding="utf-8") as f:
        for row in weak_labeled:
            f.write(json.dumps({"text": row["text"], "tokens": row["tokens"], "tags": row["tags"]}) + "\n")
    print(f"Wrote {len(weak_labeled)} weak-labeled examples -> {weak_path}")

    # Sample a subset for hand-correction. Oversample examples that already
    # have at least one entity -- reviewing all-O captions teaches a human
    # reviewer nothing about entity boundaries.
    random.seed(SEED)
    without = [r for r in weak_labeled if r not in has_entities]
    n_with = int(REVIEW_SAMPLE_SIZE * 0.8)
    n_without = REVIEW_SAMPLE_SIZE - n_with
    pool = random.sample(has_entities, min(n_with, len(has_entities))) + \
        random.sample(without, min(n_without, len(without)))
    random.shuffle(pool)

    review_path = OUT_DIR / "for_review.csv"
    _write_review_csv(pool, review_path)
    print(f"Wrote {len(pool)} examples for hand-correction -> {review_path}")
    print()
    print("Next: open that CSV (Excel/Sheets/etc.), correct the entity columns")
    print("(semicolon-separated per cell), save, then run:")
    print("    venv/Scripts/python.exe -m ner.apply_corrections")


if __name__ == "__main__":
    main()
