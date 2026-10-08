"""Shared pieces of the S-134 harness: a pytest-free copy of funground's tests/conftest.py helpers.

Runs unchanged in CPython and in Pyodide: only the standard library plus funground's own
dependencies are used (no subprocess, threads, pytest or Pillow).

``run_sketch``, ``script_frame`` and ``reset_funground`` follow funground/tests/conftest.py
line for line; ``gallery_tools`` loads tools/make_gallery.py the way tests/test_gallery.py does.
"""
from __future__ import annotations

import builtins
import contextlib
import importlib.util
import inspect
import os
import sys
import time
import traceback
from pathlib import Path

# Modules whose use is worth reporting per sketch (C extensions and the libraries around them).
WATCHED = ("cairo", "uharfbuzz", "pathops", "pygame", "PIL", "numpy", "fontTools", "svgelements", "pypdf")

# A fixed frame rate so a headless run never sleeps; 30 frames like the tests.
FPS = 1000
FRAMES = 30


def setup_environment(headless: bool = True) -> None:
    """The environment the tests run in (tests/conftest.py, tests/test_gallery.py)."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    if headless:
        os.environ["FUNGROUND_HEADLESS"] = "1"
    else:
        os.environ.pop("FUNGROUND_HEADLESS", None)


def add_funground(path) -> Path:
    """Put the funground checkout (the folder holding the ``funground`` package) on sys.path."""
    root = Path(path).resolve()
    if not (root / "funground" / "__init__.py").exists():
        raise SystemExit(f"{root} does not contain funground/__init__.py")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


# ---- conftest.py ------------------------------------------------------------------------------
def reset_funground():
    """Give the public API a fresh Sketch between tests (conftest.reset_funground)."""
    from funground import api
    from funground.sketch import Sketch

    sketch = api.use_sketch(Sketch())
    sketch.random_seed(0)
    return sketch


def end_test() -> None:
    """The autouse fixture's teardown: quit pygame if it is up, then a fresh Sketch again."""
    pygame = sys.modules.get("pygame")
    if pygame is not None and pygame.get_init():
        pygame.quit()
    reset_funground()


def script_frame(sketch):
    """A script (S-076) never calls f.run(): its frame is the finished canvas (conftest.script_frame)."""
    from funground.platform.headless import HeadlessPlatform

    sketch._script_flush()
    sketch.last_ops = sketch.frame.ops
    platform = HeadlessPlatform()
    platform.present(sketch._view_pixels())
    return platform.capture()


def run_sketch(path, frames: int = FRAMES, fps: int = FPS):
    """Execute a learner sketch file unchanged, stopping after *frames* (conftest.run_sketch).

    Returns ``((width, height), rgb_bytes)`` of the final frame.
    """
    import funground
    from funground import api

    path = Path(path)
    source = path.read_text(encoding="utf-8")
    namespace: dict[str, object] = {"__name__": "__sketch__", "__file__": str(path)}

    def harness_run(*, fps=fps, max_frames=frames):
        caller = inspect.currentframe().f_back
        api.active_sketch().run_namespace(caller.f_globals, fps=fps, max_frames=max_frames)

    def harness_show():
        pass            # a script's f.show() would wait for a window to be closed (S-076)

    original_run, original_show = funground.run, funground.show
    funground.run, funground.show = harness_run, harness_show
    try:
        exec(compile(source, str(path), "exec"), namespace)
    finally:
        funground.run, funground.show = original_run, original_show

    active = api.active_sketch()
    if active.last_frame is None and active._script:
        return script_frame(active)
    frame = active.last_frame
    assert frame is not None, "sketch did not reach max_frames"
    return frame


# ---- gallery ----------------------------------------------------------------------------------
def gallery_tools(root: Path):
    """tools/make_gallery.py loaded as tests/test_gallery.py loads it (example list, ids, flags)."""
    tool = root / "tools" / "make_gallery.py"
    spec = importlib.util.spec_from_file_location("make_gallery", tool)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---- bookkeeping ------------------------------------------------------------------------------
class ImportTracker:
    """Records which watched top-level modules are *requested* while a sketch runs.

    Wraps ``builtins.__import__`` so that a lazy ``import pathops`` inside a function is seen
    even when the module was already loaded by an earlier sketch.
    """

    def __init__(self) -> None:
        self.seen: set[str] = set()
        self._orig = None

    def _hook(self, name, globals=None, locals=None, fromlist=(), level=0):
        if level == 0:
            top = name.partition(".")[0]
            if top in WATCHED:
                self.seen.add(top)
        return self._orig(name, globals, locals, fromlist, level)

    @contextlib.contextmanager
    def active(self):
        self.seen = set()
        self._orig = builtins.__import__
        builtins.__import__ = self._hook
        try:
            yield self
        finally:
            builtins.__import__ = self._orig


def purge_funground() -> None:
    """Forget funground's own modules so the next import re-runs their imports.

    C extensions stay loaded (they cannot be re-initialised), but the ImportTracker still sees
    every ``import cairo`` / ``import uharfbuzz`` / ``import pathops`` that funground makes again,
    so each sketch is credited with exactly the modules a fresh process would have needed."""
    for name in [n for n in sys.modules if n == "funground" or n.startswith("funground.")]:
        del sys.modules[name]


class _CountingModule:
    """Stands in for a C-extension module inside funground and counts the names looked up on it."""

    def __init__(self, module, counts: dict) -> None:
        object.__setattr__(self, "_module", module)
        object.__setattr__(self, "_counts", counts)

    def __getattr__(self, name):
        counts = object.__getattribute__(self, "_counts")
        counts[name] = counts.get(name, 0) + 1
        return getattr(object.__getattribute__(self, "_module"), name)


def install_usage_counters() -> dict:
    """Count run-time use of uharfbuzz (funground.typography.hb) and skia-pathops (funground.pathops._sk).

    Call after ``import funground`` (module-level uses at import time are not counted). Returns
    {"uharfbuzz": {name: n}, "pathops": {name: n}}, filled while the sketch runs."""
    counts = {"uharfbuzz": {}, "pathops": {}}
    typography = sys.modules.get("funground.typography")
    if typography is not None and hasattr(typography, "hb"):
        typography.hb = _CountingModule(typography.hb, counts["uharfbuzz"])
    fpathops = sys.modules.get("funground.pathops")
    if fpathops is not None and hasattr(fpathops, "_sk"):
        fpathops._sk = _CountingModule(fpathops._sk, counts["pathops"])
    return counts


def native_modules() -> list[str]:
    """Loaded modules that live in a compiled file (.so/.pyd/.wasm), by top-level name."""
    found = set()
    for name, mod in list(sys.modules.items()):
        file = getattr(mod, "__file__", None) or ""
        if file.endswith((".so", ".pyd", ".wasm")):
            found.add(name)
    return sorted(found)


def funground_modules() -> list[str]:
    return sorted(n for n in sys.modules if n == "funground" or n.startswith("funground."))


def environment_info() -> dict:
    import platform

    info = {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
            "platform": sys.platform, "machine": platform.machine(),
            "env": {k: os.environ.get(k) for k in ("FUNGROUND_HEADLESS", "FUNGROUND_BACKING_SCALE",
                                                   "PIXMAN_DISABLE", "SDL_VIDEODRIVER")}}
    try:
        import cairo
        info["pycairo"] = cairo.version
        info["cairo"] = cairo.cairo_version_string()
    except Exception as exc:                       # pragma: no cover
        info["cairo_error"] = repr(exc)
    for mod, attr in (("pygame", "ver"), ("uharfbuzz", "__version__"), ("pathops", "__version__"),
                      ("fontTools", "version")):
        m = sys.modules.get(mod)                   # only report what the run actually loaded
        info[mod] = str(getattr(m, attr, "loaded")) if m is not None else "not imported"
    return info


def exception_text() -> str:
    return traceback.format_exc()


now = time.perf_counter
