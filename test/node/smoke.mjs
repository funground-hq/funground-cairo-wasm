// Smoke test: load Pyodide in Node, install the locally built wheels, exercise pycairo
// (and uharfbuzz / skia-pathops if their wheels are in dist/).
//   PYODIDE_DIST=/path/to/unpacked/pyodide  WHEEL_DIR=dist  node test/node/smoke.mjs
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "../..");
const dist = process.env.PYODIDE_DIST || "/home/user/pyodide-dist/pyodide";
const wheelDir = path.resolve(process.env.WHEEL_DIR || path.join(repo, "dist"));
const fontPath = process.env.FONT_TTF ||
  "/home/user/funground-hq/funground/funground/fonts/DejaVuSans.ttf";

const { loadPyodide } = await import(pathToFileURL(path.join(dist, "pyodide.mjs")).href);
const py = await loadPyodide({ indexURL: dist, stdout: (s) => console.log(s), stderr: (s) => console.error(s) });
console.log("Pyodide", py.version, "| Python", py.runPython("import sys; sys.version.split()[0]"));

await py.loadPackage("micropip");
const micropip = py.pyimport("micropip");

const wheels = fs.readdirSync(wheelDir).filter((f) => f.endsWith("-pyemscripten_2026_0_wasm32.whl")).sort();
if (!wheels.some((w) => w.startsWith("pycairo-"))) throw new Error("no pycairo wheel in " + wheelDir);
for (const w of wheels) {
  py.FS.writeFile("/tmp/" + w, fs.readFileSync(path.join(wheelDir, w)));
  await micropip.install("emfs:/tmp/" + w, { deps: false });
  console.log("installed", w);
}

let failures = 0;
const check = (name, ok, extra = "") => {
  console.log((ok ? "PASS " : "FAIL ") + name + (extra ? "  " + extra : ""));
  if (!ok) failures++;
};

// ---- pycairo ---------------------------------------------------------------
py.FS.mkdirTree("/smoke");
py.FS.writeFile("/smoke/draw_smoke.py", fs.readFileSync(path.join(repo, "test/py/draw_smoke.py")));
const res = py.runPython(`
import sys, json
sys.path.insert(0, "/smoke")
import draw_smoke
json.dumps(draw_smoke.run())
`);
const r = JSON.parse(res);
console.log(JSON.stringify(r, null, 2));
check("pycairo version is 1.29.2", r.version === "1.29.2", r.version);
check("cairo version is 1.18.4", r.cairo_version_string === "1.18.4", r.cairo_version_string);
check("PNG written (magic ok, non-empty)", r.png_magic_ok && r.png_bytes > 100, `${r.png_bytes} bytes`);
check("PNG read back equals drawn pixels", r.png_roundtrip_equal);
check("PDF non-empty, %PDF header", r.pdf_bytes > 500 && r.pdf_head.startsWith("%PDF"), `${r.pdf_bytes} bytes`);
check("SVG non-empty", r.svg_bytes > 200, `${r.svg_bytes} bytes, head ${JSON.stringify(r.svg_head)}`);
check("PS non-empty, %!PS header", r.ps_bytes > 200 && r.ps_head.startsWith("%!PS"), `${r.ps_bytes} bytes`);
check("recording surface ink extents", JSON.stringify(r.recording_ink_extents) === "[1,1,10,10]" ||
      JSON.stringify(r.recording_ink_extents) === "[1.0,1.0,10.0,10.0]", JSON.stringify(r.recording_ink_extents));
console.log("IMAGE_SHA256", r.image_sha256);
if (process.env.EXPECT_IMAGE_SHA256)
  check("image sha256 matches EXPECT_IMAGE_SHA256", r.image_sha256 === process.env.EXPECT_IMAGE_SHA256);

// ---- uharfbuzz (stage 2a) ----------------------------------------------------
if (wheels.some((w) => w.startsWith("uharfbuzz-"))) {
  py.FS.writeFile("/smoke/font.ttf", fs.readFileSync(fontPath));
  const hb = JSON.parse(py.runPython(`
import json, uharfbuzz as hb
blob = hb.Blob.from_file_path("/smoke/font.ttf")
face = hb.Face(blob); font = hb.Font(face)
buf = hb.Buffer(); buf.add_str("Hello"); buf.guess_segment_properties()
hb.shape(font, buf, {"kern": True, "liga": True})
json.dumps({"version": hb.__version__, "hb_version": hb.version_string(), "upem": face.upem,
            "gids": [i.codepoint for i in buf.glyph_infos],
            "advances": [p.x_advance for p in buf.glyph_positions]})
`));
  console.log("uharfbuzz:", JSON.stringify(hb));
  check("uharfbuzz shaped 5 glyphs with non-zero advances", hb.gids.length === 5 && hb.advances.every((a) => a > 0));
}

// ---- skia-pathops (stage 2b) ---------------------------------------------------
if (wheels.some((w) => w.startsWith("skia_pathops-"))) {
  const pp = JSON.parse(py.runPython(`
import json, pathops
a = pathops.Path(); pen = a.getPen(); pen.moveTo((0,0)); pen.lineTo((10,0)); pen.lineTo((10,10)); pen.lineTo((0,10)); pen.closePath()
b = pathops.Path(); pen = b.getPen(); pen.moveTo((5,5)); pen.lineTo((15,5)); pen.lineTo((15,15)); pen.lineTo((5,15)); pen.closePath()
u = pathops.op(a, b, pathops.PathOp.UNION)
json.dumps({"bounds": u.bounds, "area": u.area, "segments": len(list(u.segments)), "version": getattr(pathops, "__version__", "?")})
`));
  console.log("skia-pathops:", JSON.stringify(pp));
  check("pathops union bounds (0,0,15,15) and area 175", (JSON.stringify(pp.bounds) === "[0,0,15,15]" ||
        JSON.stringify(pp.bounds) === "[0.0,0.0,15.0,15.0]") && pp.area === 175, JSON.stringify(pp));
}

console.log(failures ? `\n${failures} check(s) FAILED` : "\nALL SMOKE CHECKS PASSED");
process.exit(failures ? 1 : 0);
