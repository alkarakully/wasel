"""
Builds the NAWSIL ◆ نوصل lettering from one font, IBM Plex Sans Arabic Bold (the
apps' own font, OFL), so every letter has the same weight and size. HarfBuzz shapes
the Arabic so its letters join. Plex's capital I has serifs, so the I is the upright
stroke of the same font's L: the same thickness and height as every other stem. The gold divider with its soft diamond comes from
the traced artwork (traced.json).

  .venv/bin/pip install skia-pathops fonttools uharfbuzz
  .venv/bin/python brand/tools/compose_nawsil.py   # writes brand/tools/composed.json

build_logo.py reads composed.json.
"""

import json
from pathlib import Path

import pathops
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
FONT = HERE.parents[1] / "apps" / "nawsil_core" / "assets" / "fonts" / "IBMPlexSansArabic-Bold.ttf"
t = json.loads((HERE / "traced.json").read_text())

LATIN_TEXT, ARABIC_TEXT = "NAWSIL", "نوصل"
BASELINE = 254.7  # the traced artwork's baseline and cap height, kept so the divider fits as before
CAP = 103.0
TRACKING = 0.02  # extra space between Latin capitals, in ems
GAP = 26.0  # from the lettering to the divider's diamond, each side

font = TTFont(FONT)
glyphs = font.getGlyphSet()
upem = font["head"].unitsPerEm
scale = CAP / font["OS/2"].sCapHeight
blob = hb.Blob.from_file_path(str(FONT))
hb_font = hb.Font(hb.Face(blob))


def shape(text, direction):
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    buf.direction = direction
    hb.shape(hb_font, buf)
    return buf.glyph_infos, buf.glyph_positions


def plain_i():
    """The upright stroke of L, as a capital I with L's left side bearing on both sides."""
    stroke = pathops.Path()
    glyphs["L"].draw(stroke.getPen(glyphSet=glyphs))
    probe = pathops.Path()
    pen = probe.getPen()
    y = font["OS/2"].sCapHeight / 2
    for q in ((-100, y - 1), (2000, y - 1), (2000, y + 1), (-100, y + 1)):
        (pen.moveTo if q[0] == -100 and q[1] == y - 1 else pen.lineTo)(q)
    pen.closePath()
    x0, _, x1, _ = pathops.op(stroke, probe, pathops.PathOp.INTERSECTION).bounds
    box = pathops.Path()
    pen = box.getPen()
    for q in ((x0, -10), (x1, -10), (x1, 2000), (x0, 2000)):
        (pen.moveTo if q == (x0, -10) else pen.lineTo)(q)
    pen.closePath()
    stem = pathops.op(stroke, box, pathops.PathOp.INTERSECTION)
    advance = (x1 - x0) + 2 * x0  # L's left side bearing on each side
    return stem, advance


I_STEM, I_ADVANCE = plain_i()


def word(text, direction, x0, tracking=0.0):
    """Outline of `text` with its left edge's pen origin at x0, on the baseline."""
    infos, positions = shape(text, direction)
    names = font.getGlyphOrder()
    path = pathops.Path()
    x = 0.0
    for i, (info, pos) in enumerate(zip(infos, positions)):
        g = names[info.codepoint]
        pen = TransformPen(path.getPen(glyphSet=glyphs), (scale, 0, 0, -scale, x0 + (x + pos.x_offset) * scale, BASELINE - pos.y_offset * scale))
        advance = pos.x_advance
        if g == "I":
            I_STEM.draw(pen)
            advance = I_ADVANCE
        else:
            glyphs[g].draw(pen)
        x += advance + (tracking * upem if i < len(infos) - 1 else 0)
    return pathops.simplify(path)


def to_path(d, dx=0.0):
    p = pathops.Path()
    parse_path(d, TransformPen(p.getPen(), (1, 0, 0, 1, dx, 0)))
    return p


def d_of(p):
    pen = SVGPathPen(None, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    p.draw(pen)
    return pen.getCommands()


latin = word(LATIN_TEXT, "ltr", 0, TRACKING)
lb = latin.bounds
latin = word(LATIN_TEXT, "ltr", 19.1 - lb[0], TRACKING)  # left edge where the artwork's began
lb = latin.bounds

divider = to_path(t["divider"])
db = divider.bounds
divider = to_path(t["divider"], dx=lb[2] + GAP - db[0])
db = divider.bounds

arabic = word(ARABIC_TEXT, "rtl", 0)
ab = arabic.bounds
arabic = word(ARABIC_TEXT, "rtl", db[2] + GAP - ab[0])
ab = arabic.bounds

out = {
    "latin": d_of(latin),
    "arabic": d_of(arabic),
    "divider": d_of(divider),
    "latin_box": [round(v, 2) for v in lb],
    "arabic_box": [round(v, 2) for v in ab],
    "divider_box": [round(v, 2) for v in db],
}
(HERE / "composed.json").write_text(json.dumps(out))
print("latin", out["latin_box"], "arabic", out["arabic_box"], "divider", out["divider_box"])
