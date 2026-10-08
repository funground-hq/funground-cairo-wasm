# Native control (Linux x86_64, gcc 13.3, Python 3.14.6) vs the Windows goldens

Build: zlib 1.3.1, libpng 1.6.59, pixman 0.46.4, cairo 1.18.4 (static, -fPIC, no FreeType/fontconfig/X11/glib),
pycairo 1.29.2 from sdist, statically linked (`ldd _cairo*.so`: only libm, libc). Details: `build_report.txt`.
Goldens: Windows, PyPI pycairo 1.29.2 wheel = cairo 1.18.6.

| set | images | byte-identical to golden | differing |
|---|---|---|---|
| Session 1 (13 sketches, 11_delta_time has no golden) | 13 | 13 | 0 |
| gallery (deterministic examples with a golden) | 78 | 78 | 0 |

With `PIXMAN_DISABLE="mmx sse2 ssse3"` (x86 SIMD off, as in wasm; pixman printed the three "Disabled" lines):
`results/native-nosimd/`: 91/91 identical to the golden and to `results/native/`. SIMD does not change pixels here.

Imports (manifest.json): `import funground` loads cairo, uharfbuzz, skia-pathops and fontTools unconditionally;
at run time uharfbuzz is called by 05_text, 13_transforms, 14_paths and most gallery sketches; pathops is called
only by some gallery examples (shapes-04, text-05, paths-05/06, images-05, projects-01/02, studios-04/05) and by no
Session-1 sketch. pygame (C extension) is imported only by a few gallery examples that use pygame directly.

Bench (`bench.json`): 93 gallery examples counted, top 10 timed; medians in ms, see the file for means and spread.
