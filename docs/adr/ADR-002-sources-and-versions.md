# ADR-002: Source versions and where they come from

**Status:** accepted for the spike (8 October 2026). **Decision:** D-002.

## Context

funground's goldens (`tests/golden/`) were made on Windows with the PyPI wheel
`pycairo-1.29.2-cp3xx-win_amd64`, which links **cairo 1.18.6** statically (the version string
is in `_cairo.pyd`). cairographics.org and freedesktop's GitLab are blocked in the sandbox, and
there is no GitHub mirror of cairo. The Ubuntu archive pool carries upstream tarballs unchanged
(`*.orig.tar.*`) up to **cairo 1.18.4** and **pixman 0.46.4**.

## Decision

- cairo 1.18.4, pixman 0.46.4, libpng 1.6.59, zlib 1.3.1, pycairo 1.29.2, all pinned by sha256
  in `sources.sha256`.
- The native Linux control is built from the **same** tarballs with the same meson options, so
  the wasm-vs-native comparison isolates the effect of compiling to wasm.

## Consequences

- A difference between our renders and the Windows goldens may come from the version gap
  (1.18.4 vs 1.18.6), from pixman (version in the Windows wheel unknown), or from Windows vs
  Linux compilers, not from wasm. The three-way comparison (architecture.md) tells them apart.
- To close the gap later: fetch cairo 1.18.6 from cairographics.org in CI (open network) and
  rerun the comparison. Recorded as an open item in RESULTS.md.
