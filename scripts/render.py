"""Render dark_mode.svg and light_mode.svg from card.json, stats.json and the ASCII art.

Standard library only, so the GitHub Action needs no dependencies.
Usage: python scripts/render.py
"""
import json
import pathlib
from html import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent

THEMES = {
    "dark": dict(bg="#161b22", border="#30363d", text="#c9d1d9", key="#ffa657",
                 value="#a5d6ff", dots="#616e7f", art="#c9d1d9", accent="#3fb950",
                 lo="#353c46", mid="#7d8590", hi="#f0f6fc", sel="#1f6feb", ascii="ascii_dark.txt"),
    "light": dict(bg="#f6f8fa", border="#d0d7de", text="#24292f", key="#953800",
                  value="#0a3069", dots="#8c959f", art="#24292f", accent="#1a7f37",
                  lo="#d3d9e0", mid="#8c959f", hi="#1f2328", sel="#54aeff", ascii="ascii_light.txt"),
}

FONT = 16            # info text size (px)
CW = FONT * 0.6      # JetBrains Mono advance width
LH = 21              # info line height
ART_FONT = 12
ART_CW = ART_FONT * 0.6
ART_LH = 14.6
PAD = 26


def fmt_stats(stats):
    langs = " · ".join(f"{name} {pct}%" for name, pct in stats["languages"])
    return {
        "repos": f'{stats["repos"]:,}',
        "forks": f'{stats["forks"]:,}',
        "commits": f'{stats["commits"]:,}',
        "contributions": f'{stats["contributions"]:,}',
        "languages": langs,
    }


def t(s, cls):
    return f'<tspan class="{cls}">{escape(s)}</tspan>'


def build_lines(card, stats):
    width = card["width"]
    user, host = card["user"], card["host"]
    rows = []
    head = f"{user}@{host}"
    rows.append(t(user, "k") + t("@", "x") + t(host, "k") + t(" " + "—" * (width - len(head) - 1), "d"))
    for ln in card["lines"]:
        kind = ln["type"]
        if kind == "blank":
            rows.append("")
        elif kind == "section":
            label = f'— {ln["title"]} '
            rows.append(t("— ", "d") + t(ln["title"], "x") + t(" " + "—" * (width - len(label)), "d"))
        elif kind == "kv":
            key = ln["key"] + ":"
            val = ln["value"].format(**stats)
            dots = max(2, width - len(key) - len(val) - 2)
            rows.append(t(key, "k") + t(" " + "." * dots + " ", "d") + t(val, "v"))
    return rows


def render(theme_name, card, stats):
    th = THEMES[theme_name]
    art = (ROOT / th["ascii"]).read_text(encoding="utf-8").rstrip("\n").split("\n")
    art_cols = max(len(r) for r in art)
    art_w = art_cols * ART_CW
    art_h = len(art) * ART_LH

    rows = build_lines(card, stats)
    text_x = PAD + art_w + 34
    text_w = card["width"] * CW
    W = round(text_x + text_w + PAD)
    info_h = (len(rows) + 2) * LH
    H = round(max(art_h, info_h) + PAD * 2)

    art_y0 = (H - art_h) / 2 + ART_FONT * 0.8
    mask_file = ROOT / "ascii_mask.txt"
    if mask_file.exists():
        # two-tone art: each cell is dim, mid or bright according to the mask (' ', '+', '@')
        mask = mask_file.read_text(encoding="utf-8").rstrip("\n").split("\n")
        tone = {" ": "lo", "+": "mid", "@": "hi"}
        lines, sel = [], []
        highlight = (ROOT / "card.json").exists() and json.loads((ROOT / "card.json").read_text(encoding="utf-8")).get("highlight", False)
        for i, r in enumerate(art):
            if highlight:
                m = mask[i] if i < len(mask) else ""
                y_top = art_y0 + i * ART_LH - ART_LH * 0.74
                j = 0
                while j < len(m):
                    if m[j] in "+@":
                        k = j
                        while k < len(m) and m[k] == m[j]:
                            k += 1
                        op = ".42" if m[j] == "@" else ".18"
                        sel.append(f'<rect x="{PAD + j * ART_CW:.2f}" y="{y_top:.2f}" width="{(k - j) * ART_CW:.2f}" height="{ART_LH:.2f}" fill="{th["sel"]}" fill-opacity="{op}"/>')
                        j = k
                    else:
                        j += 1
            m = mask[i] if i < len(mask) else ""
            runs, cur, buf = [], None, ""
            for j, ch in enumerate(r):
                c = tone.get(m[j] if j < len(m) else " ", "lo")
                if c != cur and buf:
                    runs.append((cur, buf)); buf = ""
                cur = c; buf += ch
            if buf:
                runs.append((cur, buf))
            spans = "".join(t(txt, c) for c, txt in runs)
            lines.append(f'<text x="{PAD}" y="{art_y0 + i * ART_LH:.1f}" class="art">{spans}</text>')
        art_svg = "\n".join(sel + lines)
    else:
        art_svg = "\n".join(
            f'<text x="{PAD}" y="{art_y0 + i * ART_LH:.1f}" class="art">{escape(r)}</text>' for i, r in enumerate(art)
        )
    info_y0 = (H - info_h) / 2 + FONT * 0.85
    info_svg = "\n".join(
        f'<text x="{text_x:.1f}" y="{info_y0 + i * LH:.1f}">{r}</text>' for i, r in enumerate(rows) if r
    )
    cy = info_y0 + (len(rows) + 1) * LH
    prompt = f'{card["user"]}@{card["host"]}:~$ '
    cursor = (
        f'<text x="{text_x:.1f}" y="{cy:.1f}">{t(prompt, "p")}</text>'
        f'<rect class="cur" x="{text_x + len(prompt) * CW:.1f}" y="{cy - FONT * 0.82:.1f}" width="{CW:.1f}" height="{FONT * 1.05:.1f}"/>'
    )

    font_css = (ROOT / "scripts" / "font.css").read_text()
    css = f"""{font_css}
text{{font-family:'JBM',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:{FONT}px;fill:{th['text']};white-space:pre}}
.art{{font-size:{ART_FONT}px;fill:{th['art']}}}
.k{{fill:{th['key']}}} .v{{fill:{th['value']}}} .d{{fill:{th['dots']}}} .x{{fill:{th['text']};font-weight:700}}
.p{{fill:{th['accent']}}}
.lo{{fill:{th['lo']}}} .mid{{fill:{th['mid']}}} .hi{{fill:{th['hi']};font-weight:700}}
.cur{{fill:{th['text']};animation:b 1.1s steps(1) infinite}}
@keyframes b{{50%{{opacity:0}}}}
@media (prefers-reduced-motion: reduce){{.cur{{animation:none}}}}"""

    alt = f'{card["user"]}@{card["host"]} — ' + "; ".join(
        f'{ln["key"]}: {ln["value"].format(**stats)}' for ln in card["lines"] if ln["type"] == "kv"
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{escape(alt)}">
<title>{escape(alt)}</title>
<style>
{css}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="{th['bg']}" stroke="{th['border']}"/>
{art_svg}
{info_svg}
{cursor}
</svg>
"""


def main():
    card = json.loads((ROOT / "card.json").read_text(encoding="utf-8"))
    stats = fmt_stats(json.loads((ROOT / "stats.json").read_text(encoding="utf-8")))
    for name in THEMES:
        (ROOT / f"{name}_mode.svg").write_text(render(name, card, stats), encoding="utf-8")
        print(f"wrote {name}_mode.svg")


if __name__ == "__main__":
    main()
