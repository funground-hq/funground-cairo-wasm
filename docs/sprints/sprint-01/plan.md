# Sprint 01 — spike S-134: pycairo in Pyodide

**Dates:** 8 October 2026, time-boxed to the spike (3–4 days in funground's plan).
**Goal:** answer S-134's four criteria with numbers: (a) builds, (b) goldens byte-identical,
(c) frame time, (d) wheel size. Change nothing in funground.

## Inputs

- funground `release-0.2-web` at `518c7df`: `docs/design/Web_Target_Options.md` §3C, §6 row 2.
- Pyodide 314.0.7 (CPython 3.14.2, Emscripten 5.0.3, ABI 2026_0).

## Stories (detail in `stories.md`)

| ID | Story | Owner |
|---|---|---|
| S-134.1 | Toolchain installed and versions recorded | orchestrator |
| S-134.2 | Static cairo + pixman + libpng + zlib and the pycairo wheel for wasm | build agent |
| S-134.3 | Native Linux control from the same sources; shared golden and benchmark harness | harness agent |
| S-134.4 | Pyodide-in-Node runner; goldens compared three ways | test agent |
| S-134.5 | Text: uharfbuzz (PyPI wasm wheel) and skia-pathops if the goldens need them | build agent |
| S-134.6 | Frame times: 10 heaviest gallery examples, 640×400 and 1280×800, Node vs native | test agent |
| S-134.7 | Wheel sizes raw, gzip, brotli | orchestrator |
| S-134.8 | CI workflow rebuilding the wheel | CI agent |
| S-134.9 | RESULTS.md and sprint review | orchestrator |

## Order

```
S-134.1 ──► S-134.2 ──► S-134.5 ──► S-134.4 ──► S-134.6 ──► S-134.7 ──► S-134.9
        └─► S-134.3 (in parallel with .2) ──┘          └─► S-134.8
```

## Risks

- cairo or pixman fail to build with Emscripten (pixman's SIMD paths, cairo's thread checks).
- skia-pathops has no wasm wheel; funground imports it from `paths.py` and `svg.py`.
- Goldens differ because of the cairo version gap (ADR-002), not because of wasm.
- Node timing is a stand-in for Chrome on the teaching machine: same V8, but no browser
  overhead and a different CPU. Recorded as unverified.

## Agents and models

Well-defined coding (scripts, harness, CI) goes to Sonnet agents with full specs. Orchestration,
decisions, the comparison verdict and RESULTS.md stay with the main session.
