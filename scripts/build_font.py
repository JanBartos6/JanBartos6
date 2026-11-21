"""Rebuild scripts/font.css: JetBrains Mono (OFL) regular + bold, subset and base64-embedded.

Only needed when a new non-ASCII character appears on a card; the GitHub Action never runs it.
Usage: pip install fonttools brotli && python scripts/build_font.py path/to/JetBrainsMono/webfonts
"""
import base64
import io
import pathlib
import sys

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
# all printable ASCII, so daily data (dates, numbers, repo text) never needs a rebuild,
# plus the symbols and accented letters the cards use
EXTRA = "·→←—–…●○■□▪░▒▓█│─├└┌┐┘┬┴┼✓✗★☆áéíóúýčďěňřšťůžÁČŠŽäöüß"
TEXT = "".join(chr(c) for c in range(0x20, 0x7F)) + EXTRA


def face(path, weight):
    font = TTFont(path)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = []  # no ligatures: code should render char by char
    opts.name_IDs = []
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(text=TEXT)
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:'JBM';font-weight:{weight};src:url(data:font/woff2;base64,{b64}) format('woff2')}}"


def main():
    src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    css = face(src / "JetBrainsMono-Regular.woff2", 400) + "\n" + face(src / "JetBrainsMono-Bold.woff2", 700) + "\n"
    (ROOT / "scripts" / "font.css").write_text(css)
    print(f"wrote scripts/font.css ({len(css) // 1024} KB, {len(TEXT)} glyphs per weight)")


if __name__ == "__main__":
    main()
