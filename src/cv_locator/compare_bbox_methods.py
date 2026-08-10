#!/usr/bin/env python3
"""Compare CAPTCHA region proposals followed by the same traditional CV detector."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any, Callable

import cv2

from detect_jigsaw import locate
from vlm_bbox import bbox_1000_to_pixels, cache_key, call_vlm, resolve_api_key


BBox = list[int]


def area(box: BBox) -> int:
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def intersection(box_a: BBox, box_b: BBox) -> int:
    return max(0, min(box_a[2], box_b[2]) - max(box_a[0], box_b[0])) * max(
        0, min(box_a[3], box_b[3]) - max(box_a[1], box_b[1])
    )


def iou(box_a: BBox, box_b: BBox) -> float:
    overlap = intersection(box_a, box_b)
    union = area(box_a) + area(box_b) - overlap
    return overlap / union if union else 0.0


def contains(container: BBox, child: BBox) -> bool:
    return intersection(container, child) >= 0.98 * area(child)


def clip_and_pad(box: BBox, width: int, height: int, padding: float) -> BBox:
    box_w, box_h = box[2] - box[0], box[3] - box[1]
    pad_x, pad_y = round(box_w * padding), round(box_h * padding)
    return [
        max(0, box[0] - pad_x),
        max(0, box[1] - pad_y),
        min(width, box[2] + pad_x),
        min(height, box[3] + pad_y),
    ]


def fixed_center(sample: dict[str, Any], _: Path) -> tuple[BBox, dict[str, Any]]:
    width, height = sample["screen_size"]
    target_w, target_h = 960, 540
    x1, y1 = (width - target_w) // 2, (height - target_h) // 2
    return [x1, y1, x1 + target_w, y1 + target_h], {}


def full_screen(sample: dict[str, Any], _: Path) -> tuple[BBox, dict[str, Any]]:
    width, height = sample["screen_size"]
    return [0, 0, width, height], {}


def layout_panel(sample: dict[str, Any], _: Path) -> tuple[BBox, dict[str, Any]]:
    return list(sample["panel_bbox"]), {"source": "simulated_layout"}


def oracle_image(sample: dict[str, Any], _: Path) -> tuple[BBox, dict[str, Any]]:
    return list(sample["image_bbox"]), {"source": "ground_truth"}


class VlmMethod:
    def __init__(self, args: argparse.Namespace):
        self.api_key = resolve_api_key(args.api_key_file)
        self.base_url = args.base_url
        self.model = args.model
        self.cache_dir = args.cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def __call__(self, sample: dict[str, Any], image_path: Path) -> tuple[BBox, dict[str, Any]]:
        key = cache_key(image_path, self.model)
        cache_path = self.cache_dir / f"{sample['id']}-{key[:12]}.json"
        if cache_path.exists():
            response = json.loads(cache_path.read_text(encoding="utf-8"))
            cached = True
        else:
            response = call_vlm(image_path, self.api_key, self.base_url, self.model)
            cache_path.write_text(json.dumps(response, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")
            cached = False
        if not response.get("found") or not response.get("candidates"):
            raise RuntimeError("VLM returned no CAPTCHA candidate")
        candidate = response["candidates"][0]
        width, height = sample["screen_size"]
        box = bbox_1000_to_pixels(candidate["image_bbox_1000"], width, height)
        return box, {
            "confidence": candidate["confidence"],
            "captcha_type": candidate["captcha_type"],
            "vlm_latency_ms": response.get("latency_ms", 0),
            "cached": cached,
        }


def annotate(image, gt: BBox, predicted: BBox, output: Path, label: str) -> None:
    rendered = image.copy()
    cv2.rectangle(rendered, gt[:2], gt[2:], (255, 90, 0), 4)
    cv2.rectangle(rendered, predicted[:2], predicted[2:], (0, 220, 0), 4)
    cv2.putText(rendered, label, (predicted[0], max(30, predicted[1] - 12)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 150, 0), 2, cv2.LINE_AA)
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), rendered)


def evaluate_one(
    method_name: str,
    method: Callable[[dict[str, Any], Path], tuple[BBox, dict[str, Any]]],
    sample: dict[str, Any],
    dataset: Path,
    output_dir: Path,
    padding: float,
) -> dict[str, Any]:
    image_path = dataset / sample["screenshot"]
    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(image_path)
    started = time.perf_counter()
    row: dict[str, Any] = {
        "sample": sample["id"],
        "scene": sample["scene"],
        "position": sample["position"],
        "method": method_name,
        "success": False,
    }
    try:
        raw_box, metadata = method(sample, image_path)
        box = clip_and_pad(raw_box, image.shape[1], image.shape[0], padding if method_name == "vlm_bbox_cv" else 0)
        if box[2] <= box[0] or box[3] <= box[1]:
            raise ValueError(f"invalid crop bbox: {box}")
        # Persist region-stage evidence even when the downstream CV verifier fails.
        row.update({
            "bbox": box,
            "raw_bbox": raw_box,
            "bbox_iou": round(iou(box, sample["image_bbox"]), 4),
            "contains_piece": contains(box, sample["piece_bbox"]),
            "contains_gap": contains(box, sample["gap_bbox"]),
            **metadata,
        })
        crop = image[box[1]:box[3], box[0]:box[2]]
        cv_result = locate(crop)
        target_error = abs(float(cv_result["target_percent"]) - float(sample["target_percent"]))
        row.update({
            "target_percent": cv_result["target_percent"],
            "target_abs_error": round(target_error, 3),
            "cv_candidate_count": cv_result["candidate_count"],
            "success": target_error <= 3.0,
        })
        annotate(image, sample["image_bbox"], box,
                 output_dir / "annotated" / method_name / f"{sample['id']}.png", method_name)
    except Exception as error:  # Record failure without aborting the comparison.
        row["error"] = f"{type(error).__name__}: {error}"
    row["total_latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return row


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for method in sorted({row["method"] for row in rows}):
        selected = [row for row in rows if row["method"] == method]
        successes = [row for row in selected if row["success"]]
        detected = [row for row in selected if "bbox_iou" in row]
        localized = [row for row in detected if row["bbox_iou"] >= 0.5]
        errors = [row["target_abs_error"] for row in selected if "target_abs_error" in row]
        latencies = [row["total_latency_ms"] for row in selected]
        provider_latencies = [row["vlm_latency_ms"] for row in selected if "vlm_latency_ms" in row]
        summaries.append({
            "method": method,
            "samples": len(selected),
            "detection_rate": round(len(localized) / len(selected), 4),
            "end_to_end_success_rate": round(len(successes) / len(selected), 4),
            "mean_bbox_iou": round(statistics.fmean(row["bbox_iou"] for row in detected), 4) if detected else 0,
            "piece_gap_recall": round(
                sum(
                    bool(row.get("contains_piece")) and bool(row.get("contains_gap"))
                    for row in selected
                )
                / len(selected),
                4,
            ),
            "mean_target_abs_error": round(statistics.fmean(errors), 3) if errors else None,
            "mean_total_latency_ms": round(statistics.fmean(latencies), 2),
            "mean_vlm_provider_latency_ms": (
                round(statistics.fmean(provider_latencies), 2) if provider_latencies else None
            ),
        })
    return summaries


def markdown_report(summaries: list[dict[str, Any]], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# CAPTCHA BBox method comparison",
        "",
        "Localization means region IoU >= 0.5. A run is successful when traditional CV completes and target-percent absolute error is at most 3 points.",
        "",
        "| Method | Samples | Localization | E2E success | Mean IoU | Piece+gap containment | Mean target error | Runtime ms | Provider ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in summaries:
        target_error = "-" if item["mean_target_abs_error"] is None else f"{item['mean_target_abs_error']:.3f}"
        provider_latency = (
            "-" if item["mean_vlm_provider_latency_ms"] is None
            else f"{item['mean_vlm_provider_latency_ms']:.1f}"
        )
        lines.append(
            f"| {item['method']} | {item['samples']} | {item['detection_rate']:.1%} | "
            f"{item['end_to_end_success_rate']:.1%} | {item['mean_bbox_iou']:.3f} | "
            f"{item['piece_gap_recall']:.1%} | {target_error} | {item['mean_total_latency_ms']:.1f} | "
            f"{provider_latency} |"
        )
    lines.extend(["", "## Failures", ""])
    failures = [row for row in rows if not row["success"]]
    if not failures:
        lines.append("None.")
    else:
        for row in failures:
            detail = row.get("error") or f"target error={row.get('target_abs_error')}"
            lines.append(f"- `{row['method']}` / `{row['sample']}`: {detail}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--methods", default="fixed_center_cv,full_screen_cv,layout_bbox_cv,oracle_bbox_cv")
    parser.add_argument("--positions", help="comma-separated subset: top,center,bottom")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--base-url", default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    parser.add_argument("--model", default="qwen3.8-max")
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--vlm-padding", type=float, default=0.02)
    args = parser.parse_args()

    manifest = json.loads((args.dataset / "manifest.json").read_text(encoding="utf-8"))
    samples = manifest["samples"]
    if args.positions:
        allowed = set(args.positions.split(","))
        samples = [sample for sample in samples if sample["position"] in allowed]
    if args.limit is not None:
        samples = samples[:args.limit]
    args.output.mkdir(parents=True, exist_ok=True)
    if args.cache_dir is None:
        args.cache_dir = args.output / "vlm_cache"

    methods: dict[str, Callable] = {
        "fixed_center_cv": fixed_center,
        "full_screen_cv": full_screen,
        "layout_bbox_cv": layout_panel,
        "oracle_bbox_cv": oracle_image,
    }
    requested = args.methods.split(",")
    if "vlm_bbox_cv" in requested:
        try:
            methods["vlm_bbox_cv"] = VlmMethod(args)
        except ValueError as error:
            parser.error(str(error))
    unknown = [name for name in requested if name not in methods]
    if unknown:
        parser.error(f"unknown methods: {','.join(unknown)}")

    rows = []
    for sample in samples:
        for method_name in requested:
            rows.append(evaluate_one(
                method_name, methods[method_name], sample, args.dataset,
                args.output, args.vlm_padding,
            ))
            print(json.dumps(rows[-1], ensure_ascii=False))

    summaries = summarize(rows)
    report = {"summaries": summaries, "rows": rows}
    (args.output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output / "REPORT.md").write_text(markdown_report(summaries, rows), encoding="utf-8")
    print(json.dumps({"summaries": summaries, "output": str(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
