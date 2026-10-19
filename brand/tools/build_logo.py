"""
Builds the Wasel logo set from the traced artwork (brand/logo-source.jpeg):
WASEL in blue, the gold divider with its soft diamond, and واصل in gold.

  .venv/bin/pip install pillow numpy potracer
  .venv/bin/python brand/tools/trace_logo.py brand/tools   # writes brand/tools/traced.json
  .venv/bin/python brand/tools/build_logo.py               # writes brand/*.svg and brand/logo.json
"""

import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
t = json.loads((HERE / "traced.json").read_text())

BLUE, GOLD, PAPER = "#033990", "#E4A739", "#F4F6FF"
LATIN, ARABIC, DIVIDER = t["blue"], t["gold"], t["divider"]

# Ink boxes in the source artwork (pixels).
LAT = (19, 151, 452, 256)  # WASEL
AR = (520, 115, 838, 283)  # واصل
DIV_TOP, DIV_BOTTOM = 83, 325
PAD = 6
HX, HY = LAT[0] - PAD, DIV_TOP - PAD
HW, HH = AR[2] - LAT[0] + 2 * PAD, DIV_BOTTOM - DIV_TOP + 2 * PAD


def r(v):
    return round(v, 2)


def soft_diamond(cx, cy, k, c):
    pts = [(cx, cy - k), (cx + k, cy), (cx, cy + k), (cx - k, cy)]

    def towards(a, b, d):
        L = math.dist(a, b)
        return (a[0] + (b[0] - a[0]) * d / L, a[1] + (b[1] - a[1]) * d / L)

    out = ""
    for i, p in enumerate(pts):
        a, b = towards(p, pts[i - 1], c), towards(p, pts[(i + 1) % 4], c)
        out += f"{'M' if i == 0 else 'L'}{r(a[0])} {r(a[1])}Q{r(p[0])} {r(p[1])} {r(b[0])} {r(b[1])}"
    return out + "Z"


def hbar(x1, x2, y, w=6.0):
    rr = w / 2
    return f"M{r(x1 + rr)} {r(y - rr)}H{r(x2 - rr)}A{rr} {rr} 0 0 1 {r(x2 - rr)} {r(y + rr)}H{r(x1 + rr)}A{rr} {rr} 0 0 1 {r(x1 + rr)} {r(y - rr)}Z"


def horizontal(latin, arabic, rule):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{HX} {HY} {HW} {HH}" role="img" aria-label="WASEL واصل">'
        f'<path d="{LATIN}" fill="{latin}" fill-rule="evenodd"/>'
        f'<path d="{DIVIDER}" fill="{rule}"/>'
        f'<path d="{ARABIC}" fill="{arabic}" fill-rule="evenodd"/></svg>'
    )


# Stacked: واصل, a horizontal divider with the diamond, WASEL below at 58%.
S_LAT = 0.58
SW = (AR[2] - AR[0]) + 2 * PAD + 20
ar_dx, ar_dy = PAD + 10 - AR[0], PAD - AR[1]
rule_y = (AR[3] - AR[1]) + PAD + 26
lat_w = (LAT[2] - LAT[0]) * S_LAT
lat_dx = (SW - lat_w) / 2 - LAT[0] * S_LAT
lat_dy = rule_y + 24 - LAT[1] * S_LAT
SH = lat_dy + LAT[3] * S_LAT + PAD
STACK_RULE = hbar(SW * 0.12, SW / 2 - 18, rule_y) + soft_diamond(SW / 2, rule_y, 11, 3.6) + hbar(SW / 2 + 18, SW * 0.88, rule_y)


def stacked(latin, arabic, rule):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {r(SW)} {r(SH)}" role="img" aria-label="WASEL واصل">'
        f'<path transform="translate({r(ar_dx)} {r(ar_dy)})" d="{ARABIC}" fill="{arabic}" fill-rule="evenodd"/>'
        f'<path d="{STACK_RULE}" fill="{rule}"/>'
        f'<path transform="translate({r(lat_dx)} {r(lat_dy)}) scale({S_LAT})" d="{LATIN}" fill="{latin}" fill-rule="evenodd"/></svg>'
    )


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


def icon(size=1024, rounded=True, bricks=True, background=True):
    """App icon: the gold واصل over a gold divider on deep blue glaze."""
    s = size / 1024
    aw, ah = AR[2] - AR[0], AR[3] - AR[1]
    k = 600 * s / aw
    x = (size - aw * k) / 2 - AR[0] * k
    y = (size - ah * k) / 2 - AR[1] * k - 50 * s
    ry = y + AR[3] * k + 70 * s
    cx = size / 2
    rule = hbar(size * 0.3, cx - 40 * s, ry, 12 * s) + soft_diamond(cx, ry, 24 * s, 8 * s) + hbar(cx + 40 * s, size * 0.7, ry, 12 * s)
    bg = ""
    if background:
        bg = (
            f'<defs><linearGradient id="ig" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0B4BB8"/>'
            f'<stop offset=".5" stop-color="{BLUE}"/><stop offset="1" stop-color="#02215A"/></linearGradient></defs>'
            f'<rect width="{size}" height="{size}"{f" rx={chr(34)}{r(224*s)}{chr(34)}" if rounded else ""} fill="url(#ig)"/>'
        )
        if bricks:
            bg += f'<path d="{rect_bricks(size, s)}" fill="none" stroke="#fff" stroke-opacity=".06" stroke-width="{r(4*s)}"/>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}">{bg}'
        f'<path transform="translate({r(x)} {r(y)}) scale({r(k)})" d="{ARABIC}" fill="{GOLD}" fill-rule="evenodd"/>'
        f'<path d="{rule}" fill="{GOLD}"/></svg>'
    )


files = {
    "wasel-logo.svg": horizontal(BLUE, GOLD, GOLD),
    "wasel-logo-dark.svg": horizontal(PAPER, GOLD, GOLD),
    "wasel-logo-on-glaze.svg": horizontal(PAPER, GOLD, GOLD),
    "wasel-logo-stacked.svg": stacked(BLUE, GOLD, GOLD),
    "wasel-logo-stacked-dark.svg": stacked(PAPER, GOLD, GOLD),
    "wasel-icon.svg": icon(),
    "wasel-icon-square.svg": icon(rounded=False),
    "wasel-icon-foreground.svg": icon(background=False),
    "favicon.svg": icon(64, bricks=False),
}
for name, content in files.items():
    (OUT / name).write_text(content)

(OUT / "logo.json").write_text(json.dumps({
    "colors": {"blue": BLUE, "gold": GOLD},
    "horizontal": {"viewBox": [HX, HY, HW, HH], "latin": LATIN, "arabic": ARABIC, "divider": DIVIDER},
    "stacked": {
        "viewBox": [0, 0, r(SW), r(SH)],
        "arabic": {"d": ARABIC, "transform": f"translate({r(ar_dx)} {r(ar_dy)})"},
        "rule": STACK_RULE,
        "latin": {"d": LATIN, "transform": f"translate({r(lat_dx)} {r(lat_dy)}) scale({S_LAT})"},
    },
}))
print("ok", HW, HH, r(SW), r(SH))
