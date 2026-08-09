# Slider localization-to-drag pipeline evaluation

Date: 2026-08-08

Pipeline under test:

```text
live screenshot -> puzzle CV target -> Slider Layout crop -> track/handle CV
-> percentage-to-coordinate adapter -> HDC swipe -> Layout verification
```

The test restarted the benchmark app, completed the controlled login form, and
tested all three photographic puzzle scenes in sequence. No target coordinates
were hard-coded into the drag actions. The adapter detected the effective track
as x=`181.47..1084.00`, y=`1638.5` from the live screenshot.

| Scene | Ground truth | CV result | Drag x | Actual Slider | Result |
|---|---:|---:|---:|---:|---|
| Street | 72% | 72.48% | 181 -> 836 | 72% | Passed |
| Lake | 45% | 44.84% | 181 -> 586 | 44% | Passed |
| Cafe | 63% | 62.77% | 181 -> 748 | 62% | Passed |

All three pages displayed `验证通过` and enabled the login button. The maximum
CV localization error was 0.48 percentage points. The maximum end-to-end Slider
error, including screenshot detection, coordinate conversion, integer rounding,
and touch execution, was 1 percentage point.

Reproduction command:

```bash
python test_live_pipeline.py \
  --hdc /Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc \
  --output drag_pipeline
```

The machine-readable result is `pipeline_report.json`; each scene also includes
the screenshot and Layout before and after the generated drag action.
