"""
Wasel bilingual wordmark: WASEL ◆ واصل. Writes brand/*.svg and brand/logo.json.

  python -m venv .venv && .venv/bin/pip install fonttools uharfbuzz
  .venv/bin/python brand/tools/wordmark.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import uharfbuzz as hb
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from shape import shape

OUT = str(HERE.parent) + "/"
F = str(HERE.parents[1] / "apps/wasel_core/assets/fonts") + "/"
BOLD, SEMI = F + "IBMPlexSansArabic-Bold.ttf", F + "IBMPlexSansArabic-SemiBold.ttf"
LAPIS_600, LAPIS, DEEP, GOLD = "#2F48B0", "#22379B", "#131F5C", "#F2C75C"
PAPER = "#F4F6FF"


def r(v):
    return round(v, 2)


def ink_box(font_path, text, size, tracking=0):
    """Path, advance width and the ink box (x0, top, x1, bottom; y grows down)."""
    d, w, _, _ = shape(font_path, text, size, tracking)
    font = hb.Font(hb.Face(hb.Blob.from_file_path(font_path)))
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True})
    tt = TTFont(font_path)
    gs, order = tt.getGlyphSet(), tt.getGlyphOrder()
    sc = size / tt["head"].unitsPerEm
    bp, x = BoundsPen(gs), 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        gs[order[info.codepoint]].draw(TransformPen(bp, (sc, 0, 0, -sc, (x + pos.x_offset) * sc, -pos.y_offset * sc)))
        x += pos.x_advance + tracking
    return d, w, bp.bounds


def diamond(cx, cy, k, fill):
    return f'<path d="M{r(cx)} {r(cy-k)}L{r(cx+k)} {r(cy)}L{r(cx)} {r(cy+k)}L{r(cx-k)} {r(cy)}Z" fill="{fill}"/>'


UPEM = TTFont(SEMI)["head"].unitsPerEm

# واصل sets the scale. WASEL's capitals are as tall as the Arabic letter bodies
# reach above the baseline, so the two names read as one.
AR = 88
ar_d, ar_w, (ax0, atop, ax1, abot) = ink_box(BOLD, "واصل", AR)
stem = -atop
_, _, (_, cap_top, _, _) = ink_box(SEMI, "WASEL", 100)
cap_per_size = -cap_top / 100
LA = stem * 0.52 / cap_per_size
la_d, la_w, (lx0, ltop, lx1, lbot) = ink_box(SEMI, "WASEL", LA, 0.2 * UPEM)

PAD, GAP = 6, 30
H = (abot - atop) + 2 * PAD
base = PAD - atop  # Arabic baseline
cap = -ltop
la_base = base  # WASEL sits on the same baseline as واصل
cy = base - cap / 2
span = cap * 0.95
x_la = PAD - lx0
div_x = PAD + (lx1 - lx0) + GAP
x_ar = div_x + GAP - ax0
W = x_ar + ax1 + PAD


def horizontal(ink, latin):
    body = (
        f'<path transform="translate({r(x_la)} {r(la_base)})" d="{la_d}" fill="{latin}"/>'
        f'<path d="M{r(div_x)} {r(cy-span)}V{r(cy+span)}" stroke="{GOLD}" stroke-width="1.6"/>'
        + diamond(div_x, cy, 5, GOLD)
        + f'<path transform="translate({r(x_ar)} {r(base)})" d="{ar_d}" fill="{ink}"/>'
    )
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {r(W)} {r(H)}" role="img" aria-label="واصل WASEL">{body}</svg>'


# Stacked: واصل, a gold rule with its diamond, and a letter-spaced WASEL below.
SW = (ax1 - ax0) + 2 * PAD
s_x_ar = PAD - ax0
rule_y = base + abot + 16
s_la = LA * 0.62
s_d, _, (sx0, stop, sx1, sbot) = ink_box(SEMI, "WASEL", s_la, 0.5 * UPEM)
s_lw = sx1 - sx0
s_lx = (SW - s_lw) / 2 - sx0
s_lbase = rule_y + 16 - stop
SH = s_lbase + sbot + PAD
rule_from, rule_to = SW * 0.2, SW * 0.8


def stacked(ink, latin):
    body = (
        f'<path transform="translate({r(s_x_ar)} {r(base)})" d="{ar_d}" fill="{ink}"/>'
        f'<path d="M{r(rule_from)} {r(rule_y)}H{r(rule_to)}" stroke="{GOLD}" stroke-width="1.4"/>'
        + diamond(SW / 2, rule_y, 3.8, GOLD)
        + f'<path transform="translate({r(s_lx)} {r(s_lbase)})" d="{s_d}" fill="{latin}"/>'
    )
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {r(SW)} {r(SH)}" role="img" aria-label="واصل WASEL">{body}</svg>'


def rect_bricks(size, s):
    lines, row, yy = [], 0, 40 * s
    while yy < size:
        lines.append(f"M0 {r(yy)}H{size}")
        step = 120 * s
        jx = step / 2 if row % 2 else 0
        while jx < size:
            lines.append(f"M{r(jx)} {r(yy)}V{r(yy + 82 * s)}")
            jx += step
        yy += 82 * s
        row += 1
    return "".join(lines)


def icon(size=1024, bricks=True):
    """App icon: واصل in gold on glazed lapis, a gold diamond rule beneath."""
    s = size / 1024
    k = 640 * s / (ax1 - ax0)
    gw, gh = (ax1 - ax0) * k, (abot - atop) * k
    x = (size - gw) / 2 - ax0 * k
    y = (size - gh) / 2 - atop * k - 50 * s
    ry = y + abot * k + 80 * s
    texture = (
        f'<path d="{rect_bricks(size, s)}" fill="none" stroke="#fff" stroke-opacity=".06" stroke-width="{r(4*s)}"/>'
        if bricks
        else ""
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}">'
        f'<defs><linearGradient id="ig" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{LAPIS_600}"/>'
        f'<stop offset=".5" stop-color="{LAPIS}"/><stop offset="1" stop-color="{DEEP}"/></linearGradient></defs>'
        f'<rect width="{size}" height="{size}" rx="{r(224*s)}" fill="url(#ig)"/>{texture}'
        f'<path transform="translate({r(x)} {r(y)}) scale({r(k)})" d="{ar_d}" fill="{GOLD}"/>'
        f'<path d="M{r(size*0.32)} {r(ry)}H{r(size*0.68)}" stroke="{GOLD}" stroke-opacity=".75" stroke-width="{r(9*s)}"/>'
        + diamond(size / 2, ry, 24 * s, GOLD)
        + "</svg>"
    )


files = {
    "wasel-logo.svg": horizontal(LAPIS, LAPIS),
    "wasel-logo-dark.svg": horizontal(PAPER, GOLD),
    "wasel-logo-stacked.svg": stacked(LAPIS, LAPIS),
    "wasel-logo-stacked-dark.svg": stacked(PAPER, GOLD),
    "wasel-icon.svg": icon(),
    "favicon.svg": icon(64, bricks=False),
}
for name, content in files.items():
    with open(OUT + name, "w") as f:
        f.write(content)

with open(OUT + "logo.json", "w") as f:
    json.dump(
        {
            "horizontal": {
                "width": r(W), "height": r(H),
                "latin": {"d": la_d, "x": r(x_la), "y": r(la_base)},
                "arabic": {"d": ar_d, "x": r(x_ar), "y": r(base)},
                "divider": {"x": r(div_x), "y1": r(cy - span), "y2": r(cy + span), "cy": r(cy), "k": 5},
            },
            "stacked": {
                "width": r(SW), "height": r(SH),
                "arabic": {"d": ar_d, "x": r(s_x_ar), "y": r(base)},
                "latin": {"d": s_d, "x": r(s_lx), "y": r(s_lbase)},
                "rule": {"x1": r(rule_from), "x2": r(rule_to), "y": r(rule_y), "k": 3.8},
            },
        },
        f,
    )
print("ok", r(W), r(H), r(SW), r(SH))
