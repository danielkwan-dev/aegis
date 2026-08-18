"""Fine-tunes DistilBERT for token classification on the weak + hand-corrected
NER data built by build_weak_labels.py / apply_corrections.py.

Meant to run on a GPU (a free Colab T4 is enough for this model/data size)
-- see ../COLAB.md for the exact steps. Nothing here is Colab-specific
though; it runs anywhere with the deps installed.

Usage (from backend/ml_training/):
    venv/Scripts/python.exe -m ner.train
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from datasets import Dataset
from seqeval.metrics import classification_report, f1_score
from transformers import (
    AutoModelForTokenClassification,
    AutoTokenizer,
    DataCollatorForTokenClassification,
    Trainer,
    TrainingArguments,
)

from ner.label_schema import ID2LABEL, LABEL2ID, LABEL_LIST

MODEL_NAME = "distilbert-base-uncased"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "ner"
OUT_DIR = Path(__file__).resolve().parent.parent / "models" / "ner-distilbert"

MAX_LENGTH = 64
VAL_FRACTION = 0.1


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def _build_datasets() -> tuple[Dataset, Dataset, Dataset]:
    weak = _load_jsonl(DATA_DIR / "weak_labeled.jsonl")
    synthetic = _load_jsonl(DATA_DIR / "synthetic.jsonl")
    gold = _load_jsonl(DATA_DIR / "hand_corrected.jsonl")
    if not weak:
        raise SystemExit("No weak_labeled.jsonl found -- run `python -m ner.build_weak_labels` first.")
    if not gold:
        raise SystemExit(
            "No hand_corrected.jsonl found -- hand-correct data/ner/for_review.csv, "
            "then run `python -m ner.apply_corrections`. The gold set is the real "
            "eval signal here; training on weak labels alone isn't trustworthy."
        )

    # Gold examples are held out entirely as the test set -- must not leak
    # into train/val, that's what makes the held-out eval honest.
    gold_texts = {row["text"] for row in gold}
    weak_train_pool = [row for row in weak if row["text"] not in gold_texts]

    rng = np.random.default_rng(42)
    idx = rng.permutation(len(weak_train_pool))
    n_val = max(1, int(len(idx) * VAL_FRACTION))
    val_rows = [weak_train_pool[i] for i in idx[:n_val]]
    train_rows = [weak_train_pool[i] for i in idx[n_val:]]

    # Synthetic examples are 100% correctly labeled by construction -- they
    # go into training only, never val/test, so eval always reflects
    # real-world caption performance, not template performance.
    train_rows = train_rows + synthetic
    if synthetic:
        print(f"(+{len(synthetic)} synthetic examples folded into train split)")

    return Dataset.from_list(train_rows), Dataset.from_list(val_rows), Dataset.from_list(gold)


def _tokenize_and_align(tokenizer):
    def fn(batch):
        tokenized = tokenizer(
            batch["tokens"],
            truncation=True,
            max_length=MAX_LENGTH,
            is_split_into_words=True,
        )
        all_labels = []
        for i, tags in enumerate(batch["tags"]):
            word_ids = tokenized.word_ids(batch_index=i)
            label_ids = []
            prev_word_id = None
            for word_id in word_ids:
                if word_id is None:
                    label_ids.append(-100)
                elif word_id != prev_word_id:
                    label_ids.append(LABEL2ID[tags[word_id]])
                else:
                    # Non-first subword of a word is ignored in the loss.
                    label_ids.append(-100)
                prev_word_id = word_id
            all_labels.append(label_ids)
        tokenized["labels"] = all_labels
        return tokenized

    return fn


def _strip_ignored(predictions, label_ids):
    preds = np.argmax(predictions, axis=2)
    true_predictions = [
        [ID2LABEL[p] for p, l in zip(pred_row, label_row) if l != -100]
        for pred_row, label_row in zip(preds, label_ids)
    ]
    true_labels = [
        [ID2LABEL[l] for p, l in zip(pred_row, label_row) if l != -100]
        for pred_row, label_row in zip(preds, label_ids)
    ]
    return true_predictions, true_labels


def _compute_metrics(eval_pred):
    predictions, labels = eval_pred
    true_predictions, true_labels = _strip_ignored(predictions, labels)
    return {"f1": f1_score(true_labels, true_predictions)}


def main() -> None:
    train_ds, val_ds, test_ds = _build_datasets()
    print(f"train={len(train_ds)}  val={len(val_ds)}  test(gold, held out)={len(test_ds)}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_NAME, num_labels=len(LABEL_LIST), id2label=ID2LABEL, label2id=LABEL2ID,
    )

    tokenize_fn = _tokenize_and_align(tokenizer)
    train_tok = train_ds.map(tokenize_fn, batched=True, remove_columns=train_ds.column_names)
    val_tok = val_ds.map(tokenize_fn, batched=True, remove_columns=val_ds.column_names)
    test_tok = test_ds.map(tokenize_fn, batched=True, remove_columns=test_ds.column_names)

    collator = DataCollatorForTokenClassification(tokenizer)

    args = TrainingArguments(
        output_dir=str(OUT_DIR / "checkpoints"),
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=3e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        num_train_epochs=6,
        weight_decay=0.01,
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_tok,
        eval_dataset=val_tok,
        data_collator=collator,
        compute_metrics=_compute_metrics,
    )

    trainer.train()

    print("\n=== Held-out gold-set evaluation (entity-level, seqeval) ===")
    test_predictions = trainer.predict(test_tok)
    true_predictions, true_labels = _strip_ignored(test_predictions.predictions, test_predictions.label_ids)
    print(classification_report(true_labels, true_predictions, digits=3))

    final_dir = OUT_DIR / "final"
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    print(f"\nSaved fine-tuned model -> {final_dir}")
    print("Next: `python -m ner.export_onnx` to export + quantize for CPU serving,")
    print("and `python -m ner.benchmark` for the regex vs. base vs. quantized comparison.")


if __name__ == "__main__":
    main()
