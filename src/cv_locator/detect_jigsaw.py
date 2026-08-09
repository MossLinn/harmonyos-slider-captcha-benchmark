#!/usr/bin/env python3
"""Locate paired jigsaw outlines in a controlled slider-challenge image."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def outline_components(image: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 60, 160)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    height, width = image.shape[:2]
    candidates = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        if (
            0.08 * width <= w <= 0.23 * width
            and 0.13 * height <= h <= 0.38 * height
            and area >= 500
        ):
            candidates.append((int(x), int(y), int(w), int(h), int(area)))
    return sorted(set(candidates), key=lambda box: (box[0], box[1], box[2], box[3]))


def select_pair(candidates: list[tuple[int, int, int, int, int]], shape: tuple[int, ...]):
    height, width = shape[:2]
    pairs = []
    for left in candidates:
        lx, ly, lw, lh, la = left
        lcx, lcy = lx + lw / 2, ly + lh / 2
        if lcx > 0.28 * width:
            continue
        for right in candidates:
            rx, ry, rw, rh, ra = right
            rcx, rcy = rx + rw / 2, ry + rh / 2
            if rcx - lcx < 0.18 * width:
                continue
            row_error = abs(lcy - rcy) / height
            size_error = abs(max(lw, lh) - max(rw, rh)) / max(max(lw, lh), max(rw, rh))
            area_error = abs(la - ra) / max(la, ra)
            if size_error > 0.24:
                continue
            # Direct drag-and-drop targets may be above or below the source.
            # Geometry similarity dominates; row alignment is only a weak tie-breaker.
            score = 0.5 * row_error + 5 * size_error + area_error
            pairs.append((score, left, right))
    if not pairs:
        raise RuntimeError(f"no paired jigsaw outlines found; candidates={candidates}")
    _, piece, gap = min(pairs, key=lambda item: item[0])
    return piece, gap


def locate(image: np.ndarray) -> dict:
    # A panel may include the slider beneath the photographic challenge. The
    # upper 82% safely excludes it while retaining the whole puzzle image.
    analysis = image[:round(image.shape[0] * 0.82)] if image.shape[0] / image.shape[1] > 0.62 else image
    candidates = outline_components(analysis)
    piece, gap = select_pair(candidates, analysis.shape)
    px, py, pw, ph, _ = piece
    gx, gy, gw, gh, _ = gap
    piece_center = px + pw / 2
    gap_center = gx + gw / 2
    nominal_side = max(pw, ph, gw, gh)
    available_travel = analysis.shape[1] - nominal_side / 2 - piece_center
    target = 100 * (gap_center - piece_center) / available_travel
    return {
        "piece_bbox": [px, py, pw, ph],
        "gap_bbox": [gx, gy, gw, gh],
        "piece_center_x": round(piece_center, 2),
        "gap_center_x": round(gap_center, 2),
        "drag_pixels": round(gap_center - piece_center, 2),
        "available_travel_pixels": round(available_travel, 2),
        "target_percent": round(target, 2),
        "candidate_count": len(candidates),
        "detection_method": "paired_jigsaw_outline",
    }


def annotate(image: np.ndarray, result: dict) -> np.ndarray:
    output = image.copy()
    for key, color, label in (
        ("piece_bbox", (0, 220, 0), "piece"),
        ("gap_bbox", (0, 80, 255), "gap"),
    ):
        x, y, w, h = result[key]
        cv2.rectangle(output, (x, y), (x + w, y + h), color, 3)
        cv2.putText(output, label, (x, max(25, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--annotated", type=Path)
    args = parser.parse_args()
    image = cv2.imread(str(args.image))
    if image is None:
        raise FileNotFoundError(args.image)
    result = locate(image)
    if args.annotated:
        args.annotated.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(args.annotated), annotate(image, result))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
