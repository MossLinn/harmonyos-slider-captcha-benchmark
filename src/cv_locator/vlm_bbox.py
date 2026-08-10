#!/usr/bin/env python3
"""Ask an OpenAI-compatible vision model for slider CAPTCHA regions.

The model performs coarse semantic localization only. Pixel-accurate piece and
gap localization remains the responsibility of the traditional CV detector.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


PROMPT_VERSION = "slider-region-v1"
PROMPT = """你是移动端UI区域检测器。请判断完整截图中是否存在滑块拼图验证码。
你只负责检测区域，不要计算滑动距离，不要尝试完成验证码。

返回要求：
1. image_bbox_1000：拼图图片区域，不包含说明文字，格式[x1,y1,x2,y2]。
2. slider_bbox_1000：滑动轨道区域；如果没有独立轨道则为null。
3. captcha_type：slider_puzzle或direct_drag_puzzle。
4. confidence：0到1。
5. 如果存在多个候选，最多返回3个，按置信度降序。

所有坐标基于完整截图，归一化到0到1000。允许验证码位于顶部、中部或底部。
如果不存在验证码，返回found=false。只返回合法JSON，不要Markdown或解释。

返回结构：
{"found":true,"candidates":[{"image_bbox_1000":[0,0,1000,1000],"slider_bbox_1000":null,"captcha_type":"slider_puzzle","confidence":0.9}]}"""


def _image_data_url(image_path: Path) -> str:
    mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    raise ValueError(f"unsupported response content: {type(content).__name__}")


def _parse_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError(f"model did not return JSON: {text[:300]}")
        value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("model response must be a JSON object")
    return value


def _valid_box(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    try:
        box = [float(number) for number in value]
    except (TypeError, ValueError):
        return None
    x1, y1, x2, y2 = box
    if not (0 <= x1 < x2 <= 1000 and 0 <= y1 < y2 <= 1000):
        return None
    return box


def validate_response(value: dict[str, Any]) -> dict[str, Any]:
    found = bool(value.get("found", False))
    output: dict[str, Any] = {"found": found, "candidates": []}
    if not found:
        return output
    candidates = value.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("found=true requires a candidates array")
    for candidate in candidates[:3]:
        if not isinstance(candidate, dict):
            continue
        image_box = _valid_box(candidate.get("image_bbox_1000"))
        if image_box is None:
            continue
        slider_value = candidate.get("slider_bbox_1000")
        slider_box = None if slider_value is None else _valid_box(slider_value)
        captcha_type = str(candidate.get("captcha_type", "slider_puzzle"))
        confidence = max(0.0, min(1.0, float(candidate.get("confidence", 0.0))))
        output["candidates"].append({
            "image_bbox_1000": image_box,
            "slider_bbox_1000": slider_box,
            "captcha_type": captcha_type,
            "confidence": confidence,
        })
    output["candidates"].sort(key=lambda item: item["confidence"], reverse=True)
    output["found"] = bool(output["candidates"])
    return output


def cache_key(image_path: Path, model: str) -> str:
    digest = hashlib.sha256()
    digest.update(PROMPT_VERSION.encode())
    digest.update(model.encode())
    digest.update(image_path.read_bytes())
    return digest.hexdigest()


def call_vlm(
    image_path: Path,
    api_key: str,
    base_url: str,
    model: str,
    timeout: float = 120,
) -> dict[str, Any]:
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    body = {
        "model": model,
        "temperature": 0,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": {"url": _image_data_url(image_path)}},
            ],
        }],
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise RuntimeError(f"VLM HTTP {error.code}: {detail[:500]}") from error
    content = payload["choices"][0]["message"]["content"]
    result = validate_response(_parse_json(_message_text(content)))
    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    result["model"] = model
    result["prompt_version"] = PROMPT_VERSION
    return result


def resolve_api_key(api_key_file: Path | None) -> str:
    if api_key_file is not None:
        value = api_key_file.read_text(encoding="utf-8").strip()
    else:
        value = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not value:
        raise ValueError("provide --api-key-file or set DASHSCOPE_API_KEY")
    return value


def bbox_1000_to_pixels(box: list[float], width: int, height: int) -> list[int]:
    x1, y1, x2, y2 = box
    return [
        max(0, min(width - 1, round(x1 * width / 1000))),
        max(0, min(height - 1, round(y1 * height / 1000))),
        max(1, min(width, round(x2 * width / 1000))),
        max(1, min(height, round(y2 * height / 1000))),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--base-url", default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    parser.add_argument("--model", default="qwen3.8-max")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = call_vlm(
        args.image,
        resolve_api_key(args.api_key_file),
        args.base_url,
        args.model,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
