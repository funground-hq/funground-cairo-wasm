# Decision log

One row per decision taken in this repository. Reasoning lives in the linked ADR or sprint
document. Status: `accepted` · `pending` · `superseded by D-nnn`.

| ID | Date | Decision | Options | Outcome | Where |
|---|---|---|---|---|---|
| D-001 | 2026-10-08 | Build route for the wheel | A pyodide-build directly · B cibuildwheel 4 · C pyodide-recipes recipe | **A** — works offline; CI runs the same scripts | ADR-001 |
| D-002 | 2026-10-08 | Source versions and origin | upstream sites (blocked) · Ubuntu archive orig tarballs | **cairo 1.18.4, pixman 0.46.4, libpng 1.6.59, zlib 1.3.1** from the Ubuntu archive, sha256-pinned; native control from the same sources | ADR-002 |
| D-003 | 2026-10-08 | How to judge golden identity | compare with Windows goldens only · three-way (goldens, native Linux control, Pyodide) | **three-way** — separates wasm effects from version and platform effects | architecture.md |
| D-004 | 2026-10-08 | uharfbuzz for text goldens (S-133) | build it · use the `pyemscripten_2026_0` wheel uharfbuzz 0.56.3 publishes on PyPI | **use PyPI's wheel** if it imports and shapes; build only if it fails | sprint-01 stories |
