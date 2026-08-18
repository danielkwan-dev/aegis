# Running the training steps on Colab

Everything in `ml_training/` runs locally except the two actual GPU fine-tuning
runs (`ner/train.py`, and later the YOLOv8n vision training) -- those need a
GPU this laptop doesn't have. Steps below assume a free Colab T4 runtime.

## NER (DistilBERT) fine-tuning

1. **Prep locally first** (no GPU needed for this part):
   ```
   cd backend/ml_training
   venv/Scripts/python.exe -m ner.build_weak_labels
   ```
   This downloads `Waterfront/social-media-captions-20k` (MIT-licensed, text-only)
   and produces:
   - `data/ner/weak_labeled.jsonl` -- 6,000 auto-labeled examples
   - `data/ner/for_review.csv` -- 400 examples sampled for hand-correction

   That corpus turned out to skew heavily toward one hashtag-heavy sports-fan
   community and is sparse in the routine/location language this app
   actually targets, so also run:
   ```
   venv/Scripts/python.exe -m ner.generate_synthetic
   ```
   which writes `data/ner/synthetic.jsonl` -- 2,000 template-generated
   examples with guaranteed-correct labels (train.py folds these into the
   train split only, never eval, so held-out numbers always reflect
   real-caption performance).

2. **Hand-correct** `data/ner/for_review.csv` in Excel/Sheets/etc. Each
   category column (`streets`, `landmarks`, `businesses`, `times`,
   `activities`) is semicolon-separated -- fix what the regex extractor got
   wrong or missed. Then:
   ```
   venv/Scripts/python.exe -m ner.apply_corrections
   ```
   This produces `data/ner/hand_corrected.jsonl` -- the gold eval set.

3. **Commit both jsonl files** (they're real project artifacts, not
   regeneratable build output -- your hand corrections are the point).

4. **On Colab**, in a fresh notebook:
   ```python
   !git clone https://github.com/danielkwan-dev/aegis.git
   %cd aegis/backend/ml_training
   !pip install -q datasets transformers accelerate seqeval optimum[onnxruntime]

   !python -m ner.train          # the actual GPU fine-tuning run
   !python -m ner.export_onnx    # ONNX export + int8 quantization (CPU is fine for this step)
   !python -m ner.benchmark      # regex vs base vs fine-tuned vs quantized comparison
   ```

5. **Download the results** from Colab (`models/ner-distilbert/onnx-quantized/`
   and the benchmark output) back to this machine, or push the quantized
   model straight to Hugging Face Hub from within the Colab session:
   ```python
   from huggingface_hub import HfApi
   HfApi().upload_folder(
       folder_path="models/ner-distilbert/onnx-quantized",
       repo_id="<your-hf-username>/aegis-ner-distilbert",
       repo_type="model",
   )
   ```

6. Point the serving app's model-loading code at that Hugging Face repo ID
   (wired up in the "detect->crop->preprocess->OCR->NER cascade" step).

## Vision (YOLOv8n) fine-tuning

Dataset: see `vision/DATASET.md` -- v1 is storefront/business-sign
detection (788 images, verified CC BY 4.0 dataset); street-name-sign
detection is a documented v2 addition, not yet built.

1. **Get a free Roboflow API key**: https://app.roboflow.com/settings/api

2. **On Colab**, in a fresh notebook (GPU runtime):
   ```python
   !git clone https://github.com/danielkwan-dev/aegis.git
   %cd aegis/backend/ml_training
   !pip install -q roboflow ultralytics onnxruntime

   !python -m vision.download_dataset \
       --workspace storefront-detection \
       --project store-front-signage-detection-ycolf \
       --version 1 \
       --api-key YOUR_ROBOFLOW_KEY

   !python -m vision.train --data data/vision/store-front-signage-detection-ycolf/data.yaml
   ```

3. **Download the results** (`models/vision-yolov8n/finetune/weights/best.pt`
   and the quantized ONNX) or push straight to Hugging Face Hub the same way
   as the NER model (see the `HfApi().upload_folder(...)` snippet above).

4. Point the serving app's vision service at that model, wired up as part of
   the detect->crop->preprocess->OCR->NER cascade.
