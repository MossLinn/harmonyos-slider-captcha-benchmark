#!/usr/bin/env python3
"""Generate full-screen top/center/bottom slider CAPTCHA localization cases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 1920
PANEL_X = 60
PANEL_Y = {"top": 140, "center": 690, "bottom": 1230}
CHALLENGE_HEIGHT = 540


def make_background(scene_image: np.ndarray, position: str) -> np.ndarray:
    screen = np.full((SCREEN_HEIGHT, SCREEN_WIDTH, 3), (244, 246, 249), np.uint8)
    cv2.rectangle(screen, (0, 0), (SCREEN_WIDTH, 96), (255, 255, 255), -1)
    cv2.putText(screen, "Security verification", (42, 62), cv2.FONT_HERSHEY_SIMPLEX,
                1.0, (30, 36, 46), 2, cv2.LINE_AA)
    cv2.rectangle(screen, (36, 112), (1044, 1880), (255, 255, 255), -1)
    cv2.rectangle(screen, (36, 112), (1044, 1880), (221, 226, 233), 2)

    # Add a non-CAPTCHA photo card in the largest free region. It makes region
    # localization non-trivial without overlapping the controlled CAPTCHA.
    thumbnail = cv2.resize(scene_image, (390, 220), interpolation=cv2.INTER_AREA)
    if position == "top":
        thumb_y = 1070
    elif position == "bottom":
        thumb_y = 290
    else:
        thumb_y = 190
    screen[thumb_y:thumb_y + 220, 345:735] = thumbnail
    cv2.rectangle(screen, (345, thumb_y), (735, thumb_y + 220), (210, 214, 220), 3)
    cv2.putText(screen, "Account protection image", (364, thumb_y + 255),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (105, 112, 124), 2, cv2.LINE_AA)
    return screen


def offset_bbox(box: list[int], dx: int, dy: int) -> list[int]:
    x, y, w, h = box
    return [x + dx, y + dy, x + dx + w, y + dy + h]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source_manifest = json.loads((args.source / "manifest.json").read_text(encoding="utf-8"))
    screens_dir = args.output / "screens"
    annotated_dir = args.output / "annotated"
    screens_dir.mkdir(parents=True, exist_ok=True)
    annotated_dir.mkdir(parents=True, exist_ok=True)
    samples = []

    for source in source_manifest["samples"]:
        scene = source["scene"]
        panel_path = args.source / "samples" / scene / source["files"]["panel"]
        panel = cv2.imread(str(panel_path))
        if panel is None:
            raise FileNotFoundError(panel_path)
        if panel.shape[1] != 960 or panel.shape[0] < CHALLENGE_HEIGHT:
            raise ValueError(f"unexpected panel size for {scene}: {panel.shape}")
        scene_image = panel[:CHALLENGE_HEIGHT]

        for position, panel_y in PANEL_Y.items():
            screen = make_background(scene_image, position)
            panel_h, panel_w = panel.shape[:2]
            screen[panel_y:panel_y + panel_h, PANEL_X:PANEL_X + panel_w] = panel
            image_bbox = [PANEL_X, panel_y, PANEL_X + panel_w, panel_y + CHALLENGE_HEIGHT]
            panel_bbox = [PANEL_X, panel_y, PANEL_X + panel_w, panel_y + panel_h]
            slider_bbox = [PANEL_X, panel_y + CHALLENGE_HEIGHT,
                           PANEL_X + panel_w, panel_y + panel_h]
            piece_bbox = offset_bbox(source["piece_start_bbox"], PANEL_X, panel_y)
            gap_bbox = offset_bbox(source["gap_bbox"], PANEL_X, panel_y)
            sample_id = f"{scene}_{position}"
            relative = Path("screens") / f"{sample_id}.png"
            cv2.imwrite(str(args.output / relative), screen)

            annotated = screen.copy()
            cv2.rectangle(annotated, image_bbox[:2], image_bbox[2:], (255, 90, 0), 4)
            cv2.rectangle(annotated, piece_bbox[:2], piece_bbox[2:], (0, 220, 0), 3)
            cv2.rectangle(annotated, gap_bbox[:2], gap_bbox[2:], (0, 60, 255), 3)
            cv2.imwrite(str(annotated_dir / f"{sample_id}.png"), annotated)
            samples.append({
                "id": sample_id,
                "scene": scene,
                "position": position,
                "screen_size": [SCREEN_WIDTH, SCREEN_HEIGHT],
                "target_percent": source["target_percent"],
                "image_bbox": image_bbox,
                "panel_bbox": panel_bbox,
                "slider_bbox": slider_bbox,
                "piece_bbox": piece_bbox,
                "gap_bbox": gap_bbox,
                "screenshot": str(relative),
            })

    manifest = {
        "schema_version": 1,
        "purpose": "compare fixed-region, layout, VLM and oracle CAPTCHA ROI methods",
        "sample_count": len(samples),
        "screen_size": [SCREEN_WIDTH, SCREEN_HEIGHT],
        "positions": list(PANEL_Y),
        "samples": samples,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(args.output), "sample_count": len(samples)}, indent=2))


if __name__ == "__main__":
    main()
