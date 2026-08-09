#!/usr/bin/env python3
"""Locate the movable piece and gap in the controlled HarmonyOS puzzle benchmark."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import cv2
import numpy as np


BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def walk(node: dict):
    yield node
    for child in node.get("children", []):
        yield from walk(child)


def canvas_bounds(layout_path: Path) -> tuple[int, int, int, int]:
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    canvases = [
        node for node in walk(layout)
        if node.get("attributes", {}).get("type") == "Canvas"
    ]
    if len(canvases) != 1:
        raise ValueError(f"expected exactly one Canvas, found {len(canvases)}")
    raw = canvases[0]["attributes"]["bounds"]
    match = BOUNDS.fullmatch(raw)
    if not match:
        raise ValueError(f"invalid Canvas bounds: {raw}")
    return tuple(map(int, match.groups()))


def square_components(image: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    """Find square borders by geometry instead of assuming a plain background."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 70, 170)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    height, width = image.shape[:2]
    result = []
    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        polygon = cv2.approxPolyDP(contour, 0.025 * perimeter, True)
        if len(polygon) != 4 or not cv2.isContourConvex(polygon):
            continue
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        aspect = w / max(h, 1)
        if (
            0.75 <= aspect <= 1.25
            and 0.16 * height <= h <= 0.42 * height
            and 0.06 * width <= w <= 0.25 * width
            and area >= 0.55 * w * h
        ):
            result.append((int(x), int(y), int(w), int(h), int(area)))
    # Canny commonly returns the two sides of the same border. Keep both: pair
    # selection below can match inner-to-inner or outer-to-outer consistently.
    return sorted(set(result), key=lambda box: (box[0], box[1], box[2]))


def bright_square_components(image: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    """Fallback for borders whose edge is interrupted by detailed imagery."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    value = hsv[:, :, 2]
    threshold = max(150, int(np.percentile(value, 98)) - 18)
    mask = cv2.inRange(
        hsv,
        np.array((0, 0, threshold), np.uint8),
        np.array((179, 65, 255), np.uint8),
    )
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    height, width = image.shape[:2]
    result = []
    for x, y, w, h, area in stats[1:count]:
        if (
            0.75 <= w / max(h, 1) <= 1.25
            and 0.16 * height <= h <= 0.42 * height
            and 0.06 * width <= w <= 0.25 * width
            and area >= 0.04 * w * h
        ):
            result.append((int(x), int(y), int(w), int(h), int(area)))
    return sorted(result, key=lambda box: box[0])


def select_pair(boxes: list[tuple[int, int, int, int, int]], shape: tuple[int, ...]):
    height, width = shape[:2]
    pairs = []
    for index, left in enumerate(boxes):
        lx, ly, lw, lh, _ = left
        left_center_x = lx + lw / 2
        left_center_y = ly + lh / 2
        if left_center_x > 0.30 * width:
            continue
        for right in boxes[index + 1:]:
            rx, ry, rw, rh, _ = right
            right_center_x = rx + rw / 2
            right_center_y = ry + rh / 2
            separation = right_center_x - left_center_x
            if separation < 0.18 * width:
                continue
            size_error = abs(lw - rw) / max(lw, rw) + abs(lh - rh) / max(lh, rh)
            row_error = abs(left_center_y - right_center_y) / height
            if size_error > 0.28 or row_error > 0.08:
                continue
            # Equal-sized, row-aligned squares dominate. A weak prior favors the
            # benchmark's initial piece near the left edge without fixing pixels.
            start_error = abs(left_center_x / width - 0.117)
            score = 4 * size_error + 5 * row_error + start_error
            pairs.append((score, left, right))
    if not pairs:
        raise RuntimeError(f"could not pair square contours; candidates={boxes}")
    _, left, right = min(pairs, key=lambda item: item[0])
    return left, right


def locate(crop: np.ndarray) -> dict:
    boxes = square_components(crop)
    method = "edge_geometry"
    try:
        piece, gap = select_pair(boxes, crop.shape)
    except RuntimeError:
        boxes = bright_square_components(crop)
        if len(boxes) < 2:
            raise RuntimeError(f"could not find piece and gap; square candidates={boxes}")
        try:
            piece, gap = select_pair(boxes, crop.shape)
        except RuntimeError:
            piece, gap = boxes[0], boxes[-1]
        method = "bright_component_fallback"
    px, py, pw, ph, _ = piece
    gx, gy, gw, gh, _ = gap
    piece_center = px + pw / 2
    gap_center = gx + gw / 2
    # The piece starts at the leftmost position. Its available travel ends when
    # its right edge reaches the canvas edge.
    available_travel = crop.shape[1] - pw - px
    target_percent = 100.0 * (gap_center - piece_center) / available_travel
    return {
        "piece_bbox": [px, py, pw, ph],
        "gap_bbox": [gx, gy, gw, gh],
        "piece_center_x": round(piece_center, 2),
        "gap_center_x": round(gap_center, 2),
        "drag_pixels": round(gap_center - piece_center, 2),
        "available_travel_pixels": round(available_travel, 2),
        "target_percent": round(target_percent, 2),
        "candidate_count": len(boxes),
        "detection_method": method,
    }


def annotate(image: np.ndarray, bounds: tuple[int, int, int, int], result: dict) -> np.ndarray:
    output = image.copy()
    x1, y1, _, _ = bounds
    for key, color, label in (
        ("piece_bbox", (0, 220, 0), "piece"),
        ("gap_bbox", (0, 80, 255), "gap"),
    ):
        x, y, w, h = result[key]
        a, b = (x1 + x, y1 + y), (x1 + x + w, y1 + y + h)
        cv2.rectangle(output, a, b, color, 4)
        cv2.putText(output, label, (a[0], a[1] - 12), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--annotated", type=Path)
    args = parser.parse_args()

    image = cv2.imread(str(args.image))
    if image is None:
        raise FileNotFoundError(args.image)
    bounds = canvas_bounds(args.layout)
    x1, y1, x2, y2 = bounds
    result = locate(image[y1:y2, x1:x2])
    result["canvas_bounds"] = list(bounds)
    if args.annotated:
        args.annotated.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(args.annotated), annotate(image, bounds, result))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
