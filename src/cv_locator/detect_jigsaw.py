#!/usr/bin/env python3
"""Shape-agnostic source/target localization for controlled slider puzzles."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class Outline:
    x: int
    y: int
    w: int
    h: int
    area: float
    contour: np.ndarray

    def compact(self) -> tuple[int, int, int, int, int]:
        return self.x, self.y, self.w, self.h, round(self.area)


def _bbox_iou(left: Outline, right: Outline) -> float:
    x1, y1 = max(left.x, right.x), max(left.y, right.y)
    x2 = min(left.x + left.w, right.x + right.w)
    y2 = min(left.y + left.h, right.y + right.h)
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    union = left.w * left.h + right.w * right.h - intersection
    return intersection / union if union else 0.0


def outline_components(image: np.ndarray) -> list[Outline]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 60, 160)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    height, width = image.shape[:2]
    raw: list[Outline] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        if (
            0.045 * width <= w <= 0.28 * width
            and 0.07 * height <= h <= 0.42 * height
            and area >= max(180, 0.00035 * width * height)
        ):
            raw.append(Outline(int(x), int(y), int(w), int(h), float(area), contour))

    # Canny yields inner and outer copies of an outline. Collapse those copies
    # so a duplicated edge cannot be selected as a source/target pair.
    candidates: list[Outline] = []
    for item in sorted(raw, key=lambda candidate: candidate.area, reverse=True):
        if any(_bbox_iou(item, kept) >= 0.82 for kept in candidates):
            continue
        candidates.append(item)
    return sorted(candidates, key=lambda item: (item.x, item.y, item.w, item.h))


def select_pair(candidates: list[Outline], shape: tuple[int, ...]):
    height, width = shape[:2]
    pairs = []
    for left in candidates:
        lx, ly, lw, lh, la = left.x, left.y, left.w, left.h, left.area
        lcx, lcy = lx + lw / 2, ly + lh / 2
        if lcx > 0.35 * width:
            continue
        for right in candidates:
            rx, ry, rw, rh, ra = right.x, right.y, right.w, right.h, right.area
            rcx, rcy = rx + rw / 2, ry + rh / 2
            if rcx - lcx < 0.18 * width:
                continue
            row_error = abs(lcy - rcy) / height
            size_error = abs(max(lw, lh) - max(rw, rh)) / max(max(lw, lh), max(rw, rh))
            area_error = abs(la - ra) / max(la, ra)
            if row_error > 0.10 or size_error > 0.30:
                continue
            # Hu-moment contour comparison is invariant to translation, scale,
            # and rotation. No circle/triangle/square/jigsaw classifier is used.
            shape_error = min(float(cv2.matchShapes(
                left.contour, right.contour, cv2.CONTOURS_MATCH_I1, 0.0
            )), 5.0)
            score = 4.0 * row_error + 2.5 * size_error + area_error + shape_error
            pairs.append((score, shape_error, left, right))
    if not pairs:
        raise RuntimeError(
            f"no paired puzzle outlines found; candidates={[item.compact() for item in candidates]}"
        )
    score, shape_error, piece, gap = min(pairs, key=lambda item: item[0])
    return piece, gap, score, shape_error


def locate(image: np.ndarray) -> dict:
    # A panel may include the slider beneath the photographic challenge. The
    # upper 82% excludes it while retaining the whole puzzle image.
    analysis = image[:round(image.shape[0] * 0.82)] if image.shape[0] / image.shape[1] > 0.62 else image
    candidates = outline_components(analysis)
    piece, gap, pair_score, shape_error = select_pair(candidates, analysis.shape)
    px, py, pw, ph, _ = piece.compact()
    gx, gy, gw, gh, _ = gap.compact()
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
        "pair_score": round(pair_score, 4),
        "shape_match_error": round(shape_error, 4),
        "detection_method": "shape_agnostic_paired_outline",
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
