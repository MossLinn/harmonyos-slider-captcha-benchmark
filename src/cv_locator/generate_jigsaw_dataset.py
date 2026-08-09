#!/usr/bin/env python3
"""Build controlled photo-based jigsaw slider samples with pixel-level truth."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


WIDTH = 960
HEIGHT = 540
MASK_SIZE = 140
PIECE_START_X = 25
SLIDER_START_X = 55
SLIDER_END_X = 905


def jigsaw_mask(rotation: int) -> np.ndarray:
    mask = np.zeros((MASK_SIZE, MASK_SIZE), np.uint8)
    cv2.rectangle(mask, (20, 20), (120, 120), 255, -1)
    # Top and bottom tabs; left and right concave sockets.
    cv2.circle(mask, (70, 20), 19, 255, -1)
    cv2.circle(mask, (70, 120), 19, 255, -1)
    cv2.circle(mask, (20, 70), 18, 0, -1)
    cv2.circle(mask, (120, 70), 18, 0, -1)
    return np.rot90(mask, rotation).copy()


def draw_contour(image: np.ndarray, mask: np.ndarray, x: int, y: int, color, thickness: int) -> None:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    shifted = [contour + np.array([[[x, y]]], dtype=contour.dtype) for contour in contours]
    cv2.drawContours(image, shifted, -1, color, thickness, cv2.LINE_AA)


def paste_masked(destination: np.ndarray, source: np.ndarray, mask: np.ndarray, x: int, y: int) -> None:
    roi = destination[y:y + MASK_SIZE, x:x + MASK_SIZE]
    np.copyto(roi, source, where=(mask[:, :, None] > 0))


def generate_sample(background_path: Path, output_dir: Path, target_percent: int,
                    gap_y: int, rotation: int) -> dict:
    original = cv2.imread(str(background_path))
    if original is None:
        raise FileNotFoundError(background_path)
    background = cv2.resize(original, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
    mask = jigsaw_mask(rotation)
    gap_x = round(PIECE_START_X + target_percent / 100 * (WIDTH - MASK_SIZE - PIECE_START_X))

    target_crop = background[gap_y:gap_y + MASK_SIZE, gap_x:gap_x + MASK_SIZE].copy()
    challenge = background.copy()

    gap_roi = challenge[gap_y:gap_y + MASK_SIZE, gap_x:gap_x + MASK_SIZE]
    darkened = np.clip(gap_roi.astype(np.float32) * 0.38, 0, 255).astype(np.uint8)
    np.copyto(gap_roi, darkened, where=(mask[:, :, None] > 0))
    draw_contour(challenge, mask, gap_x, gap_y, (245, 245, 245), 4)

    shadow_mask = cv2.GaussianBlur(mask, (13, 13), 0)
    shadow = np.zeros_like(challenge)
    shadow_y = min(gap_y + 7, HEIGHT - MASK_SIZE)
    shadow_roi = shadow[shadow_y:shadow_y + MASK_SIZE, PIECE_START_X + 7:PIECE_START_X + 7 + MASK_SIZE]
    shadow_roi[:] = (12, 12, 12)
    alpha = (shadow_mask.astype(np.float32) / 255 * 0.48)[:, :, None]
    dst = challenge[shadow_y:shadow_y + MASK_SIZE, PIECE_START_X + 7:PIECE_START_X + 7 + MASK_SIZE]
    dst[:] = (dst * (1 - alpha) + shadow_roi * alpha).astype(np.uint8)

    paste_masked(challenge, target_crop, mask, PIECE_START_X, gap_y)
    draw_contour(challenge, mask, PIECE_START_X, gap_y, (250, 250, 250), 4)

    panel = np.full((660, WIDTH, 3), 248, np.uint8)
    panel[:HEIGHT] = challenge
    cv2.line(panel, (SLIDER_START_X, 600), (SLIDER_END_X, 600), (215, 218, 224), 24, cv2.LINE_AA)
    cv2.circle(panel, (SLIDER_START_X, 600), 42, (242, 132, 24), -1, cv2.LINE_AA)
    cv2.circle(panel, (SLIDER_START_X, 600), 42, (255, 255, 255), 4, cv2.LINE_AA)
    cv2.line(panel, (43, 585), (43, 615), (255, 255, 255), 5, cv2.LINE_AA)
    cv2.line(panel, (56, 585), (56, 615), (255, 255, 255), 5, cv2.LINE_AA)
    cv2.line(panel, (69, 585), (69, 615), (255, 255, 255), 5, cv2.LINE_AA)

    output_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_dir / "background.png"), background)
    cv2.imwrite(str(output_dir / "challenge.png"), challenge)
    cv2.imwrite(str(output_dir / "panel.png"), panel)
    cv2.imwrite(str(output_dir / "mask.png"), mask)

    return {
        "scene": background_path.stem,
        "image_size": [WIDTH, HEIGHT],
        "target_percent": target_percent,
        "piece_start_bbox": [PIECE_START_X, gap_y, MASK_SIZE, MASK_SIZE],
        "gap_bbox": [gap_x, gap_y, MASK_SIZE, MASK_SIZE],
        "drag_pixels": gap_x - PIECE_START_X,
        "slider_track": [SLIDER_START_X, 600, SLIDER_END_X, 600],
        "target_slider_x": round(SLIDER_START_X + target_percent / 100 * (SLIDER_END_X - SLIDER_START_X)),
        "mask_rotation_quarters": rotation,
        "files": {
            "background": "background.png",
            "challenge": "challenge.png",
            "panel": "panel.png",
            "mask": "mask.png"
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "datasets" / "slider_puzzle_realistic_v2",
        help="dataset root containing backgrounds/ and receiving samples/",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    specs = [
        ("bridge", 38, 180, 0),
        ("library", 52, 245, 1),
        ("market", 67, 150, 2),
        ("station", 79, 220, 3),
    ]
    samples = []
    for scene, target, gap_y, rotation in specs:
        samples.append(generate_sample(
            root / "backgrounds" / f"{scene}.png",
            root / "samples" / scene,
            target,
            gap_y,
            rotation,
        ))
    manifest = {
        "schema_version": 1,
        "purpose": "controlled offline GUI-agent slider-puzzle localization benchmark",
        "sample_count": len(samples),
        "samples": samples,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
