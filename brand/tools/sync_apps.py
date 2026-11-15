"""
Copies the logo paths from brand/logo.json into the apps' logo components:
the Flutter Wordmark (logo_paths.dart) and the store portal and platform admin Logo.tsx.

  python3 brand/tools/sync_apps.py
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
logo = json.loads((ROOT / "brand" / "logo.json").read_text())
h, s = logo["horizontal"], logo["stacked"]


def num(v):
    return f"{v:g}"


h_box = " ".join(num(v) for v in h["viewBox"])
s_box = " ".join(num(v) for v in s["viewBox"])


def sub(text, pattern, value, count=1):
    new, n = re.subn(pattern, lambda m: m.group(1) + value + m.group(2), text, count=count, flags=re.S)
    if n != count:
        raise SystemExit(f"pattern not found: {pattern}")
    return new


dart = ROOT / "apps" / "nawsil_core" / "lib" / "src" / "widgets" / "logo_paths.dart"
t = dart.read_text()
t = sub(t, r"(const logoLatinPath =\s*')[^']*(';)", h["latin"])
t = sub(t, r"(const logoArabicPath =\s*')[^']*(';)", h["arabic"])
t = sub(t, r"(const logoDividerPath =\s*')[^']*(';)", h["divider"])
t = sub(t, r"(const logoViewBox = ')[^']*(';)", h_box)
t = sub(t, r"(const logoAspect = )[^;]*(;)", f"{num(h['viewBox'][2])} / {num(h['viewBox'][3])}")
t = sub(t, r"(const logoStackedViewBox = ')[^']*(';)", s_box)
t = sub(t, r"(const logoStackedAspect = )[^;]*(;)", f"{num(s['viewBox'][2])} / {num(s['viewBox'][3])}")
t = sub(t, r"(const logoStackedArabicTransform = ')[^']*(';)", s["arabic"]["transform"])
t = sub(t, r"(const logoStackedRulePath =\s*')[^']*(';)", s["rule"])
t = sub(t, r"(const logoStackedLatinTransform = ')[^']*(';)", s["latin"]["transform"])
dart.write_text(t)

for app in ("vendor", "admin"):
    tsx = ROOT / "apps" / app / "src" / "components" / "Logo.tsx"
    t = tsx.read_text()
    t = sub(t, r"(const LATIN =\s*')[^']*(')", h["latin"])
    t = sub(t, r"(const ARABIC =\s*')[^']*(')", h["arabic"])
    t = sub(t, r"(const DIVIDER =\s*')[^']*(')", h["divider"])
    t = sub(t, r"(const STACKED_RULE =\s*')[^']*(')", s["rule"])
    t = sub(t, r'(<svg className=\{`logo \$\{className\}`\} viewBox=")0 0 [^"]*(")', s_box)
    t = sub(t, r'(<path transform=")translate[^"]*(" d=\{ARABIC\})', s["arabic"]["transform"])
    t = sub(t, r'(<path transform=")translate[^"]*(" d=\{LATIN\})', s["latin"]["transform"])
    t = sub(t, r'(<svg className=\{`logo \$\{className\}`\} viewBox=")(?!0 0 )[^"]*(")', h_box)
    tsx.write_text(t)

print("synced", h_box, s_box)
