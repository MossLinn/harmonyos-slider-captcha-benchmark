#!/usr/bin/env python3
"""Evaluate shape-agnostic puzzle localization by shape family."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

import cv2

from detect_jigsaw import annotate, locate


def center(box: list[int]) -> tuple[float, float]:
    x, y, w, h = box
    return x + w / 2, y + h / 2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.dataset / "manifest.json").read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    annotated_dir = args.output / "annotated"
    annotated_dir.mkdir(exist_ok=True)
    rows = []
    for sample in manifest["samples"]:
        image = cv2.imread(str(args.dataset / sample["image"]))
        row = {"id": sample["id"], "shape": sample["shape"], "success": False}
        try:
            result = locate(image)
            target_error = abs(result["target_percent"] - sample["target_percent"])
            pcx, pcy = center(result["piece_bbox"])
            gcx, gcy = center(result["gap_bbox"])
            tpcx, tpcy = center(sample["piece_bbox"])
            tgcx, tgcy = center(sample["gap_bbox"])
            center_error = (abs(pcx - tpcx) + abs(pcy - tpcy) +
                            abs(gcx - tgcx) + abs(gcy - tgcy)) / 4
            row.update({
                "success": target_error <= 3.0 and center_error <= 8.0,
                "target_percent": result["target_percent"],
                "target_error": round(target_error, 3),
                "mean_center_error_px": round(center_error, 3),
                "pair_score": result["pair_score"],
                "shape_match_error": result["shape_match_error"],
            })
            cv2.imwrite(str(annotated_dir / f"{sample['id']}.png"), annotate(image, result))
        except Exception as error:
            row["error"] = f"{type(error).__name__}: {error}"
        rows.append(row)

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["shape"]].append(row)
    summary = []
    for shape, selected in sorted(grouped.items()):
        errors = [row["target_error"] for row in selected if "target_error" in row]
        summary.append({
            "shape": shape,
            "samples": len(selected),
            "success_rate": round(sum(row["success"] for row in selected) / len(selected), 4),
            "mean_target_error": round(statistics.fmean(errors), 3) if errors else None,
        })
    report = {"summary": summary, "rows": rows}
    (args.output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = ["# Shape-agnostic puzzle benchmark", "", "| Shape | Samples | Success | Mean target error |", "|---|---:|---:|---:|"]
    for item in summary:
        error = "-" if item["mean_target_error"] is None else f"{item['mean_target_error']:.3f}"
        lines.append(f"| {item['shape']} | {item['samples']} | {item['success_rate']:.1%} | {error} |")
    (args.output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
