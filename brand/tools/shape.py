"""Shape text with HarfBuzz and emit one SVG path (font units, y up flipped)."""
import sys, json
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

def shape(font_path, text, size, tracking=0, direction=None):
    blob = hb.Blob.from_file_path(font_path)
    face = hb.Face(blob); font = hb.Font(face)
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    if direction: buf.direction = direction
    hb.shape(font, buf, {"kern": True, "liga": True})
    tt = TTFont(font_path); gs = tt.getGlyphSet(); order = tt.getGlyphOrder()
    upem = tt["head"].unitsPerEm; scale = size / upem
    pen = SVGPathPen(gs)
    x = 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = order[info.codepoint]
        t = TransformPen(pen, (scale, 0, 0, -scale, (x + pos.x_offset) * scale, -pos.y_offset * scale))
        gs[name].draw(t)
        x += pos.x_advance + tracking
    width = (x - tracking) * scale
    asc = tt["hhea"].ascent * scale; desc = -tt["hhea"].descent * scale
    return pen.getCommands(), width, asc, desc

if __name__ == "__main__":
    font, text, size = sys.argv[1], sys.argv[2], float(sys.argv[3])
    tracking = float(sys.argv[4]) if len(sys.argv) > 4 else 0
    d, w, a, de = shape(font, text, size, tracking)
    print(json.dumps({"d": d, "width": w, "ascent": a, "descent": de}))
