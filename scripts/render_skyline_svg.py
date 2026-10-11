#!/usr/bin/env python3
"""
Render the contribution "skyline": a year of activity as an isometric 3D city
whose towers rise (and settle) in a wave from the oldest week to the newest.

It reads data/contributions.json and writes two self-contained animated SVGs
(light and dark) that GitHub renders inside a README <picture>. The geometry
and maths mirror the ContributionSkyline React component (same grid, levels,
bar heights, camera and palette); the motion is pure CSS inside the SVG, so it
works in an <img> tag with no JavaScript.

usage: python scripts/render_skyline_svg.py [--data data/contributions.json] [--out .]
"""
import argparse
import datetime
import json
import math
import os

# ---- camera (same as the component's 3D view: yaw 45deg, elevation 34deg) ----
K = math.cos(math.radians(45))      # horizontal factor for one grid step
SE = math.sin(math.radians(34))     # sin(elevation)
CE = math.cos(math.radians(34))     # cos(elevation)
B = K * SE                          # vertical factor for one grid step
THETA = math.degrees(math.atan(SE)) # skew angle of the side faces

W_BAR = 0.9                         # bar footprint (grid units)
OFF = (1 - W_BAR) / 2

# ---- motion ----
CYCLE = 9.0       # seconds for one rise / hold / settle loop
WAVE = 1.8        # seconds the wave takes to sweep oldest week -> newest

PALETTES = {
    "light": {
        "levels": ["#ebedf0", "#c6e48b", "#7bc96f", "#239a3b", "#196127"],
        "fg": "#1f2328",
        "muted": "#59636e",
    },
    "dark": {
        "levels": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
        "fg": "#e6edf3",
        "muted": "#9198a1",
    },
}


# ---------------------------------------------------------------- data ----
def build_grid(days):
    counts = {}
    for d in days:
        c = d.get("count", 0)
        if c and c > 0:
            counts[d["date"]] = counts.get(d["date"], 0) + c
    end = max(datetime.date.fromisoformat(d["date"]) for d in days)
    start = end - datetime.timedelta(days=364)
    start -= datetime.timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    cells = []
    i = 0
    cur = start
    while cur <= end:
        key = cur.isoformat()
        cells.append({"date": key, "count": counts.get(key, 0), "week": i // 7, "day": i % 7, "level": 0})
        cur += datetime.timedelta(days=1)
        i += 1
    nz = sorted(c["count"] for c in cells if c["count"] > 0)
    busy = nz[int(math.floor(0.95 * (len(nz) - 1)))] if nz else 0
    for c in cells:
        n = c["count"]
        c["level"] = 0 if n <= 0 else (4 if busy <= 0 else 1 + min(3, int(math.floor(n / busy * 4))))
    weeks = cells[-1]["week"] + 1
    return cells, weeks, (nz[-1] if nz else 0)


def bar_height(count, mx):
    return 0.4 + math.pow(count / mx, 0.85) * 7.2 if count > 0 and mx > 0 else 0.2


def compute_stats(cells):
    total = sum(c["count"] for c in cells)
    best = max(cells, key=lambda c: c["count"])
    run = 0
    run_start = None
    longest = (0, None, None)
    for c in cells:
        if c["count"] > 0:
            if run == 0:
                run_start = c["date"]
            run += 1
            if run > longest[0]:
                longest = (run, run_start, c["date"])
        else:
            run = 0
    j = len(cells) - 1
    if j >= 0 and cells[j]["count"] == 0:
        j -= 1  # today isn't over yet
    end_at = j
    while j >= 0 and cells[j]["count"] > 0:
        j -= 1
    n = end_at - j
    current = (n, cells[j + 1]["date"], cells[end_at]["date"]) if n > 0 else (0, None, None)
    return {
        "total": total,
        "first": cells[0]["date"],
        "last": cells[-1]["date"],
        "busiest": (best["count"], best["date"] if best["count"] > 0 else None),
        "longest": longest,
        "current": current,
    }


# ------------------------------------------------------------- helpers ----
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt(date, year=False):
    if not date:
        return "—"
    d = datetime.date.fromisoformat(date)
    s = f"{MONTHS[d.month - 1]} {d.day}"
    return f"{s}, {d.year}" if year else s


def rng(a, b, year=False):
    return "—" if not a or not b else f"{fmt(a, year)} — {fmt(b, year)}"


def shade(hex_color, f):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (round(r * f), round(g * f), round(b * f))


def noun(n, unit="contribution"):
    return unit if n == 1 else unit + "s"


def num(n):
    return f"{n:,}"


# --------------------------------------------------------------- render ----
def render(data, theme, scale=16.5, width=860):
    pal = PALETTES[theme]
    cells, weeks, mx = build_grid(data["days"])
    stats = compute_stats(cells)
    S = scale

    def sx(x, y):
        return (x - y) * K * S

    def sy(x, y):
        return (x + y) * B * S

    # bounding box of the full-height scene, so it can be centred
    minx = miny = 1e9
    maxx = maxy = -1e9
    for c in cells:
        h = bar_height(c["count"], mx) * CE * S
        x0, y0 = c["week"] + OFF, c["day"] + OFF
        x1, y1 = x0 + W_BAR, y0 + W_BAR
        for (x, y) in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            minx, maxx = min(minx, sx(x, y)), max(maxx, sx(x, y))
            miny = min(miny, sy(x, y) - h)
            maxy = max(maxy, sy(x, y))
    label_pad = 26
    top_pad, foot_pad = 22, 34
    ox = width / 2 - (minx + maxx) / 2
    oy = top_pad - miny
    height = math.ceil(top_pad + (maxy - miny) + label_pad + foot_pad)

    out = []
    a = out.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
      f'role="img" aria-labelledby="t d">')
    a(f'<title id="t">{num(stats["total"])} {noun(stats["total"])} in the last year</title>')
    a(f'<desc id="d">Isometric skyline of the last year of GitHub activity for {data.get("username", "")}: '
      f'one tower per day, taller means more contributions.</desc>')

    # ---- styles ----
    css = [
        "svg{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif}",
        f".lb{{font-size:13px;fill:{pal['muted']}}}",
        f".sb{{font-size:12px;fill:{pal['muted']}}}",
        f".un{{font-size:15px;fill:{pal['fg']}}}",
        f".bv{{font-size:40px;font-weight:600;letter-spacing:-.02em;fill:{pal['levels'][4]}}}",
        f".mo{{font-size:10px;fill:{pal['muted']}}}",
    ]
    for lv, col in enumerate(pal["levels"]):
        css.append(f".a{lv}{{fill:{col}}}.b{lv}{{fill:{shade(col, .84)}}}.c{lv}{{fill:{shade(col, .68)}}}")
    css.append(
        f".g,.t{{animation:{CYCLE}s ease-in-out infinite both;animation-name:grow;animation-delay:var(--d)}}"
        ".g{transform-box:fill-box;transform-origin:0 100%}"
        ".t{animation-name:lift}"
    )
    p1, p2, p3 = 16, 60, 76  # % of the cycle: risen by, held until, settled by
    css.append(f"@keyframes grow{{0%{{transform:scaleY(0)}}{p1}%,{p2}%{{transform:scaleY(1)}}{p3}%,100%{{transform:scaleY(0)}}}}")
    css.append(f"@keyframes lift{{0%{{transform:translateY(0)}}{p1}%,{p2}%{{transform:translateY(var(--ny))}}{p3}%,100%{{transform:translateY(0)}}}}")
    css.append("@media (prefers-reduced-motion:reduce){.g,.t{animation:none}}")
    a("<style>" + "".join(css) + "</style>")

    # ---- towers, far to near ----
    a('<g class="city">')
    for c in sorted(cells, key=lambda c: (c["week"] + c["day"], c["week"])):
        lv = c["level"]
        h = bar_height(c["count"], mx)
        H = h * CE * S
        x0, y0 = c["week"] + OFF, c["day"] + OFF
        x1, y1 = x0 + W_BAR, y0 + W_BAR
        bx, by = ox + sx(x0, y0), oy + sy(x0, y0)   # back
        rx, ry = ox + sx(x1, y0), oy + sy(x1, y0)   # right
        fx, fy = ox + sx(x1, y1), oy + sy(x1, y1)   # front
        lx, ly = ox + sx(x0, y1), oy + sy(x0, y1)   # left
        if c["count"] <= 0:
            # empty day: a thin static slab
            a(f'<polygon class="b{lv}" points="{lx:.1f},{ly:.1f} {fx:.1f},{fy:.1f} {fx:.1f},{fy - H:.1f} {lx:.1f},{ly - H:.1f}"/>')
            a(f'<polygon class="c{lv}" points="{fx:.1f},{fy:.1f} {rx:.1f},{ry:.1f} {rx:.1f},{ry - H:.1f} {fx:.1f},{fy - H:.1f}"/>')
            a(f'<polygon class="a{lv}" points="{bx:.1f},{by - H:.1f} {rx:.1f},{ry - H:.1f} {fx:.1f},{fy - H:.1f} {lx:.1f},{ly - H:.1f}"/>')
            continue
        delay = (c["week"] / max(1, weeks - 1)) * WAVE + (c["day"] / 6) * 0.2
        wd = W_BAR * K * S
        a(f'<g style="--d:{delay:.2f}s;--ny:-{H:.1f}px">')
        a(f'<g transform="translate({lx:.1f} {ly:.1f}) skewY({THETA:.2f})"><rect class="g b{lv}" y="-{H:.1f}" width="{wd:.1f}" height="{H:.1f}"/></g>')
        a(f'<g transform="translate({fx:.1f} {fy:.1f}) skewY(-{THETA:.2f})"><rect class="g c{lv}" y="-{H:.1f}" width="{wd:.1f}" height="{H:.1f}"/></g>')
        a(f'<polygon class="t a{lv}" points="{bx:.1f},{by:.1f} {rx:.1f},{ry:.1f} {fx:.1f},{fy:.1f} {lx:.1f},{ly:.1f}"/>')
        a("</g>")
    a("</g>")

    # ---- month labels along the front edge ----
    prev, last_x = -1, -1e9
    labels = []
    for w in range(weeks):
        d = datetime.date.fromisoformat(cells[w * 7]["date"])
        if d.month != prev:
            labels.append((w, MONTHS[d.month - 1]))
        prev = d.month
    if len(labels) > 1 and labels[1][0] - labels[0][0] < 3:
        labels.pop(0)
    for w, name in labels:
        x = ox + sx(w + 0.5, 7.3)
        y = oy + sy(w + 0.5, 7.3) + 12
        if x - last_x < 36 or x > width - 20:
            continue
        a(f'<text class="mo" x="{x:.1f}" y="{y:.1f}">{name}</text>')
        last_x = x

    # ---- stats in the empty corners (top-right, bottom-left) ----
    def stat(x, y, anchor, label, value, unit, sub):
        a(f'<text class="lb" x="{x}" y="{y + 13}" text-anchor="{anchor}">{label}</text>')
        a(f'<text x="{x}" y="{y + 55}" text-anchor="{anchor}"><tspan class="bv">{value}</tspan><tspan class="un" dx="7">{unit}</tspan></text>')
        a(f'<text class="sb" x="{x}" y="{y + 74}" text-anchor="{anchor}">{sub}</text>')

    bd = stats["busiest"]
    ln, lstart, lend = stats["longest"]
    cn, cstart, cend = stats["current"]
    stat(width - 14, 8, "end", "1 year total", num(stats["total"]), noun(stats["total"]), rng(stats["first"], stats["last"], True))
    stat(width - 14, 100, "end", "Busiest day", num(bd[0]), noun(bd[0]), fmt(bd[1]))
    bottom = height - foot_pad - 4
    stat(14, bottom - 176, "start", "Longest streak", num(ln), noun(ln, "day"), rng(lstart, lend))
    stat(14, bottom - 84, "start", "Current streak", num(cn), noun(cn, "day"), rng(cstart, cend))

    # ---- legend ----
    ly0 = height - 20
    lx = width - 14
    a(f'<text class="sb" x="{lx}" y="{ly0 + 9}" text-anchor="end">More</text>')
    x = lx - 34
    for lv in (4, 3, 2, 1, 0):
        x -= 15
        a(f'<rect class="a{lv}" x="{x}" y="{ly0}" width="11" height="11" rx="2"/>')
    a(f'<text class="sb" x="{x - 6}" y="{ly0 + 9}" text-anchor="end">Less</text>')

    a("</svg>")
    return "\n".join(out)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(here, "..", "data", "contributions.json"))
    ap.add_argument("--out", default=os.path.join(here, ".."))
    ap.add_argument("--scale", type=float, default=16.5)
    args = ap.parse_args()

    with open(args.data) as f:
        data = json.load(f)
    for theme in ("light", "dark"):
        svg = render(data, theme, scale=args.scale)
        path = os.path.join(args.out, f"skyline-{theme}.svg")
        with open(path, "w") as f:
            f.write(svg)
        print(f"wrote {path} ({len(svg) // 1024} KB)")


if __name__ == "__main__":
    main()
