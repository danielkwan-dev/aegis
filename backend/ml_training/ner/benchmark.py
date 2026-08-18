"""Regex baseline vs. base (untrained head) DistilBERT vs. fine-tuned
DistilBERT vs. fine-tuned quantized DistilBERT, entity-level F1 on the
held-out hand-corrected gold set. This is the comparison table that goes in
the README -- it's what proves the fine-tuning (and quantization) steps are
earning their complexity rather than just adding moving parts.

Usage (from backend/ml_training/):
    venv/Scripts/python.exe -m ner.benchmark
"""

from __future__ import annotations

import json
import sys
import time
from contextlib import nullcontext
from pathlib import Path

import numpy as np
import torch
from seqeval.metrics import classification_report, f1_score
from transformers import AutoModelForTokenClassification, AutoTokenizer

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_BACKEND_ROOT))
from app.services.entity_extraction import extract_entities  # noqa: E402

from ner.label_schema import LABEL_LIST, entities_to_bio  # noqa: E402

MODEL_NAME = "distilbert-base-uncased"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "ner"
FINE_TUNED_DIR = Path(__file__).resolve().parent.parent / "models" / "ner-distilbert" / "final"
QUANTIZED_DIR = Path(__file__).resolve().parent.parent / "models" / "ner-distilbert" / "onnx-quantized"


def _load_gold() -> list[dict]:
    path = DATA_DIR / "hand_corrected.jsonl"
    if not path.exists():
        raise SystemExit(f"{path} not found -- run build_weak_labels.py + apply_corrections.py first.")
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def _regex_predictions(gold: list[dict]) -> list[list[str]]:
    preds = []
    for row in gold:
        entities = extract_entities(row["text"])
        _, tags = entities_to_bio(row["text"], entities)
        preds.append(tags)
    return preds


def _predict_with_model(model, tokenizer, gold: list[dict]) -> tuple[list[list[str]], float]:
    """Works for both a plain transformers model and an optimum ORTModel --
    both support model(**inputs) -> .logits and expose .config.id2label."""
    preds = []
    start = time.perf_counter()
    ctx = torch.no_grad() if isinstance(model, torch.nn.Module) else nullcontext()
    with ctx:
        for row in gold:
            tokenized = tokenizer(row["tokens"], is_split_into_words=True, truncation=True, return_tensors="pt")
            output = model(**tokenized)
            logits = output.logits
            logits = logits.detach().cpu().numpy() if hasattr(logits, "detach") else np.asarray(logits)
            pred_ids = logits[0].argmax(axis=-1).tolist()
            word_ids = tokenized.word_ids()

            word_tags = ["O"] * len(row["tokens"])
            seen = set()
            for token_idx, word_id in enumerate(word_ids):
                if word_id is None or word_id in seen:
                    continue
                seen.add(word_id)
                word_tags[word_id] = model.config.id2label.get(pred_ids[token_idx], "O")
            preds.append(word_tags)
    elapsed_ms = (time.perf_counter() - start) * 1000 / max(len(gold), 1)
    return preds, elapsed_ms


def main() -> None:
    gold = _load_gold()
    true_labels = [row["tags"] for row in gold]
    print(f"Evaluating on {len(gold)} hand-corrected gold examples\n")

    results: dict[str, tuple[list[list[str]], float | None]] = {}
    results["Regex baseline"] = (_regex_predictions(gold), None)

    if not FINE_TUNED_DIR.exists():
        print(f"(skipping model comparisons -- {FINE_TUNED_DIR} not found; run `python -m ner.train` first)\n")
    else:
        base_tok = AutoTokenizer.from_pretrained(MODEL_NAME)
        base_model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME, num_labels=len(LABEL_LIST))
        results["Base DistilBERT (untrained head)"] = _predict_with_model(base_model, base_tok, gold)

        ft_tok = AutoTokenizer.from_pretrained(str(FINE_TUNED_DIR))
        ft_model = AutoModelForTokenClassification.from_pretrained(str(FINE_TUNED_DIR))
        results["Fine-tuned DistilBERT"] = _predict_with_model(ft_model, ft_tok, gold)

        if QUANTIZED_DIR.exists():
            from optimum.onnxruntime import ORTModelForTokenClassification

            q_tok = AutoTokenizer.from_pretrained(str(QUANTIZED_DIR))
            q_model = ORTModelForTokenClassification.from_pretrained(str(QUANTIZED_DIR))
            results["Fine-tuned + ONNX int8 quantized"] = _predict_with_model(q_model, q_tok, gold)
        else:
            print(f"(skipping quantized row -- {QUANTIZED_DIR} not found; run `python -m ner.export_onnx` first)\n")

    print(f"{'Model':<38}{'Entity F1':>12}{'ms/example':>14}")
    print("-" * 64)
    for name, (preds, ms) in results.items():
        f1 = f1_score(true_labels, preds)
        ms_str = f"{ms:.1f}" if ms is not None else "n/a"
        print(f"{name:<38}{f1:>12.3f}{ms_str:>14}")

    if "Fine-tuned DistilBERT" in results:
        print("\n=== Fine-tuned DistilBERT -- full entity-level report ===")
        print(classification_report(true_labels, results["Fine-tuned DistilBERT"][0], digits=3))


if __name__ == "__main__":
    main()
