#!/usr/bin/env python3
"""End-to-end simulator proof: screenshot -> CV -> drag action -> verification."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import cv2

from build_drag_action import build_action, detect_geometry, slider_info
from detect_puzzle import canvas_bounds, locate


def walk(node: dict):
    yield node
    for child in node.get("children", []):
        yield from walk(child)


def center(node: dict) -> tuple[int, int]:
    raw = node["attributes"]["bounds"].replace("][", ",").strip("[]")
    x1, y1, x2, y2 = map(int, raw.split(","))
    return round((x1 + x2) / 2), round((y1 + y2) / 2)


class Device:
    def __init__(self, hdc: Path):
        self.hdc = str(hdc)

    def run(self, *args: str) -> None:
        subprocess.run([self.hdc, *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def shell(self, *args: str) -> None:
        self.run("shell", *args)

    def dump(self, local: Path) -> dict:
        remote = f"/data/local/tmp/{local.name}"
        self.shell("uitest", "dumpLayout", "-p", remote)
        self.run("file", "recv", remote, str(local))
        return json.loads(local.read_text(encoding="utf-8"))

    def screenshot(self, local: Path) -> None:
        remote = f"/data/local/tmp/{local.name}"
        self.shell("uitest", "screenCap", "-p", remote)
        self.run("file", "recv", remote, str(local))


def find_node(layout: dict, node_type: str, text: str = "", hint: str = "") -> dict:
    for node in walk(layout):
        attrs = node.get("attributes", {})
        if attrs.get("type") != node_type:
            continue
        if text and attrs.get("text") != text:
            continue
        if hint and attrs.get("hint") != hint:
            continue
        return node
    raise LookupError(f"node not found: type={node_type}, text={text}, hint={hint}")


def enter_text(device: Device, layout: dict, hint: str, value: str) -> None:
    x, y = center(find_node(layout, "TextInput", hint=hint))
    device.shell("uitest", "uiInput", "click", str(x), str(y))
    device.shell("uitest", "uiInput", "inputText", str(x), str(y), value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hdc", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    device = Device(args.hdc)

    device.shell("aa", "force-stop", "com.hmtest.captchalogin")
    device.shell("aa", "start", "-a", "EntryAbility", "-b", "com.hmtest.captchalogin")
    time.sleep(1.5)
    login_path = args.output / "login.json"
    login = device.dump(login_path)
    enter_text(device, login, "请输入账号", "testuser")
    enter_text(device, login, "请输入密码", "pass1234")
    enter_text(device, login, "输入图中字符", "7K3M")
    x, y = center(find_node(login, "Button", text="验证并继续"))
    device.shell("uitest", "uiInput", "click", str(x), str(y))
    time.sleep(1.5)

    ground_truth = [72.0, 45.0, 63.0]
    scene_names = ["street", "lake", "cafe"]
    results = []
    for index, (scene, truth) in enumerate(zip(scene_names, ground_truth)):
        before_image = args.output / f"{scene}_before.png"
        before_layout = args.output / f"{scene}_before.json"
        device.screenshot(before_image)
        before = device.dump(before_layout)

        screenshot = cv2.imread(str(before_image))
        x1, y1, x2, y2 = canvas_bounds(before_layout)
        detection = locate(screenshot[y1:y2, x1:x2])
        bounds, current = slider_info(before_layout)
        geometry = detect_geometry(screenshot, bounds, current)
        action = build_action(detection["target_percent"], current, geometry, 500)
        sx, sy = action["start"]
        ex, ey = action["end"]
        device.shell("uitest", "uiInput", "swipe", str(sx), str(sy), str(ex), str(ey), "500")
        time.sleep(1.0)

        after_image = args.output / f"{scene}_after.png"
        after_layout = args.output / f"{scene}_after.json"
        device.screenshot(after_image)
        after = device.dump(after_layout)
        actual = float(find_node(after, "Slider")["attributes"]["text"])
        status = find_node(after, "Text", text="验证通过")["attributes"]["text"] if any(
            node.get("attributes", {}).get("text") == "验证通过" for node in walk(after)
        ) else "验证失败"
        passed = status == "验证通过" and abs(actual - truth) <= 4
        results.append({
            "scene": scene,
            "ground_truth_percent": truth,
            "cv_percent": detection["target_percent"],
            "cv_absolute_error": round(abs(detection["target_percent"] - truth), 2),
            "track": action["track"],
            "drag_start": action["start"],
            "drag_end": action["end"],
            "actual_slider_percent": actual,
            "execution_absolute_error": round(abs(actual - truth), 2),
            "status": status,
            "passed": passed,
            "before_image": before_image.name,
            "after_image": after_image.name,
        })

        if index < len(scene_names) - 1:
            x, y = center(find_node(after, "Button", text="换一张拼图"))
            device.shell("uitest", "uiInput", "click", str(x), str(y))
            time.sleep(1.0)

    report = {
        "pipeline": "screenshot -> puzzle CV -> track CV/Layout -> drag action -> HDC -> Layout verification",
        "all_passed": all(result["passed"] for result in results),
        "results": results,
    }
    report_path = args.output / "pipeline_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
