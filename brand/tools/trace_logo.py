"""Trace brand/logo-source.jpeg into clean SVG paths (blue WASEL, gold واصل) and draw the divider.

  .venv/bin/python brand/tools/trace_logo.py brand/tools
"""
import json
import sys

import numpy as np
import potrace
from PIL import Image, ImageFilter

SRC = str(__import__("pathlib").Path(__file__).resolve().parents[1] / "logo-source.jpeg")
UP = 4  # trace an upscaled, smoothed copy so curves come out clean

im = Image.open(SRC).convert("RGB")
W, H = im.size
big = im.resize((W * UP, H * UP), Image.LANCZOS).filter(ImageFilter.GaussianBlur(3.2))
a = np.asarray(big).astype(int)
r, g, b = a[..., 0], a[..., 1], a[..., 2]
bg = np.array([244, 240, 229])
# Distance from the cream background toward each ink colour, thresholded at the midpoint.
blue_ink = np.array([3, 57, 144]); gold_ink = np.array([228, 167, 57])
def mask(ink):
    d_bg = np.linalg.norm(a - bg, axis=2)
    d_ink = np.linalg.norm(a - ink, axis=2)
    return d_ink < d_bg
blue = mask(blue_ink) & (b > r)
gold = mask(gold_ink) & (r > b + 40)
# The divider is redrawn as exact geometry; trace only the Arabic.
gold[:, : 514 * UP] = False

def trace(m):
    bmp = potrace.Bitmap(~m)  # the tracer draws the False (dark) pixels
    path = bmp.trace(turdsize=40, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY, alphamax=1.1,
                     opticurve=True, opttolerance=0.9)
    parts = []
    f = lambda p: f"{p.x / UP:.2f} {p.y / UP:.2f}"
    for curve in path:
        parts.append(f"M{f(curve.start_point)}")
        for seg in curve.segments:
            if seg.is_corner:
                parts.append(f"L{f(seg.c)}L{f(seg.end_point)}")
            else:
                parts.append(f"C{f(seg.c1)} {f(seg.c2)} {f(seg.end_point)}")
        parts.append("Z")
    return "".join(parts)

# Divider: two bars with rounded ends and a soft diamond between them.
CX, CY = 489.5, 202.5
def bar(y1, y2, w=9.5):
    rr = w / 2
    return (f"M{CX - w/2:.2f} {y1 + rr:.2f}A{rr:.2f} {rr:.2f} 0 0 1 {CX + w/2:.2f} {y1 + rr:.2f}"
            f"V{y2 - rr:.2f}A{rr:.2f} {rr:.2f} 0 0 1 {CX - w/2:.2f} {y2 - rr:.2f}Z")
def soft_diamond(k=16.0, c=5.0):
    # A diamond with rounded corners: straight edges, quadratic curves at each tip.
    t, rgt, btm, lft = (CX, CY - k), (CX + k, CY), (CX, CY + k), (CX - k, CY)
    def towards(a, b, d):
        import math
        L = math.dist(a, b); return (a[0] + (b[0]-a[0]) * d / L, a[1] + (b[1]-a[1]) * d / L)
    pts = [t, rgt, btm, lft]
    out = ""
    for i, p in enumerate(pts):
        prev, nxt = pts[i - 1], pts[(i + 1) % 4]
        a, b = towards(p, prev, c), towards(p, nxt, c)
        out += (f"{'M' if i == 0 else 'L'}{a[0]:.2f} {a[1]:.2f}Q{p[0]:.2f} {p[1]:.2f} {b[0]:.2f} {b[1]:.2f}")
    return out + "Z"
divider = bar(83, 184) + soft_diamond() + bar(221, 325)

out = {"width": W, "height": H, "blue": trace(blue), "gold": trace(gold), "divider": divider}
json.dump(out, open(sys.argv[1] + "/traced.json", "w"))
print(len(out["blue"]), len(out["gold"]))
