# CV + VLM hybrid localization evaluation

Date: 2026-08-08

Scope: controlled HarmonyOS `captcha_login_benchmark`. This evaluation measures
localization accuracy; it is not intended for bypassing third-party CAPTCHA
systems.

## Pipeline

1. Read the HarmonyOS accessibility layout and crop the Canvas using
   `[91,843][1169,1389]`.
2. Use OpenCV brightness/saturation segmentation and connected components to
   propose square candidates.
3. Identify the left candidate as the movable piece and the right candidate as
   the gap.
4. Compute the target as a percentage of available piece travel.
5. Let the agent decide whether the current state calls for a drag, then map the
   percentage to Slider touch coordinates.

## Accuracy

| Measurement | Result |
|---|---:|
| Ground-truth target | 72.00% |
| OpenCV prediction | 72.36% |
| CV absolute error | 0.36 percentage points |
| Qwen screenshot-only prediction | 71% |
| Qwen absolute error | 1.00 percentage point |
| Live Slider value after CV-directed drag | 73% |
| Application result | Passed |

Detected Canvas-relative boxes:

- Movable piece: `[47,236,159,159]`, center x = `126.5`
- Puzzle gap: `[678,236,159,159]`, center x = `757.5`
- Detected horizontal distance: `631 px`

## Robustness test

The same screenshot was deterministically perturbed across three scales, three
brightness offsets, two blur settings, and two JPEG qualities (36 cases).

| Metric | Result |
|---|---:|
| Detection rate | 36/36 (100%) |
| Mean absolute error | 0.427 percentage points |
| Maximum absolute error | 2.05 percentage points |
| Error <= 1 percentage point | 34/36 (94.44%) |
| Within app tolerance (±4%) | 36/36 (100%) |

## Interpretation

For this controlled sample, CV gives a more precise geometry estimate than the
single screenshot-only VLM call. The useful hybrid division is: layout for the
Canvas/Slider bounds, CV for pixel geometry, and the VLM/agent for state and
action selection. This initial result should not yet be generalized to irregular,
rotated, or animated puzzle challenges without a broader dataset.

## Realistic-scene iteration (2026-08-08)

The flat illustration was replaced by three generated, unbranded photographic
scenes. The app now cycles through street, alpine-lake, and cafe-table images
with targets of 72%, 45%, and 63%. The rectangular piece contains the real image
crop from the target location rather than a solid-color placeholder.

The first bright-component detector exposed a genuine failure on the cafe image:
the white cup connected with the white puzzle border under blur/brightness
perturbations. Cafe detection fell to 61.11%, with 8.237 percentage points mean
absolute error. The detector was therefore changed to use rectangular edge
geometry first and retain bright connected components only as fallback.

| Scene | Direct CV prediction | Ground truth | 36-case detection rate | Mean error | Max error |
|---|---:|---:|---:|---:|---:|
| Street | 72.48% | 72% | 100% | 0.497 pp | 0.70 pp |
| Alpine lake | 44.84% | 45% | 100% | 0.197 pp | 0.48 pp |
| Cafe table | 62.77% | 63% | 100% | 0.227 pp | 0.52 pp |

Across all 108 deterministic perturbation cases, detection succeeded in 108/108
and every result was within one percentage point of its target. Live simulator
drags landed at 72%, 43%, and 63%; all three passed the app's ±4% tolerance.

These are realistic-looking controlled scenes, not captured challenges from a
production service. They improve visual diversity without creating a workflow
for attacking a third-party CAPTCHA system.
