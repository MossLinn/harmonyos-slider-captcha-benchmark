#!/usr/bin/env python3
"""Generate controlled circle/triangle/square/jigsaw slider challenges."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from generate_jigsaw_dataset import draw_contour, jigsaw_mask, paste_masked


WIDTH, HEIGHT, MASK_SIZE = 960, 540, 140
SOURCE_X = 25


def shape_mask(kind: str, variant: int) -> np.ndarray:
    mask = np.zeros((MASK_SIZE, MASK_SIZE), np.uint8)
    if kind == "circle":
        cv2.circle(mask, (70, 70), 49 + variant % 3, 255, -1)
    elif kind == "square":
        inset = 18 + variant % 4
        cv2.rectangle(mask, (inset, inset), (MASK_SIZE - inset, MASK_SIZE - inset), 255, -1)
    elif kind == "triangle":
        skew = (variant % 3 - 1) * 8
        points = np.array([[70 + skew, 12], [128, 124], [12, 124]], np.int32)
        cv2.fillPoly(mask, [points], 255)
    elif kind == "jigsaw":
        mask = jigsaw_mask(variant % 4)
    else:
        raise ValueError(kind)
    return mask


def make_sample(background_path: Path, output: Path, kind: str, variant: int,
                gap_x: int, y: int) -> dict:
    source = cv2.imread(str(background_path))
    if source is None:
        raise FileNotFoundError(background_path)
    background = cv2.resize(source, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
    challenge = background.copy()
    mask = shape_mask(kind, variant)
    target_crop = background[y:y + MASK_SIZE, gap_x:gap_x + MASK_SIZE].copy()

    gap_roi = challenge[y:y + MASK_SIZE, gap_x:gap_x + MASK_SIZE]
    darkened = np.clip(gap_roi.astype(np.float32) * 0.35, 0, 255).astype(np.uint8)
    np.copyto(gap_roi, darkened, where=(mask[:, :, None] > 0))
    draw_contour(challenge, mask, gap_x, y, (250, 250, 250), 5)
    paste_masked(challenge, target_crop, mask, SOURCE_X, y)
    draw_contour(challenge, mask, SOURCE_X, y, (250, 250, 250), 5)

    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), challenge)
    bx, by, bw, bh = cv2.boundingRect(mask)
    piece_bbox = [SOURCE_X + bx, y + by, bw, bh]
    gap_bbox = [gap_x + bx, y + by, bw, bh]
    piece_center = piece_bbox[0] + bw / 2
    gap_center = gap_bbox[0] + bw / 2
    available = WIDTH - max(bw, bh) / 2 - piece_center
    return {
        "id": output.stem,
        "shape": kind,
        "scene": background_path.stem,
        "image": str(Path("images") / output.name),
        "piece_bbox": piece_bbox,
        "gap_bbox": gap_bbox,
        "target_percent": round(100 * (gap_center - piece_center) / available, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backgrounds", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scenes = ["bridge", "library", "market", "station"]
    shapes = ["circle", "triangle", "square", "jigsaw"]
    gap_xs = [320, 450, 590, 715]
    ys = [115, 205, 155, 235]
    samples = []
    for shape_index, kind in enumerate(shapes):
        for scene_index, scene in enumerate(scenes):
            sample_id = f"{kind}_{scene}"
            samples.append(make_sample(
                args.backgrounds / f"{scene}.png",
                args.output / "images" / f"{sample_id}.png",
                kind,
                scene_index + shape_index,
                gap_xs[scene_index],
                ys[(scene_index + shape_index) % len(ys)],
            ))
    manifest = {
        "schema_version": 1,
        "purpose": "shape-agnostic slider puzzle localization benchmark",
        "sample_count": len(samples),
        "shapes": shapes,
        "samples": samples,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"output": str(args.output), "sample_count": len(samples)}))


if __name__ == "__main__":
    main()
