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
