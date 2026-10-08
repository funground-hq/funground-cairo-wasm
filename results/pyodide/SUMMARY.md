# Pyodide 314.0.7 in Node 22: goldens and bench

Runner: `scripts/run_node_tests.sh` (`test/node/run.mjs`). Node v22.22.0 (V8 12.4.254.21-node.33), Intel Xeon @ 2.80GHz, 4 vCPUs.
`import funground` and all 87 renderable sketches work on the wasm wheels. The 4 pixel differences come from JPEG decoding
in Pyodide's pygame-ce/Pillow, plus (projects-05 only) pygame-ce's smoothscale GENERIC vs SSE2 backend; not from cairo (see ../jpeg-check/SUMMARY.md). pygame's mixer cannot start in Pyodide, which stops 4 of the 91 golden sketches.

## Versions in the Pyodide run (`versions.json`)
| | |
|---|---|
| Pyodide / Python | 314.0.7 / CPython 3.14.2 (Emscripten 5.0.3 build) |
| pycairo / cairo | 1.29.2 (local wheel) / 1.18.4 (static, pixman 0.46.4, libpng 1.6.59, zlib 1.3.1) |
| uharfbuzz / HarfBuzz | 0.56.3 (local wheel) / 14.6.0 |
| skia-pathops | 0.9.2 (local wheel) |
| fontTools | 4.62.1 (Pyodide dist) |
| Pillow / numpy / pygame-ce | 12.2.0 / 2.4.6 / 2.5.7 with SDL 2.32.10 (Pyodide dist) |
| svgelements / pypdf | 1.9.6 / 6.19.0 (PyPI wheels, pre-downloaded to `build/pywheels`, installed from emfs) |
| micropip | 0.11.1 (Pyodide dist) |

Native control (`.venv-native`) differs in: fontTools 4.66.1, Pillow 12.3.0, numpy 2.5.3, pygame-ce 2.5.8, CPython 3.14.6.

## Goldens (`manifest.json`, `compare_vs_golden.json`, `compare_vs_native.json`)
Default run (real `pygame.mixer`): 91 sketches attempted, 87 rendered, 4 errors.

| set | rendered | byte-identical to the Windows golden | differing |
|---|---|---|---|
| Session 1 (13) | 13 | 13 | 0 |
| gallery (78 with a golden) | 74 | 70 | 4 |
| gallery, not rendered | 4 | | music-07_a_songs_fingerprint, music-10_ear_training, projects-04_voice_game, projects-07_scratch_card |

The native renders are byte-identical to the goldens, so the comparison "Pyodide vs native" gives the same four images with the same numbers.

| image | diff px | % | max abs diff | mean abs diff (channels of differing px) | share of diff px in edge mask | bbox x0,y0,x1,y1 |
|---|---:|---:|---:|---:|---:|---|
| gallery/images-01_load_image | 50454 | 19.709 | 87 | 1.439 | 1.0 | 20,26,619,349 |
| gallery/images-02_tint_and_parts | 83123 | 32.470 | 69 | 1.325 | 0.9999 | 10,13,629,364 |
| gallery/images-04_filters | 41874 | 16.357 | 128 | 1.127 | 0.9998 | 8,13,623,362 |
| gallery/projects-05_typographic_portrait | 11297 | 4.184 | 93 | 0.918 | 1.0 | 3,20,597,445 |

Cause: these are exactly the four sketches that load `photo.jpg` through pygame. Decoding that file gives different RGB in Pyodide than
natively (400x300, 35692 of 120000 pixels = 29.7% differ, max 87), and Pyodide's own pygame and Pillow agree with each other
(sha256 prefix 46c7a913c5d3ff5d) while native pygame and Pillow agree with each other (1fb62ea530a25fac). So the JPEG decoder inside
the Pyodide pygame-ce/Pillow builds differs from the native wheels' decoder. cairo is not shown to be involved; the "edge share" is
high only because a photo is textured. All other image sketches (no JPEG) are identical. This was identified by decoding the file, not by
feeding the Pyodide-decoded pixels through native cairo (not done). Diff crops: `diff-samples/` (gain x32, 2x); full diffs are in the gitignored `diff/`.

### Sound
`pygame.mixer.init()` fails in Pyodide under Node ("Couldn't create audio thread startup semaphore": SDL's audio subsystem, even the dummy driver,
needs a thread), so funground raises "sound support is not available on this computer" on the first `f.melody()` / `f.pluck()` / ... This stops
4 golden sketches (above); without the stub, bench op counting also fails for 11 more gallery examples (sound-01..03, music-01..05, 08, 09, 11) including sound-02, which is in the native top 10.
Not verified in a browser (there SDL would use WebAudio, a different path).
Workaround for measuring only: `MIXER_STUB=1` installs `test/node/mixer_stub.py` (no sound, headless only). With it
(`mixerstub/`: `manifest.json`, `compare_vs_golden.json`, `compare_vs_native.json`) 91/91 render, Session 1 13/13 and gallery 74/78 identical, the same 4 JPEG images differing with the same numbers, and the 4 sound sketches byte-identical to the goldens.
The bench in `bench.json` was run with the stub (sound-02_write_a_tune is in the top 10).

## Bench
See [`../bench_comparison.md`](../bench_comparison.md); data `bench.json` (Node, stub mixer) and `../native/bench_rerun.json` (native, run right after, same settings: 30 repetitions after 5 warm-up, same 10 examples).
With the stub, 92 of 93 examples are counted in Node; sound-01_visualiser still errors (it loads a sound file, which the stub does not support). Last-frame op counts equal the native ones for the 10 timed examples; music-11 (110 vs 107) and sound-03 (31 vs 34) differ slightly, both sound/clock-driven examples outside the top 10.
Golden sketch wall time (sum of the 87 that render): 59.0 s in Node vs 24.9 s native (median per sketch 2.4x).

## Not verified
Browsers; a real audio device; the Pyodide-decoded JPEG pixels through native cairo; Pyodide with network-installed (CDN) packages (everything here was local).
