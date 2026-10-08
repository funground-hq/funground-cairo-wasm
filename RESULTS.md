# S-134 results: pycairo (cairo + pixman) in Pyodide 314.0.7

**Spike:** S-134, funground 0.2 web target, architecture C (`Web_Target_Options.md` §3C, §6 row 2).
**Date:** 8 October 2026. **Branch:** `claude/cloud-session-start-v8c54n`. funground was read at
`release-0.2-web` `518c7df` and not changed.

## Verdict

| Criterion | Target | Result | |
|---|---|---|---|
| (a) builds | pycairo with cairo + pixman as a Pyodide 314 wheel | Built, loads and draws in Pyodide; CI rebuilds it | **PASS** |
| (b) goldens byte-identical | the Session-1 goldens | **13 of 13 byte-identical** (`11_delta_time` has no golden; there are 13, not 14) | **PASS** |
| (b′) gallery goldens (extra) | — | 70 of 74 rendered identical; the 4 others decode `photo.jpg` differently (JPEG decoder, not cairo, see below); 4 need sound | pass for cairo |
| (c) frame time | ≤ 12 ms mean at 640×400 × DPR 2 (1280×800) | Cairo replay in Node: **16.5 ms mean**, 5 of 10 ≤ 12 ms; ≈ 2.0× native. Full frame at 2× (Python `draw()` + render): 66.5 ms mean, 0 of 8 loop examples ≤ 12 ms, natively also 0 of 8 | **FAIL** (see "What (c) really measures") |
| (d) size | the three wheels add ≤ 6 MB | **1.65 MB** | **PASS** |

```
            Cairo replay of one frame at 1280×800 (median ms, 10 heaviest gallery examples)
 native   ███████▊                                        7.8 mean
 Node     ████████████████▌                              16.5 mean     budget ──► 12 ms
                                                │
            Full frame at 2×: where the time goes (mean of the 8 loop examples, ms)
 native   draw ██████████████████▌ 18.5 │ render ██████████▋ 10.6
 Node     draw ██████████████████████████████████████████████▌ 46.5 │ render ██████████████████▊ 18.8
```

**Reading:** Cairo itself runs in wasm at about half native speed (ratio 1.4–2.8, mean 2.0 at
1280×800). That puts the average heavy frame over the 12 ms budget (16.5 ms). But the larger cost is
Python: the sketches' own `draw()` code takes 2.5× longer than rendering in Node. Native CPython does
not meet 12 ms for full frames of these examples either, and route B (Canvas 2D) would pay the same
Python cost. So by the letter of §6 row 2, (c) fails, which points to B. Our numbers suggest the 12 ms
gate can't separate B from C as written. The maintainer has to rule on it; see "Decision needed" below.

## Versions

| Piece | Version | Note |
|---|---|---|
| Pyodide | 314.0.7 | CPython 3.14.2, ABI `2026_0`, wheel platform `pyemscripten_2026_0_wasm32` |
| Emscripten | 5.0.3 (LLVM 22) | from the xbuildenv's `PYODIDE_EMSCRIPTEN_VERSION` |
| pyodide-build | 0.39.1 | host CPython 3.14.6 (uv) |
| cairo | 1.18.4 | the goldens' Windows wheel bundles 1.18.6 (ADR-002); no pixel effect seen |
| pixman | 0.46.4 | generic C paths only: pixman has no wasm SIMD |
| libpng / zlib | 1.6.59 / 1.3.1 | |
| pycairo | 1.29.2 | built from the PyPI sdist |
| skia-pathops | 0.9.2 | built here: funground imports it unconditionally (CW-D-005) |
| uharfbuzz | 0.56.3 (HarfBuzz 14.6.0) | PyPI's own `pyemscripten_2026_0` wheel, not built (CW-D-004) |
| From the Pyodide distribution | fontTools 4.62.1, Pillow 12.2.0, numpy 2.4.6, pygame-ce 2.5.7, micropip 0.11.1 | |
| From PyPI (pure Python) | svgelements 1.9.6, pypdf 6.19.0 | installed with micropip from local files |
| Node | 22.22.0 (V8 12.4) | Intel Xeon 2.8 GHz, 4 vCPUs |
| Native control | CPython 3.14.6, gcc 13.3, same C sources and meson options | |

## (a) What built

- **cairo:** static, with no threads (`CAIRO_NO_MUTEX`; Pyodide is single-threaded). Surfaces:
  image, PNG, PDF, PS, SVG, recording, script, tee. No FreeType, fontconfig, X11 or glib.
  funground draws text as paths, so nothing is lost: every text golden matches.
- **pixman:** static, generic C.
- **pycairo:** one side module (`_cairo.so`, a wasm library Pyodide loads into its main program),
  with cairo, pixman, libpng and zlib linked inside. Its imports were checked: none are left
  unresolved.
- **skia-pathops:** Skia built with its own gn/ninja for `target_cpu="wasm"` (about 4 min), then the
  wheel with `pyodide build`. No source changes.
- **CI:** `.github/workflows/build.yml` rebuilds all three wheels on a clean `ubuntu-24.04` runner,
  runs the import check and the Node smoke test, and uploads the artifact `wheels`. The first full
  run passed in about 6 minutes ([run 37764610483](https://github.com/funground-hq/funground-cairo-wasm/actions/runs/37764610483)).

### Patches

| Patch | Why |
|---|---|
| `patches/pixman/0001-emscripten-no-pthread.patch` | `dependency('threads')` put `-pthread` into `pixman-1.pc`; shared-memory wasm cannot link into a Pyodide side module |
| `patches/cairo/0001-emscripten-no-pthread-no-mutex.patch` | emcc passes cairo's pthread probe; skip it on Emscripten and use no-op mutexes |
| `patches/cairo/0002-image-source-atomic-ptr-cast.patch` | three pointer casts at `_cairo_atomic_ptr_cmpxchg`: clang 22 makes the type mismatch an error, gcc only warns |

## (b) Goldens

Three-way comparison (CW-D-003): the Windows goldens, a native Linux build from the same sources, and
Pyodide in Node. All images are compared byte for byte, then per pixel.

| Set | Native vs golden | Pyodide vs golden | Pyodide vs native |
|---|---|---|---|
| Session 1 (13 goldens) | 13 identical | **13 identical** | 13 identical |
| Gallery (78 goldens) | 78 identical | 70 identical, 4 differ, 4 not run | same 4 differ |
| Gallery, mixer stubbed | — | 74 identical, same 4 differ | same 4 differ |

- **The cairo version gap and the compilers make no difference.** cairo 1.18.4 built with gcc on Linux
  matches the Windows goldens (cairo 1.18.6) everywhere, with or without pixman's x86 SIMD.
- **The four differing images** are exactly the four sketches that load `photo.jpg`
  (`images-01_load_image`, `images-02_tint_and_parts`, `images-04_filters`,
  `projects-05_typographic_portrait`). Decoding the JPEG alone gives different pixels in Pyodide
  (29.7 % of pixels, max |Δ| 87). Pyodide's Pillow and pygame-ce agree with each other, and so do the
  native ones, so the JPEG decoder in Pyodide's builds differs.

  | Image | Differing px | Max \|Δ\| | Mean \|Δ\| |
  |---|---:|---:|---:|
  | images-01_load_image | 50 454 (19.7 %) | 87 | 1.44 |
  | images-02_tint_and_parts | 83 123 (32.5 %) | 69 | 1.33 |
  | images-04_filters | 41 874 (16.4 %) | 128 | 1.13 |
  | projects-05_typographic_portrait | 11 297 (4.2 %) | 93 | 0.92 |

  These are not edge-only differences: they cover the photo's area. **Cairo is clean on all four**
  (`results/jpeg-check/`): with the photo given to both sides as a lossless PNG, images-01, -02 and -04 are
  byte-identical between Pyodide and native. projects-05 keeps 622 pixels off by 1 level on letter edges. The
  cause is pygame-ce's `smoothscale` (used by `picture.resize()`), which runs its SSE2 backend natively and
  GENERIC in Pyodide. Forcing GENERIC natively makes the two renders byte-identical. pixman SIMD has no effect.
- **Sound:** `pygame.mixer.init()` cannot start in Pyodide under Node ("Couldn't create audio thread
  startup semaphore"), so 4 gallery goldens with sound fail to run (`music-07`, `music-10`,
  `projects-04`, `projects-07`). With `MIXER_STUB=1`, a silent stand-in used for measuring only, they
  render byte-identical. Browser audio is a separate path (S-137) and was not tested.

Diff crops (gain ×32): `results/pyodide/diff-samples/`. Data: `results/pyodide/compare_vs_*.json`.

## (c) Frame time

The 10 gallery examples with the most IR ops in their 30th frame. Each was timed 30 times after 5
warm-up runs, and the table shows the median in ms. Node and native ran back to back on the same
machine (CW-D-006). Full table: `results/bench_comparison.md`.

- **Replay** = `CairoRenderer` replaying the captured frame's IR onto a surface. 1280×800 uses
  funground's own HiDPI path (`attach(w·2, h·2, scale·2)`). This is what Cairo costs per frame.
- **Full 2×** = one headless loop iteration (`draw()` + render) with `FUNGROUND_BACKING_SCALE=2`.

| Example | Ops | Replay 1280×800 Node | Native | × | Full 2× Node | Native |
|---|---:|---:|---:|---:|---:|---:|
| projects-02_rangoli | 636 | 12.8 | 9.1 | 1.4 | 33.1 | 17.6 |
| projects-06_kinetic_type | 633 | 22.2 | 11.0 | 2.0 | 126.1 | 51.5 |
| text-09_text_dots | 507 | 27.5 | 9.7 | 2.8 | 61.7 | 25.5 |
| randomness-03_noise | 419 | 4.7 | 2.4 | 1.9 | 32.8 | 15.2 |
| sound-02_write_a_tune | 413 | 10.8 | 7.6 | 1.4 | 162.6 | 63.6 |
| randomness-02_gaussian_and_choice | 401 | 11.1 | 6.5 | 1.7 | 29.7 | 16.0 |
| studios-03_rhythm *(script)* | 371 | 8.3 | 4.2 | 2.0 | n/a | n/a |
| studios-05_text_as_geometry *(script)* | 290 | 6.3 | 3.2 | 2.0 | n/a | n/a |
| paths-06_outlines | 249 | 19.2 | 8.8 | 2.2 | 37.9 | 16.8 |
| studios-06_poster_series | 229 | 41.8 | 15.6 | 2.7 | 48.3 | 30.6 |
| **Mean** | | **16.5** | **7.8** | **2.0** | 66.5 ¹ | 29.6 ¹ |
| **≤ 12 ms** | | **5 of 10** | 9 of 10 | | 0 of 8 | 0 of 8 |

¹ Mean of the 8 loop examples. studios-03 and -05 are scripts with no frame loop.

- **Where full-frame time goes, 2×, mean of the 8 loop examples:**

  | | `draw()` (Python) | render (Cairo) |
  |---|---:|---:|
  | Node | 46.5 ms | 18.8 ms |
  | native | 18.5 ms | 10.6 ms |
- **Ratios.** Node/native is about 2.0–2.5× for both the Python and the C side. That is better than
  Pyodide's 3–5× rule of thumb for Python.
- **Peak frame (supplement).** projects-05_typographic_portrait redraws only on change. Its peak
  frame (1 377 ops) replays in 210 ms in Node and 85 ms natively at 1280×800.
- **What (c) really measures.** The gate was written as "average ≤ 12 ms a frame". Cairo alone
  averages 16.5 ms over these heavy examples, so C fails it. But the Python half alone (46.5 ms) is
  over budget too, and B would not remove it. Typical gallery sketches (fewer ops) are well under
  budget: the 6th to 10th heaviest replay in 4.7–12.8 ms.

## (d) Size

| Wheel | Raw | gzip -9 | brotli -q 11 | `.so` inside, raw / brotli |
|---|---:|---:|---:|---:|
| pycairo-1.29.2-cp314-cp314-pyemscripten_2026_0_wasm32 | 496 371 | 495 667 | 496 376 | 1 188 873 / 358 271 |
| skia_pathops-0.9.2-cp310-abi3-pyemscripten_2026_0_wasm32 | 172 919 | 172 304 | 172 924 | 452 130 / 139 048 |
| uharfbuzz-0.56.3-cp310-abi3-pyemscripten_2026_0_wasm32 | 981 875 | 980 933 | 981 880 | 4 343 574 / 639 575 |
| **Total** | **1 651 165 (1.65 MB)** | | | |

Wheels are zip archives that are already compressed, so gzip and brotli gain nothing on top. The
download is the raw wheel size. Pyodide itself and its packages (fontTools, Pillow, numpy,
pygame-ce) are not counted; that budget belongs to S-139.

## Problems met

1. **Blocked hosts in the sandbox:** `pyodide.github.io`, jsDelivr, cairographics.org and freedesktop
   GitLab. The xbuildenv and the Pyodide distribution came from GitHub releases, and the C sources
   from the Ubuntu archive, all sha256-pinned (ADR-001, ADR-002). CI uses the same sources.
2. **cairo 1.18.6 sources unreachable:** we built 1.18.4. It matches the 1.18.6 goldens anyway.
3. **Threads:** both libraries detect pthreads under emcc. Patched out (see Patches).
4. **`pkg-config --static`:** in the wasm prefix, `cairo.pc` lists its dependencies under `Requires`,
   so no wrapper was needed. The native build needed a `--static` wrapper.
5. **No sound in Node:** `pygame.mixer` can't start. A measurement-only stub is used for the bench.
6. **JPEG decoding differs** in Pyodide's Pillow and pygame-ce, and pygame-ce's `smoothscale` uses a
   different backend (GENERIC vs SSE2). Both are outside cairo (see (b)).

## Not verified

- **Chrome on the teaching machine and a low-end Chromebook.** Every timing here is Node 22 on a 2.8 GHz
  Xeon. Chrome has the same V8, but a different CPU and browser overhead.
- **Presenting a frame in the browser** (BGRA → canvas) is not timed.
- **Bit-identical wheel rebuilds:** two pycairo builds gave the same size and pixel hash. The wheel
  bytes were not compared.
- **Pyodide from its CDN with micropip:** packages here were installed from local files.
- **Browser audio**, and file outputs (PDF/SVG bytes vs desktop): that is S-138.
- **pixman version in the Windows wheel:** unknown, but the native comparison shows no pixel effect.

## Decision needed (maintainer)

The §6 rule says that if (c) fails, take architecture B. We recommend not applying it mechanically:

- **A.** Apply the rule as written: (c) fails, take B.
- **B.** Restate (c) as a render budget for typical sketches. Compare Cairo-in-wasm replay with Canvas 2D
  replay of the same IR in Chrome (S-135), and measure in Chrome on the teaching machine before deciding.
- **C.** Accept C with a "heavy sketch" caveat, and optimise later.

**Recommended: B.** Cairo is 2× native in wasm, fully byte-identical on Session 1, and 1.65 MB. The
frame budget is dominated by Python, which both architectures share.
