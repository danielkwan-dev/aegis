"""Downloads a Roboflow Universe dataset in YOLOv8 format via the official
`roboflow` SDK. Not hardcoded to one project -- works for any public
Roboflow Universe workspace/project/version. See DATASET.md for the
verified dataset this pipeline is built against.

Usage (from backend/ml_training/):
    venv/Scripts/python.exe -m vision.download_dataset \\
        --workspace storefront-detection \\
        --project store-front-signage-detection-ycolf \\
        --version 1 \\
        --api-key <your-free-roboflow-api-key>
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from roboflow import Roboflow

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "vision"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--api-key", default=os.environ.get("ROBOFLOW_API_KEY"))
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit(
            "No Roboflow API key. Pass --api-key or set ROBOFLOW_API_KEY "
            "(free account -> https://app.roboflow.com/settings/api)."
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rf = Roboflow(api_key=args.api_key)
    project = rf.workspace(args.workspace).project(args.project)
    dataset = project.version(args.version).download("yolov8", location=str(OUT_DIR / args.project))

    print(f"Downloaded -> {dataset.location}")
    print(f"data.yaml -> {dataset.location}/data.yaml")
    print("\nNext: venv/Scripts/python.exe -m vision.train --data "
          f"{dataset.location}/data.yaml")


if __name__ == "__main__":
    main()
