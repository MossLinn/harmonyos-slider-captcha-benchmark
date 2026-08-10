# CAPTCHA BBox method comparison

Localization means region IoU >= 0.5. A run is successful when traditional CV completes and target-percent absolute error is at most 3 points.

| Method | Samples | Localization | E2E success | Mean IoU | Piece+gap containment | Mean target error | Runtime ms | Provider ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fixed_center_cv | 12 | 33.3% | 33.3% | 0.333 | 33.3% | 5.814 | 9.4 | - |
| full_screen_cv | 12 | 0.0% | 8.3% | 0.250 | 100.0% | 4.700 | 8.8 | - |
| layout_bbox_cv | 12 | 100.0% | 100.0% | 0.818 | 100.0% | 0.302 | 22.3 | - |
| oracle_bbox_cv | 12 | 100.0% | 100.0% | 1.000 | 100.0% | 0.302 | 21.9 | - |
| vlm_bbox_cv | 12 | 91.7% | 91.7% | 0.848 | 91.7% | 1.690 | 20.9 | 74409.0 |

## Failures

- `fixed_center_cv` / `bridge_top`: RuntimeError: no paired jigsaw outlines found; candidates=[(16, 11, 79, 79, 4856), (16, 11, 79, 79, 4798), (287, 382, 206, 158, 5444), (494, 382, 180, 120, 2346)]
- `full_screen_cv` / `bridge_top`: RuntimeError: no paired jigsaw outlines found; candidates=[(59, 139, 150, 323, 39471), (347, 1072, 206, 217, 6465)]
- `full_screen_cv` / `bridge_center`: RuntimeError: no paired jigsaw outlines found; candidates=[(59, 689, 150, 323, 39471), (347, 192, 206, 217, 6465)]
- `fixed_center_cv` / `bridge_bottom`: RuntimeError: no paired jigsaw outlines found; candidates=[]
- `full_screen_cv` / `bridge_bottom`: RuntimeError: no paired jigsaw outlines found; candidates=[(59, 1229, 150, 323, 39471), (347, 292, 206, 217, 6465)]
- `fixed_center_cv` / `library_top`: RuntimeError: no paired jigsaw outlines found; candidates=[(16, 11, 79, 79, 4856), (16, 11, 79, 79, 4798), (438, 449, 108, 91, 2235), (568, 385, 103, 114, 694)]
- `full_screen_cv` / `library_top`: RuntimeError: no paired jigsaw outlines found; candidates=[(71, 243, 157, 265, 14790), (814, 139, 207, 542, 3150)]
- `full_screen_cv` / `library_center`: RuntimeError: no paired jigsaw outlines found; candidates=[(71, 793, 157, 265, 14790), (814, 689, 207, 542, 3150)]
- `vlm_bbox_cv` / `library_center`: RuntimeError: no paired jigsaw outlines found; candidates=[]
- `fixed_center_cv` / `library_bottom`: RuntimeError: no paired jigsaw outlines found; candidates=[]
- `fixed_center_cv` / `market_top`: target error=27.86
- `full_screen_cv` / `market_top`: RuntimeError: no paired jigsaw outlines found; candidates=[(59, 236, 240, 445, 2425), (362, 139, 185, 313, 3386), (504, 216, 205, 239, 5114)]
- `full_screen_cv` / `market_center`: RuntimeError: no paired jigsaw outlines found; candidates=[(59, 786, 240, 445, 2425), (362, 689, 185, 313, 3386), (504, 766, 205, 239, 5114)]
- `fixed_center_cv` / `market_bottom`: RuntimeError: no paired jigsaw outlines found; candidates=[]
- `full_screen_cv` / `market_bottom`: target error=8.93
- `fixed_center_cv` / `station_top`: RuntimeError: no paired jigsaw outlines found; candidates=[(16, 11, 79, 79, 4856), (16, 11, 79, 79, 4798)]
- `full_screen_cv` / `station_top`: RuntimeError: no paired jigsaw outlines found; candidates=[]
- `full_screen_cv` / `station_center`: RuntimeError: no paired jigsaw outlines found; candidates=[]
- `fixed_center_cv` / `station_bottom`: RuntimeError: no paired jigsaw outlines found; candidates=[]
- `full_screen_cv` / `station_bottom`: RuntimeError: no paired jigsaw outlines found; candidates=[]
