"""Drawing used by the Node smoke test (and runnable on native CPython with pycairo)."""
import hashlib
import io

import cairo


def draw(surface_cls_args=(cairo.FORMAT_ARGB32, 64, 64)):
    surf = cairo.ImageSurface(*surface_cls_args)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(1, 1, 1)
    ctx.paint()
    ctx.set_antialias(cairo.ANTIALIAS_GRAY)
    ctx.set_source_rgba(0.9, 0.2, 0.1, 1.0)
    ctx.arc(32.3, 30.7, 18.4, 0, 2 * 3.141592653589793)
    ctx.fill()
    ctx.set_source_rgba(0.1, 0.3, 0.8, 0.6)
    ctx.rectangle(8.5, 40.25, 40.5, 15.75)
    ctx.fill()
    ctx.set_source_rgb(0, 0, 0)
    ctx.set_line_width(1.5)
    ctx.move_to(4, 4)
    ctx.curve_to(20, 0, 40, 20, 60, 4)
    ctx.stroke()
    surf.flush()
    return surf


def run():
    out = {}
    out["version"] = cairo.version
    out["cairo_version_string"] = cairo.cairo_version_string()
    surf = draw()
    data = bytes(surf.get_data())
    out["image_sha256"] = hashlib.sha256(data).hexdigest()
    out["image_stride"] = surf.get_stride()
    png = io.BytesIO()
    surf.write_to_png(png)
    out["png_bytes"] = len(png.getvalue())
    out["png_magic_ok"] = png.getvalue()[:8] == b"\x89PNG\r\n\x1a\n"
    # PNG round trip through libpng's read path
    back = cairo.ImageSurface.create_from_png(io.BytesIO(png.getvalue()))
    out["png_roundtrip_equal"] = bytes(back.get_data()) == data
    for name, cls in (("pdf", cairo.PDFSurface), ("svg", cairo.SVGSurface), ("ps", cairo.PSSurface)):
        buf = io.BytesIO()
        s = cls(buf, 64, 64)
        c = cairo.Context(s)
        c.set_source_rgb(0.2, 0.6, 0.3)
        c.arc(32, 32, 20, 0, 6.2831853)
        c.fill()
        c.show_page()
        s.finish()
        out[f"{name}_bytes"] = len(buf.getvalue())
        out[f"{name}_head"] = buf.getvalue()[:8].decode("latin1")
    rec = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, None)
    c = cairo.Context(rec)
    c.rectangle(1, 1, 10, 10)
    c.fill()
    out["recording_ink_extents"] = rec.ink_extents()
    return out
