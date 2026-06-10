from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://aegis:aegis@localhost:5432/aegis"

    # If unset, resolved at runtime via shutil.which("tesseract") — no hardcoded install path.
    tesseract_cmd: str | None = None

    # Fine-tuned YOLOv8n signage/storefront detector (quantized ONNX). Unset
    # until the Colab training run in ml_training/vision/ has produced one —
    # the OCR cascade falls back to whole-image OCR until then.
    vision_model_path: str | None = None

    # Directory containing the fine-tuned DistilBERT NER model, exported to
    # ONNX + quantized (expects tokenizer.json + either model.onnx or
    # model_quantized.onnx inside -- optimum's ORTQuantizer names its output
    # the latter). Unset until the Colab training run in ml_training/ner/
    # has produced one — entity extraction falls back to regex until then.
    ner_model_dir: str | None = None

    session_cookie_name: str = "aegis_session_id"

    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
