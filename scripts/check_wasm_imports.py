#!/usr/bin/env python3
"""List the imports of wasm side modules (.so) inside wheel(s) and fail if any import is a symbol
that should have been linked in statically (cairo, pixman, libpng, zlib).

Usage: check_wasm_imports.py WHEEL...   (reads the wasm import section directly; no tools needed)
Everything else imported (Python C-API, libc, emscripten runtime) is expected to be provided by
the Pyodide main module at load time.
"""
import re, sys, zipfile, collections

BAD = re.compile(r"^(Sk[A-Z]|_ZN\d*(Sk|sk_|skia)|_?cairo_|_?pixman_|_?png_|png$|deflate|inflate|crc32|adler32|zlib|compress|uncompress|gz[a-z]+$|z_|_tr_)")

def leb(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1
        r |= (x & 0x7F) << s; s += 7
        if not x & 0x80:
            return r, i

def imports(data):
    assert data[:4] == b"\0asm", "not wasm"
    i, out, exports = 8, [], set()
    while i < len(data):
        sid = data[i]; i += 1
        size, i = leb(data, i)
        if sid == 2:
            j = i
            n, j = leb(data, j)
            for _ in range(n):
                l, j = leb(data, j); mod = data[j:j+l].decode(); j += l
                l, j = leb(data, j); name = data[j:j+l].decode(); j += l
                kind = data[j]; j += 1
                if kind == 0: _, j = leb(data, j)                 # func: type idx
                elif kind == 1: j += 1; f = data[j]; j += 1; _, j = leb(data, j); (_, j) = leb(data, j) if f & 1 else (0, j)  # table
                elif kind == 2: f = data[j]; j += 1; _, j = leb(data, j); (_, j) = leb(data, j) if f & 1 else (0, j)        # memory
                elif kind == 3: j += 2                            # global: type, mut
                elif kind == 4: j += 1; _, j = leb(data, j)       # tag
                out.append((mod, name, kind))
        elif sid == 7:
            j = i
            n, j = leb(data, j)
            for _ in range(n):
                l, j = leb(data, j); exports.add(data[j:j+l].decode()); j += l
                j += 1; _, j = leb(data, j)
        i += size
    return out, exports

rc = 0
for whl in sys.argv[1:]:
    with zipfile.ZipFile(whl) as z:
        for n in z.namelist():
            if not n.endswith(".so"):
                continue
            imps, exports = imports(z.read(n))
            bymod = collections.Counter(m for m, _, _ in imps)
            # GOT.func/GOT.mem imports of symbols the module itself exports are its own
            # (hidden-visibility) functions/data whose address is taken; the loader resolves them.
            bad = [(m, nm) for m, nm, _ in imps if BAD.match(nm) and nm not in exports]
            own = sorted({nm for m, nm, _ in imps if BAD.match(nm) and nm in exports})
            py = sorted({nm for _, nm, _ in imps if nm.startswith(("Py", "_Py"))})
            print(f"{whl}:{n}: {len(imps)} imports {dict(bymod)}; {len(py)} Python C-API symbols")
            print("  non-Python imports:", " ".join(sorted({nm for _, nm, _ in imps if nm not in py})))
            if own:
                print(f"  {len(own)} GOT imports resolve to the module's own exports: {' '.join(own)}")
            if bad:
                rc = 1
                print("  UNRESOLVED library symbols:", bad)
            else:
                print("  OK: no cairo/pixman/png/zlib symbols imported")
sys.exit(rc)
