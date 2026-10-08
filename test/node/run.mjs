// Run the S-134 harness (golden renders and/or benchmark) in Pyodide under plain Node (no npm install).
//   PYODIDE_DIST=/path/to/pyodide  FUNGROUND=/path/to/funground  WHEELS=dist  PYWHEELS=build/pywheels \
//   OUT=results/pyodide  MODE=goldens|bench|all  node test/node/run.mjs [-- extra bench.py args]
// Env: BENCH_ARGS / GOLDEN_ARGS (extra args for bench.main / render_goldens.main, space separated), BENCH_OUT.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../..");
const env = process.env;
const dist = path.resolve(env.PYODIDE_DIST || "/home/user/pyodide-dist/pyodide");
const fungroundDir = path.resolve(env.FUNGROUND || "/home/user/funground-hq/funground");
const wheelDir = path.resolve(env.WHEELS || path.join(repo, "dist"));
const pyWheelDir = path.resolve(env.PYWHEELS || path.join(repo, "build/pywheels"));
const outDir = path.resolve(env.OUT || path.join(repo, "results/pyodide"));
const mode = env.MODE || "all";
if (!["goldens", "bench", "all"].includes(mode)) throw new Error("MODE must be goldens|bench|all");
const split = (s) => (s ? s.split(/\s+/).filter(Boolean) : []);
fs.mkdirSync(outDir, { recursive: true });

const { loadPyodide } = await import(pathToFileURL(path.join(dist, "pyodide.mjs")).href);
const py = await loadPyodide({
  indexURL: dist,
  env: { PYTHONDONTWRITEBYTECODE: "1", SDL_VIDEODRIVER: "dummy", SDL_AUDIODRIVER: "dummy", FUNGROUND_HEADLESS: "1" },
  stdout: (s) => console.log(s),
  stderr: (s) => console.error(s),
});

// Pyodide distribution packages (from the local dist, no network), then local wheels.
await py.loadPackage(["micropip", "fonttools", "pillow", "numpy", "pygame-ce"]);
const micropip = py.pyimport("micropip");
const install = async (dir, filter) => {
  for (const w of fs.readdirSync(dir).filter(filter).sort()) {
    py.FS.writeFile("/tmp/" + w, fs.readFileSync(path.join(dir, w)));
    await micropip.install("emfs:/tmp/" + w, { deps: false });
    console.log("installed", w);
  }
};
await install(wheelDir, (f) => f.endsWith("-pyemscripten_2026_0_wasm32.whl"));
if (fs.existsSync(pyWheelDir)) await install(pyWheelDir, (f) => f.endsWith(".whl"));

// Mounts: funground checkout, this repo, output dir. NODEFS has no read-only option; the harness never writes
// into funground/ or the repo (bytecode off), and scripts/run_node_tests.sh checks `git status` of the checkout.
const NODEFS = py.FS.filesystems.NODEFS;
const mount = (hostPath, mp) => {
  py.FS.mkdirTree(mp);
  py.FS.mount(NODEFS, { root: hostPath }, mp);
};
mount(fungroundDir, "/funground");
mount(repo, "/repo");
mount(outDir, "/out");

py.runPython(`
import sys, os
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path.insert(0, "/repo/harness")
`);

// Versions.
const versions = JSON.parse(py.runPython(`
import sys, json, importlib
def v(mod, *attrs):
    try:
        m = importlib.import_module(mod)
    except Exception as e:
        return "NOT AVAILABLE: " + repr(e)
    for a in attrs:
        if hasattr(m, a):
            return str(getattr(m, a))
    return "loaded"
import cairo, uharfbuzz
info = {"python": sys.version, "pycairo": cairo.version, "cairo": cairo.cairo_version_string(),
        "uharfbuzz": uharfbuzz.__version__, "harfbuzz": uharfbuzz.version_string(),
        "pathops": v("pathops", "__version__"), "fontTools": v("fontTools", "version"),
        "pypdf": v("pypdf", "__version__"), "svgelements": v("svgelements", "SVGELEMENTS_VERSION"),
        "Pillow": v("PIL", "__version__"), "numpy": v("numpy", "__version__"),
        "pygame-ce": v("pygame", "ver")}
json.dumps(info)
`));
const header = { pyodide: py.version, node: process.version, v8: process.versions.v8, ...versions };
console.log("VERSIONS " + JSON.stringify(header, null, 1));
fs.writeFileSync(path.join(outDir, "versions.json"), JSON.stringify(header, null, 1));

const runMain = (modName, args) => {
  py.globals.set("_args", args);
  py.runPython(`
import importlib, sys
_m = importlib.import_module(${JSON.stringify(modName)})
_rc = _m.main(list(_args.to_py() if hasattr(_args, "to_py") else _args))
`);
  return py.globals.get("_rc");
};

let rc = 0;
if (mode === "goldens" || mode === "all") {
  const args = ["--funground", "/funground", "--out", "/out", "--gallery", ...split(env.GOLDEN_ARGS)];
  rc ||= runMain("render_goldens", args);
}
if (mode === "bench" || mode === "all") {
  const benchOut = env.BENCH_OUT || "/out/bench.json";
  const args = ["--funground", "/funground", "--out", benchOut, ...split(env.BENCH_ARGS)];
  rc ||= runMain("bench", args);
}
process.exit(rc ? 1 : 0);
