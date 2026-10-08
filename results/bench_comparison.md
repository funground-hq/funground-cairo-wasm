# Bench comparison: Pyodide 314.0.7 in Node vs native CPython (same sources)

Node v22.22.0 (V8 12.4.254.21-node.33); Pyodide 314.0.7 (CPython 3.14.2, Emscripten 5.0.3 build); native CPython 3.14.6, gcc 13.3, cairo 1.18.4 + pixman 0.46.4 (same sources; pixman uses x86 SIMD natively, generic C in wasm).

CPU: Intel(R) Xeon(R) Processor @ 2.80GHz (lscpu model name; 4 vCPUs). Medians in ms over 30 timed repetitions after 5 warm-up. Ratio = Node / native. Node: `results/pyodide/bench.json`; native: `results/native/bench_rerun.json` (run right after the Node run, same settings, same 10 examples).

## Per example (ms, median)

| example | ops | replay 640x400 Node | native | x | replay 1280x800 Node | native | x | full frame 1x Node | native | x | full frame 2x Node | native | x |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| projects-02_rangoli | 636 | 8.91 | 4.63 | 1.93 | 12.8 | 9.05 | 1.41 | 28.2 | 13.1 | 2.15 | 33.1 | 17.6 | 1.88 |
| projects-06_kinetic_type | 633 | 18.7 | 7.42 | 2.52 | 22.2 | 11.0 | 2.01 | 107.8 | 42.8 | 2.52 | 126.1 | 51.5 | 2.45 |
| text-09_text_dots | 507 | 18.3 | 7.03 | 2.60 | 27.5 | 9.73 | 2.82 | 55.4 | 21.6 | 2.57 | 61.7 | 25.5 | 2.42 |
| randomness-03_noise | 419 | 2.82 | 2.55 | 1.11 | 4.71 | 2.44 | 1.93 | 36.3 | 16.2 | 2.25 | 32.8 | 15.2 | 2.15 |
| sound-02_write_a_tune | 413 | 8.79 | 3.57 | 2.47 | 10.8 | 7.56 | 1.42 | 168.2 | 63.9 | 2.63 | 162.6 | 63.6 | 2.56 |
| randomness-02_gaussian_and_choice | 401 | 7.87 | 4.48 | 1.76 | 11.1 | 6.49 | 1.71 | 28.0 | 11.1 | 2.52 | 29.7 | 16.0 | 1.85 |
| studios-03_rhythm | 371 | 8.76 | 3.24 | 2.70 | 8.34 | 4.19 | 1.99 | 364.4 | 139.9 | 2.61 | 1287.9 | 545.5 | 2.36 |
| studios-05_text_as_geometry | 290 | 4.52 | 1.94 | 2.33 | 6.32 | 3.15 | 2.01 | 171.8 | 69.6 | 2.47 | 662.9 | 278.5 | 2.38 |
| paths-06_outlines | 249 | 14.1 | 5.77 | 2.44 | 19.2 | 8.81 | 2.18 | 43.9 | 14.2 | 3.09 | 37.9 | 16.8 | 2.25 |
| studios-06_poster_series | 229 | 36.6 | 12.5 | 2.92 | 41.8 | 15.6 | 2.67 | 51.2 | 21.7 | 2.36 | 48.3 | 30.6 | 1.58 |
| **mean of the 10** |  | 12.9 | 5.32 | 2.28 (of ratios) / 2.43 (of means) | 16.5 | 7.81 | 2.02 (of ratios) / 2.11 (of means) | 105.5 | 41.4 | 2.52 (of ratios) / 2.55 (of means) | 248.3 | 106.1 | 2.19 (of ratios) / 2.34 (of means) |

## Examples at or under 12 ms

| measure | Node | native |
|---|---:|---:|
| replay @1280x800 | 5 / 10 | 9 / 10 |
| replay @640x400 | 6 / 10 | 9 / 10 |
| full frame 2x (draw + render + loop) | 0 / 10 | 0 / 10 |
| full frame 1x | 0 / 10 | 1 / 10 |

## Full frame split at 2x (ms, median): draw() / render

| example | Node draw | Node render | native draw | native render |
|---|---:|---:|---:|---:|
| projects-02_rangoli | 14.3 | 18.1 | 6.21 | 10.8 |
| projects-06_kinetic_type | 97.2 | 24.4 | 37.7 | 12.5 |
| text-09_text_dots | 36.2 | 23.0 | 13.6 | 10.9 |
| randomness-03_noise | 27.3 | 4.98 | 12.1 | 2.90 |
| sound-02_write_a_tune | 151.3 | 11.0 | 57.3 | 6.00 |
| randomness-02_gaussian_and_choice | 17.2 | 11.9 | 7.90 | 7.54 |
| studios-03_rhythm | n/a | n/a | n/a | n/a |
| studios-05_text_as_geometry | n/a | n/a | n/a | n/a |
| paths-06_outlines | 19.5 | 17.7 | 7.69 | 8.91 |
| studios-06_poster_series | 8.76 | 39.3 | 5.25 | 25.2 |

## Supplement: redraw-on-change examples (0 ops in the last frame)

projects-01, projects-05 (1377 ops at its peak frame) and saving-04 draw only when something changed, so the last frame is empty and they rank last by last-frame ops. The peak-op frame of projects-05 replayed:

| example | peak ops | size | Node | native | x |
|---|---:|---|---:|---:|---:|
| projects-05_typographic_portrait | 1377 | 640x400 | 219.4 | 80.8 | 2.72 |
| projects-05_typographic_portrait | 1377 | 1280x800 | 210.4 | 85.4 | 2.47 |

## Notes

- studios-03_rhythm and studios-05_text_as_geometry are top-level scripts (no `f.run()` loop): their "full frame" columns are the time of the whole script run (draw + canvas flush), not one frame; no draw/render split.
- "full frame" is the headless loop iteration (draw() + render + present), median; the ratio columns are Node / native.
- Replay times the renderer alone (cairo + pixman); full frame adds funground's Python (draw, IR building, text shaping), so its ratio mostly reflects Pyodide's CPython speed versus native.
