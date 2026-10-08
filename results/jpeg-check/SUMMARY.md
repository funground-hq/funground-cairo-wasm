# JPEG hypothesis check (S-134)

Question: are the 4 Pyodide-vs-native differences (images-01, images-02, images-04, projects-05) only due to photo.jpg decoding?
Method: scratch copy of funground (`/home/user/scratch/fg-pngphoto`), photo.jpg decoded natively with Pillow (400x300 RGB) and saved as lossless
`examples/gallery/images/data/photo.png`; the 4 sketches edited to load `photo.png`. Rendered natively (`.venv-native`) and in Pyodide-in-Node
(`MODE=goldens MIXER_STUB=1`, one run per sketch via `--only`), compared with `harness/compare.py`.

PNG decode check: pygame and Pillow, native and Pyodide, all give RGB sha256 prefix 1fb62ea530a25fac (identical; the same as native JPEG decode).

## Pyodide vs native, PNG photo
| image | result |
|---|---|
| images-01_load_image | byte-identical |
| images-02_tint_and_parts | byte-identical |
| images-04_filters | byte-identical |
| projects-05_typographic_portrait | 622 px differ (0.230%), max abs diff 1, mean 0.33, all in the 1 bucket, 100% on AA edges, bbox 102,143,568,419 |

So for 3 of 4 the JPEG decoder is the whole cause, and cairo is bit-exact there (drawing scaled images, tint, parts, filters).
Native renders with the PNG are also byte-identical to the original goldens (`compare_native_vs_golden.json`).

## projects-05 residual: pygame smoothscale, not cairo
The sketch shrinks the photo to a grid with `picture.resize()`, which is `pygame.transform.smoothscale`; the grid pixels set each letter's fill colour.
Probe on the PNG (400x300 -> grid, cell sizes 8..30): Pyodide's smoothscale backend is `GENERIC`, native's is `SSE2`; results differ for 15 of 23 cell sizes
(default cell 14 -> 43x32: 21 of 5504 bytes differ, max 1). Forcing `pygame.transform.set_smoothscale_backend("GENERIC")` natively makes the 14 grid
byte-identical to Pyodide's and the native projects-05 render byte-identical to the Pyodide render. The 622 px are letter-edge pixels whose fill colour is off by one.
Not cairo, not pixman.

## pixman SIMD
`PIXMAN_DISABLE="mmx sse2 ssse3"` natively: all 4 images byte-identical to native with SIMD (`compare_native_nosimd_vs_native.json`), and the Pyodide
differences are unchanged (`compare_pyodide_vs_native_nosimd.json`). Pixman's bilinear/SIMD paths are not involved.

## Verdict
Hypothesis confirmed for images-01/02/04 (identical once decode is equal) and confirmed for cairo in projects-05, with a correction: the 4th sketch also has a
second, non-cairo source, pygame-ce smoothscale SSE2 vs GENERIC (max 1 level). Cairo is clean on all four.

Files: compare_pyodide_vs_native.json, compare_pyodide_vs_native_nosimd.json, compare_native_nosimd_vs_native.json, compare_native_vs_golden.json.
Scratch (not in repo): /home/user/scratch/{native,nonsimd,pyo,t,probe*.py}.
