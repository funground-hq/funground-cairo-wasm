# Decision log

One row per decision taken in this repository. Reasoning lives in the linked ADR or sprint
document. Status: `accepted` · `pending` · `superseded by D-nnn`.

| ID | Date | Decision | Options | Outcome | Where |
|---|---|---|---|---|---|
| D-001 | 2026-10-08 | Build route for the wheel | A pyodide-build directly · B cibuildwheel 4 · C pyodide-recipes recipe | **A** — works offline; CI runs the same scripts | ADR-001 |
| D-002 | 2026-10-08 | Source versions and origin | upstream sites (blocked) · Ubuntu archive orig tarballs | **cairo 1.18.4, pixman 0.46.4, libpng 1.6.59, zlib 1.3.1** from the Ubuntu archive, sha256-pinned; native control from the same sources | ADR-002 |
| D-003 | 2026-10-08 | How to judge golden identity | compare with Windows goldens only · three-way (goldens, native Linux control, Pyodide) | **three-way** — separates wasm effects from version and platform effects | architecture.md |
| D-004 | 2026-10-08 | uharfbuzz for text goldens (S-133) | build it · use the `pyemscripten_2026_0` wheel uharfbuzz 0.56.3 publishes on PyPI | **use PyPI's wheel** if it imports and shapes; build only if it fails | sprint-01 stories |
| D-005 | 2026-10-08 | skia-pathops in Pyodide | skip goldens that need it · stub it · build it | **build it** — `import funground` imports pathops unconditionally, so every golden needs it; built from the 0.9.2 sdist with Skia's own gn/ninja for `target_cpu="wasm"`, no source changes | sprint-01 stories S-134.5 |
| D-006 | 2026-10-08 | What "ms per frame" means for criterion (c) | full frame only · replay only · both | **both**: (1) replay of a captured frame's IR by `CairoRenderer` at 640×400 and 1280×800 (`attach(w·d, h·d, fit·d)`, funground's own HiDPI path), the cost Cairo adds; (2) the full headless frame (`draw()` + render) at 1× and with `FUNGROUND_BACKING_SCALE=2`. Top 10 by last-frame op count, as the brief says; the peak-op redraw-on-change example (projects-05, 1377 ops) reported as a supplement. Node and native timed back to back on the same machine | `harness/bench.py`; `results/bench_comparison.md` |
| D-007 | 2026-10-08 | How to read criterion (c) now that Python `draw()` dominates frame time | A apply §6 rule: (c) fails → B · B restate (c) as a render budget and decide after S-135 + Chrome timings · C accept C with a heavy-sketch caveat | **pending (maintainer)** — recommended B | RESULTS.md "Decision needed" |
