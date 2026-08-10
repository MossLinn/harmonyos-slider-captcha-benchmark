# CV puzzle locator

This is a detector for the controlled `captcha_login_benchmark`. It combines the
HarmonyOS accessibility layout (to crop the Canvas) with OpenCV (to locate the
movable piece and puzzle gap). Edge geometry is preferred so that white or bright
objects in realistic photos do not merge with the puzzle border; a bright-region
detector remains as fallback. It is intended for GUI-agent evaluation, not for
bypassing third-party verification systems.

```bash
python detect_puzzle.py --image puzzle.png --layout puzzle.json \
  --annotated puzzle_cv_annotated.png
```

`evaluate_robustness.py` evaluates deterministic scale, brightness, blur, and
JPEG perturbations against a supplied target.

## VLM BBox + traditional CV comparison

Generate 12 full-screen cases by placing the four photo puzzles at the top,
center, and bottom of a 1080x1920 screen:

```bash
python generate_position_benchmark.py \
  --source ../../datasets/slider_puzzle_realistic_v2 \
  --output ../../datasets/captcha_region_position_v1
```

Run deterministic baselines:

```bash
python compare_bbox_methods.py \
  --dataset ../../datasets/captcha_region_position_v1 \
  --output ../../ground_truth/evidence/captcha_region_methods/rules
```

Add the cached VLM region proposal method:

```bash
export DASHSCOPE_API_KEY='your-key'
python compare_bbox_methods.py \
  --dataset ../../datasets/captcha_region_position_v1 \
  --output ../../ground_truth/evidence/captcha_region_methods/vlm \
  --methods fixed_center_cv,layout_bbox_cv,vlm_bbox_cv,oracle_bbox_cv \
  --model qwen3.8-max
```

For local automation, `--api-key-file /path/to/apikey.txt` is also supported.
Never commit that file or the generated `vlm_cache/` directory.

The VLM receives the full, uncropped screenshot and returns normalized
0..1000 coordinates. Its response is cached by image, model, and prompt hash.
Every method then uses the same `detect_jigsaw.locate` implementation so that
the comparison isolates region proposal quality.

## Shape-agnostic source/gap pairing

`detect_jigsaw.py` does not classify a puzzle as a circle, triangle, square, or
jigsaw piece. It clusters duplicate edge contours and ranks source/gap pairs by
Hu-moment contour similarity, scale, area, horizontal-row alignment, and travel
direction. This makes new shapes usable without adding shape-specific rules.

Generate and evaluate the 16-case, four-shape regression suite:

```bash
python generate_shape_benchmark.py \
  --backgrounds ../../datasets/slider_puzzle_realistic_v2/backgrounds \
  --output ../../datasets/slider_puzzle_shapes_v1

python evaluate_shape_benchmark.py \
  --dataset ../../datasets/slider_puzzle_shapes_v1 \
  --output ../../ground_truth/evidence/slider_puzzle_shapes_v1
```
