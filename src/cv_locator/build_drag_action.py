#!/usr/bin/env python3
"""Convert a CV target percentage into a HarmonyOS slider drag action."""

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


def slider_info(layout_path: Path) -> tuple[tuple[int, int, int, int], float]:
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    sliders = [node for node in walk(layout) if node.get("attributes", {}).get("type") == "Slider"]
    if len(sliders) != 1:
        raise ValueError(f"expected exactly one Slider, found {len(sliders)}")
    attrs = sliders[0]["attributes"]
    match = BOUNDS.fullmatch(attrs["bounds"])
    if not match:
        raise ValueError(f"invalid Slider bounds: {attrs['bounds']}")
    value = float(attrs.get("text") or attrs.get("originalText") or 0)
    return tuple(map(int, match.groups())), value


def detect_geometry(image: np.ndarray, bounds: tuple[int, int, int, int], current_percent: float) -> dict:
    x1, y1, x2, y2 = bounds
    crop = image[y1:y2, x1:x2]
    height, width = crop.shape[:2]

    # The ArkUI slider handle has a bright circular body. Ignore the much wider
    # near-white page background by requiring a roughly square component.
    bright = cv2.inRange(
        crop,
        np.array((248, 248, 248), np.uint8),
        np.array((255, 255, 255), np.uint8),
    )
    count, _, stats, centers = cv2.connectedComponentsWithStats(bright)
    handle_candidates = []
    for stat, center in zip(stats[1:count], centers[1:count]):
        x, y, w, h, area = stat
        if 0.55 * height <= w <= 1.10 * height and 0.55 * height <= h <= 1.10 * height and 0.75 <= w / h <= 1.25:
            handle_candidates.append((int(area), float(center[0]), float(center[1]), [int(x), int(y), int(w), int(h)]))
    if not handle_candidates:
        raise RuntimeError("slider handle was not detected")
    _, handle_x_local, handle_y_local, handle_bbox = max(handle_candidates)

    # Gray track and handle shadow form a wide low-saturation component. Its
    # rightmost point is the maximum handle-center position for this ArkUI style.
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    gray = cv2.inRange(
        hsv,
        np.array((0, 0, 185), np.uint8),
        np.array((179, 40, 242), np.uint8),
    )
    count, _, stats, _ = cv2.connectedComponentsWithStats(gray)
    wide = [stat for stat in stats[1:count] if stat[2] >= 0.55 * width]
    if not wide:
        raise RuntimeError("slider track was not detected")
    track_component = max(wide, key=lambda stat: stat[2])
    track_right_local = float(track_component[0] + track_component[2] - 1)

    current_ratio = max(0.0, min(1.0, current_percent / 100.0))
    if current_ratio >= 0.98:
        raise ValueError("cannot calibrate track start from a slider already near its maximum")
    track_left_local = (handle_x_local - current_ratio * track_right_local) / (1.0 - current_ratio)
    return {
        "handle_center": [round(x1 + handle_x_local), round(y1 + handle_y_local)],
        "handle_bbox_local": handle_bbox,
        "track_left": round(x1 + track_left_local, 2),
        "track_right": round(x1 + track_right_local, 2),
        "track_y": round(y1 + handle_y_local, 2),
    }


def build_action(target_percent: float, current_percent: float, geometry: dict, duration_ms: int) -> dict:
    target = max(0.0, min(100.0, target_percent))
    left, right = geometry["track_left"], geometry["track_right"]
    target_x = round(left + target / 100.0 * (right - left))
    return {
        "action": "drag",
        "start": geometry["handle_center"],
        "end": [target_x, round(geometry["track_y"])],
        "duration_ms": duration_ms,
        "target_percent": round(target, 2),
        "current_percent": round(current_percent, 2),
        "track": {
            "left": left,
            "right": right,
            "y": geometry["track_y"],
        },
        "hdc_command": f"uitest uiInput swipe {geometry['handle_center'][0]} {geometry['handle_center'][1]} {target_x} {round(geometry['track_y'])} {duration_ms}",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--layout", type=Path, required=True)
    parser.add_argument("--target-percent", type=float, required=True)
    parser.add_argument("--duration-ms", type=int, default=500)
    args = parser.parse_args()

    image = cv2.imread(str(args.image))
    if image is None:
        raise FileNotFoundError(args.image)
    bounds, current = slider_info(args.layout)
    geometry = detect_geometry(image, bounds, current)
    action = build_action(args.target_percent, current, geometry, args.duration_ms)
    action["slider_bounds"] = list(bounds)
    print(json.dumps(action, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
