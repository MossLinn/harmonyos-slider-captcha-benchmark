#!/usr/bin/env python3
"""Measure puzzle-location error under deterministic screenshot perturbations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from detect_puzzle import canvas_bounds, locate


def perturb(image: np.ndarray, scale: float, brightness: int, blur: int, jpeg: int) -> np.ndarray:
    changed = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
    changed = np.clip(changed.astype(np.int16) + brightness, 0, 255).astype(np.uint8)
    if blur:
        changed = cv2.GaussianBlur(changed, (blur, blur), 0)
    ok, encoded = cv2.imencode(".jpg", changed, [cv2.IMWRITE_JPEG_QUALITY, jpeg])
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return cv2.imdecode(encoded, cv2.IMREAD_COLOR)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--ground-truth", type=float, default=72.0)
    args = parser.parse_args()

    screenshot = cv2.imread(str(args.image))
    x1, y1, x2, y2 = canvas_bounds(args.layout)
    crop = screenshot[y1:y2, x1:x2]
    cases, failures = [], []
    for scale in (0.75, 1.0, 1.25):
        for brightness in (-25, 0, 25):
            for blur in (0, 3):
                for jpeg in (70, 95):
                    name = f"scale={scale},brightness={brightness},blur={blur},jpeg={jpeg}"
                    try:
                        result = locate(perturb(crop, scale, brightness, blur, jpeg))
                        error = abs(result["target_percent"] - args.ground_truth)
                        cases.append({"case": name, "prediction": result["target_percent"], "absolute_error": round(error, 2)})
                    except Exception as exc:
                        failures.append({"case": name, "error": str(exc)})

    errors = [case["absolute_error"] for case in cases]
    report = {
        "ground_truth_percent": args.ground_truth,
        "total_cases": len(cases) + len(failures),
        "successful_detections": len(cases),
        "detection_rate": round(len(cases) / (len(cases) + len(failures)), 4),
        "mean_absolute_error": round(float(np.mean(errors)), 3) if errors else None,
        "max_absolute_error": round(float(np.max(errors)), 3) if errors else None,
        "within_1_percent_rate": round(sum(e <= 1 for e in errors) / len(errors), 4) if errors else 0,
        "cases": cases,
        "failures": failures,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
