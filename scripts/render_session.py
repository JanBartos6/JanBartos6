"""Render session_dark.svg / session_light.svg: a second terminal window under the card with
a text-mode contribution heatmap (`git log | heatmap`) and an `ls -lt ~/projects` listing.

Reads card.json (project list and descriptions) and stats.json (calendar, push dates,
languages), both kept fresh by update_stats.py. Standard library only.
"""
import datetime
import json
import math
import pathlib
import sys
from html import escape

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from render import CW, FONT, PAD, ROOT, THEMES  # noqa: E402

W = 950                      # same width as the card, so the two windows line up
LH = 21
ROW = 17                     # heatmap row pitch
COL = 16                     # heatmap column pitch
RAMP = ".:-=+*#%@"           # 1, 2-3, 4-7, 8-15, 16-31, 32-63, 64-127, 128-255, 256+
GREENS = {
    "dark": ["#1f6f33", "#238636", "#2ea043", "#3fb950", "#46c35a", "#56d364", "#7ee787", "#aff5b4", "#e6ffec"],
    "light": ["#9be9a8", "#7fd68f", "#5ac173", "#40c463", "#2da44e", "#218c42", "#1a7f37", "#116329", "#033a16"],
}
LANG_COLORS = {"Python": "#3572A5", "C#": "#178600", "PHP": "#4F5D95", "JavaScript": "#f1e05a",
               "TypeScript": "#3178c6", "HTML": "#e34c26", "Rust": "#dea584", "C": "#555555",
               "Java": "#b07219", "Racket": "#3c5caa", "Jupyter Notebook": "#DA5B0B"}
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def level(n):
    return -1 if n <= 0 else min(len(RAMP) - 1, int(math.log2(n)))


def span(text, cls=None, fill=None, bold=False, extra=""):
    attrs = []
    if cls:
        attrs.append(f'class="{cls}"')
    if fill:
        attrs.append(f'fill="{fill}"')
    if bold:
        attrs.append('font-weight="700"')
    if extra:
        attrs.append(extra)
    return f'<tspan {" ".join(attrs)}>{escape(text)}</tspan>'


def streaks(counts):
    longest = cur = 0
    for n in counts:
        cur = cur + 1 if n > 0 else 0
        longest = max(longest, cur)
    current = 0
    for n in reversed(counts):
        if n <= 0:
            break
        current += 1
    return longest, current


def heatmap(th, greens, cal, x0, y0):
    start = datetime.date.fromisoformat(cal["start"])
    counts = cal["counts"]
    weeks = math.ceil(len(counts) / 7)
    gx = x0 + 4 * CW + CW            # grid starts after "Mon " + gap
    out = []

    # month labels: first week whose Sunday falls in a new month
    last_x = -1e9
    for w in range(weeks):
        d = start + datetime.timedelta(days=7 * w)
        prev = start + datetime.timedelta(days=7 * (w - 1))
        if w == 0 or d.month != prev.month:
            x = gx + w * COL
            if w == 0 and (d + datetime.timedelta(days=6)).month == d.month and d.day > 7:
                continue  # partial first month: skip its label like GitHub does
            if x - last_x >= 4 * CW:
                out.append(f'<text x="{x:.1f}" y="{y0:.1f}" class="dim">{MONTHS[d.month - 1]}</text>')
                last_x = x
    for r, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="{x0:.1f}" y="{y0 + (r + 1) * ROW + 4:.1f}" class="dim">{name}</text>')

    # cells: one glyph per day, grouped per week so the columns can sweep in left to right
    today = len(counts) - 1
    for w in range(weeks):
        cells = []
        for r in range(7):
            i = 7 * w + r
            if i >= len(counts):
                break
            n = counts[i]
            lv = level(n)
            x = gx + w * COL + (COL - CW) / 2
            y = y0 + (r + 1) * ROW + 4
            if lv < 0:
                cells.append(f'<text x="{x:.1f}" y="{y:.1f}" class="lo">·</text>')
            else:
                weight = ' font-weight="700"' if lv >= 6 else ""
                cells.append(f'<text x="{x:.1f}" y="{y:.1f}" class="g{lv}{" today" if i == today else ""}"{weight}>{escape(RAMP[lv])}</text>')
        out.append(f'<g class="wk" style="animation-delay:{0.15 + w * 0.018:.3f}s">{"".join(cells)}</g>')

    # legend + summary
    ly = y0 + 9 * ROW + 10
    legend = span("less ", "dim") + "".join(span(ch + " ", f"g{i}") for i, ch in enumerate(RAMP)) + span("more", "dim")
    out.append(f'<text x="{gx:.1f}" y="{ly:.1f}">{legend}</text>')
    total = sum(counts)
    longest, _ = streaks(counts)
    bi = max(range(len(counts)), key=lambda i: counts[i])
    bday = start + datetime.timedelta(days=bi)
    when = f"{MONTHS[bday.month - 1]} {bday.day}"
    summary = (span(f"{total:,}", "v") + span(" contributions · streak ", "dim") + span(f"{longest}d", "v")
               + span(" · peak ", "dim") + span(f"{counts[bi]}", "v") + span(f" ({when})", "dim"))
    plain = f"{total:,} contributions · streak {longest}d · peak {counts[bi]} ({when})"
    out.append(f'<text x="{W - PAD - len(plain) * CW:.1f}" y="{ly:.1f}">{summary}</text>')
    return out, ly, total


def listing(th, card, stats, x0, y0):
    meta = stats["projects"]
    rows = []
    for p in card["projects"]:
        m = meta.get(p["repo"])
        if not m:
            continue
        rows.append((m["pushed"], p, m))
    rows.sort(key=lambda r: r[0], reverse=True)       # ls -t: newest first
    name_w = max(len(p.get("name", p["repo"])) + 1 for _, p, _ in rows)
    out = [f'<text x="{x0:.1f}" y="{y0:.1f}" class="dim">total {len(rows)}</text>']
    for k, (pushed, p, m) in enumerate(rows):
        y = y0 + (k + 1) * LH
        d = datetime.date.fromisoformat(pushed)
        perms = "drwx------" if m.get("private") else "drwxr-xr-x"
        lang = m.get("language") or "—"
        date = f"{MONTHS[d.month - 1]} {d.day:>2}"
        name = p.get("name", p["repo"]) + "/"
        line = (span(perms + "  ", "dim")
                + span("● ", fill=LANG_COLORS.get(lang, th["dots"])) + span(f"{lang:<7} ", "x0")
                + span(date + "  ", "dim")
                + span(name, "dir") + span(" " * (name_w - len(name) + 1))
                + span(p["desc"], "cm"))
        out.append(f'<g class="row" style="animation-delay:{1.35 + k * 0.09:.2f}s"><text x="{x0:.1f}" y="{y:.1f}">{line}</text></g>')
    return out, y0 + len(rows) * LH


def render(theme, card, stats):
    th = THEMES[theme]
    greens = GREENS[theme]
    user, host = card["user"], card["host"]
    prompt = span(f"{user}@{host}:~$ ", "p")
    x0 = PAD
    body = []
    y = PAD + FONT * 0.9

    body.append(f'<text x="{x0}" y="{y:.1f}">{prompt}{span("git log --all --since=" + chr(34) + "1 year ago" + chr(34) + " | heatmap", "cmd")}</text>')
    hm, y_end, total = heatmap(th, greens, stats["calendar"], x0, y + LH + 6)
    body += hm

    y = y_end + LH * 1.6
    body.append(f'<text x="{x0}" y="{y:.1f}">{prompt}{span("ls -lt ~/projects", "cmd")}</text>')
    ls, y_end = listing(th, card, stats, x0, y + LH)
    body += ls

    y = y_end + LH * 1.6
    body.append(f'<text x="{x0}" y="{y:.1f}">{prompt}</text>')
    plen = len(f"{user}@{host}:~$ ")
    body.append(f'<rect class="cur" x="{x0 + plen * CW:.1f}" y="{y - FONT * 0.82:.1f}" width="{CW:.1f}" height="{FONT * 1.05:.1f}"/>')
    H = round(y + PAD)

    font_css = (ROOT / "scripts" / "font.css").read_text()
    css = f"""{font_css}
text{{font-family:'JBM',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:{FONT}px;fill:{th['text']};white-space:pre}}
.p{{fill:{th['accent']}}} .cmd{{fill:{th['text']}}} .dim{{fill:{th['dots']}}} .lo{{fill:{th['lo']}}}
.v{{fill:{th['value']}}} .x0{{fill:{th['text']}}} .dir{{fill:{th['value']};font-weight:700}} .cm{{fill:{th['mid']}}}
{" ".join(f".g{i}{{fill:{c}}}" for i, c in enumerate(greens))}
.wk,.row{{animation:in .35s ease-out both}}
@keyframes in{{from{{opacity:0}}to{{opacity:1}}}}
.today{{animation:pulse 1.6s ease-in-out infinite}}
@keyframes pulse{{50%{{opacity:.35}}}}
.cur{{fill:{th['text']};animation:b 1.1s steps(1) infinite}}
@keyframes b{{50%{{opacity:0}}}}
@media (prefers-reduced-motion: reduce){{.wk,.row,.today,.cur{{animation:none}}}}"""

    alt = (f"Terminal: {total:,} contributions in the last year as a text heatmap; projects: "
           + "; ".join(f'{p.get("name", p["repo"])} ({p["desc"]})' for p in card["projects"]))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{escape(alt)}">
<title>{escape(alt)}</title>
<style>
{css}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{th['bg']}" stroke="{th['border']}"/>
{chr(10).join(body)}
</svg>
"""


def main():
    card = json.loads((ROOT / "card.json").read_text(encoding="utf-8"))
    stats = json.loads((ROOT / "stats.json").read_text(encoding="utf-8"))
    if "calendar" not in stats or "projects" not in card:
        print("no calendar/projects yet: skipping session cards")
        return
    for name in THEMES:
        (ROOT / f"session_{name}.svg").write_text(render(name, card, stats), encoding="utf-8")
        print(f"wrote session_{name}.svg")


if __name__ == "__main__":
    main()
