# funground-cairo-wasm

WebAssembly (Pyodide) builds of the three C extensions funground needs - pycairo (with cairo and
pixman), uharfbuzz and skia-pathops - so funground's own renderer, text shaping and export can run
unchanged in the browser. Part of funground 0.2's web target (epic E-31, decision D-074).

**Process:** follow the `funground-sdlc` skill (`.claude/skills/funground-sdlc/SKILL.md`) in every
session: sprints, stories, design notes, ADRs, decision log, sprint reviews, model economy, git rules.

## Relation to funground

- `funground-hq/funground` (branch `release-0.2-web`) is the product and the reference. Read it; never
  change it from this repository.
- The question and pass/fail criteria live there: `docs/design/Web_Target_Options.md` (section 3C,
  section 6). Stories here are funground's: S-134 (pycairo), S-133 (uharfbuzz), S-138 (files on the web).
- Records specific to this repository use the prefix `CW-` (`CW-ADR-001`, `CW-D-001`).

## Local rules

- Work on a branch and push it; `main` changes by pull request.
- Builds run in a cloud sandbox or GitHub Actions, never on the maintainer's machine (no C toolchain
  there). Record every tool's exact version (Emscripten, Pyodide, pyodide-build, library versions).
- Results go in `spikes/RESULTS.md` (or `RESULTS.md` at the root for the first spike) with the
  criteria, the numbers and how they were measured.
