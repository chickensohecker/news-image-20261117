#!/usr/bin/env python3
"""The World in One Day -- Tuesday, 17 November 2026.

A one-page newspaper front page that sums up the day's world news, drawn
entirely in code: a small bitmap font (rasterised from DejaVu Sans, stored
below as glyph bitmaps), a layout engine, and a pure-stdlib PNG writer.

Runs with no network and no third-party packages: only the Python standard
library. The output is deterministic -- the same bytes on every run.

Usage (local):  mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
In the grader:   python3 main.py            (writes /output/entry.png)
"""

import os
import struct
import zlib

W, H = 1024, 1024

# --- palette ---------------------------------------------------------------
PAPER = (247, 243, 234)   # warm newsprint
INK = (26, 26, 26)        # near-black text
NAVY = (18, 40, 75)       # masthead band
NAVY_SOFT = (38, 62, 102)
GOLD = (184, 138, 29)     # masthead rule
RED = (178, 38, 30)       # war / breaking kicker
TEAL = (14, 107, 107)     # diplomacy kicker
BLUE = (31, 90, 160)      # markets kicker
PLUM = (122, 54, 96)      # aid kicker
GREY = (107, 107, 107)    # secondary text
RULE = (26, 26, 26)
FAINT_RULE = (190, 184, 172)


class Canvas:
    """A flat RGB pixel buffer with tiny drawing helpers."""

    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg) * (w * h)

    def _off(self, x, y):
        return (y * self.w + x) * 3

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            o = self._off(x, y)
            self.px[o:o + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            o = self._off(x0, yy)
            self.px[o:o + len(row)] = row

    def hline(self, x, y, w, color, thick=1):
        self.rect(x, y, w, thick, color)

    def circle(self, cx, cy, r, color):
        # Midpoint circle outline, one pixel thick.
        x, y = 0, r
        d = 1 - r
        while x <= y:
            for dx, dy in ((x, y), (y, x), (-x, y), (-y, x),
                           (x, -y), (y, -x), (-x, -y), (-y, -x)):
                self.set(cx + dx, cy + dy, color)
            if d < 0:
                d += 2 * x + 3
            else:
                d += 2 * (x - y) + 5
                y -= 1
            x += 1

    def ellipse_arc(self, cx, cy, rx, ry, color):
        # A squashed circle outline, for the globe's meridian.
        steps = 360
        for i in range(steps):
            a = 2 * 3.141592653589793 * i / steps
            import math
            self.set(round(cx + rx * math.cos(a)),
                     round(cy + ry * math.sin(a)), color)


def png_bytes(canvas):
    """Encode the canvas as a PNG (8-bit RGB, no filtering)."""
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)
        raw += canvas.px[y * stride:(y + 1) * stride]

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
            + chunk(b"IEND", b""))


# --- bitmap font -----------------------------------------------------------
# FONT maps an ASCII code to (ink width, top offset from baseline, rows,
# hex rows). Each row is ceil(width/8) bytes, most-significant bit first.
# The glyphs were rasterised from DejaVu Sans at 30 px and stored here as
# bitmaps so the program needs no font file at run time.

FONT = {
32: (10, 0, 0, ''),
33: (4, -22, 22, '70707070707070707060606060606000000070707070'),
34: (9, -22, 8, '63806380638063806380638063806380'),
35: (21, -22, 22, '0061c000e18000e18000c18000c38001c3003ffff83ffff83ffff8018700038600030600030e00ffffe0ffffe0ffffe0061c00061c000e18000c18000c38000c3800'),
36: (15, -22, 26, '0100010001000fe03ff87ff8791871006100610071003f001ff003f8013c010c010e010e413cfffcfff81fe00100010001000100'),
37: (26, -22, 22, '1f0018003f80300071c0700070c0600060e0c00060e1c00060e1800060e3800070c3000071c600003f8e1e001f0c7f00001863800018e1800030c1c00070c1c00060c1c000c0c1c001c0e1800180638003807f0003001e00'),
38: (22, -22, 22, '01f80007fc000ffc000f04001c00001c00000c00000e00000700000f80001dc03038f030707870703c60701ee0700fc07007c07803c03e0fe01ffee00ffc7003f078'),
39: (4, -22, 8, '6060606060606060'),
40: (8, -23, 27, '060e0c1c183830707070707070607070707070703038181c0c0e06'),
41: (8, -23, 27, '60703038381c1c1c0c0e0e0e0e0e0e0e0e0e0c1c1c1c3838307060'),
42: (15, -22, 14, '010001000100610c711c1ff007c007c01ff0711c610c010001000100'),
43: (19, -18, 18, '00e00000e00000e00000e00000e00000e00000e00000e000ffffe0ffffe000e00000e00000e00000e00000e00000e00000e00000e000'),
44: (5, -4, 7, '383878707060c0'),
45: (9, -9, 2, 'ff00ff00'),
46: (4, -4, 4, 'e0e0e0e0'),
47: (11, -22, 25, '01c001c0018001800380030003000700070006000e000e000c000c001c0018001800380030003000700070006000e000e000'),
48: (16, -22, 22, '07c01ff03ff83c7c701c701ce00ee00ee00ee00ee00ee00ee00ee00ee00ee00e701c701c3c7c3ff81ff007c0'),
49: (14, -22, 22, '1f00ff00ff00e3000300030003000300030003000300030003000300030003000300030003007ff87ff87ff8'),
50: (15, -22, 22, '1fc0fff0fff8e078003c001c001c001c00380038007000e001c0038007000e001c0038007000fffcfffcfffc'),
51: (15, -22, 22, '1fc07ff07ff8607c001c001c001c001c00380ff00fe00ff8003c001c000e000e000e001cc07cfff8fff03fc0'),
52: (17, -22, 22, '00780000780000f80001f80001b8000338000738000638000c38001c3800183800383800703800603800ffff00ffff00ffff00003800003800003800003800003800'),
53: (15, -22, 22, '7ff87ff87ff8700070007000700070007fc07ff07ff8607c003c001c001c001c001c003cc07cfff8fff03fc0'),
54: (16, -22, 22, '03f00ffc1ffc3e0c380078007000f000e3e0eff8fffcfc3cf01ef00ef00e700e700e701e3c3c3ffc1ff807e0'),
55: (15, -22, 22, 'fffefffcfffc001c0038003800380070007000e000e000e001c001c0038003800380070007000f000e000e00'),
56: (16, -22, 22, '0fe03ff87ffc783c701c700e700c701c383c1ff00fe03ff8783cf01ee00ee00ee00ef01e783c7ffc3ff80fe0'),
57: (16, -22, 22, '07e01ff83ffc3c3c780e700e700f700f700f780f3c3f3fff1ff707c7000f000e000e001e307c3ff83ff00fc0'),
58: (4, -16, 16, '70707070000000000000000070707070'),
59: (5, -16, 19, '383838380000000000000000383878707060c0'),
60: (19, -17, 16, '0000200001e0000fe0007f8003fc000fe0007f0000f80000f800007f00000fe00003fc00007f80000fe00001e0000020'),
61: (19, -14, 8, 'ffffe0ffffe0000000000000000000000000ffffe0ffffe0'),
62: (19, -17, 16, 'c00000f00000fe00001fc00007f80000fe00001fc00003e00003e0001fc000fe0007f8001fc000fe0000f00000c00000'),
63: (12, -22, 22, '1f807fc0ffe0e1f080f00070007000e001e003c007800f000e000e000e000e00000000000e000e000e000e00'),
64: (26, -21, 26, '003f800001fff00007fff8000fc07e001e001e003c00070038000380703e6180607f61c060ffe0c0c1e1e0c0c1c0e0c0c18060c0c18061c0c1c0e380c1e1e780e0ffff00607f7e00703e7000380000003c0000001e0018000fc0780007fff80001ffe000003f8000'),
65: (21, -22, 22, '00f00000f80000f80001f80001dc00039c00038c00038e00070e000707000707000e07000e03801c03801fff801fffc03fffc03801e03800e07000e0700070f00070'),
66: (17, -22, 22, '7ff0007ffc007ffe00701e00700e00700700700600700e00701e007ffc007ff8007ffc00700e00700700700700700700700700700700700f007ffe007ffc007ff000'),
67: (19, -22, 22, '00fe0007ff800fffc01f01c03c00403800007800007000007000007000007000007000007000007000007000007800003800003c00401f01c00fffc007ff8000fe00'),
68: (20, -22, 22, '7ff0007ffe007fff00701f807007c07001c07001e07000e07000e07000e07000e07000e07000e07000e07000e07001e07001c07007c0701f807fff007ffe007ff000'),
69: (16, -22, 22, '7ffe7ffe7ffe7000700070007000700070007ffc7ffc7ffc70007000700070007000700070007ffe7ffe7ffe'),
70: (14, -22, 22, '7ffc7ffc7ffc7000700070007000700070007ff87ff87ff87000700070007000700070007000700070007000'),
71: (20, -22, 22, '00ff0007ffc00fffe01f00e03c0020380000780000700000700000700000700ff0700ff0700ff07000707000707800703800703c00701f01f00fffe007ffc000fe00'),
72: (18, -22, 22, '7001c07001c07001c07001c07001c07001c07001c07001c07001c07fffc07fffc07fffc07001c07001c07001c07001c07001c07001c07001c07001c07001c07001c0'),
73: (4, -22, 22, '70707070707070707070707070707070707070707070'),
74: (8, -22, 28, '07070707070707070707070707070707070707070707070f1efefcf0'),
75: (19, -22, 22, '700780700f00701e00703c0070780070f00071e00073c0007780007e00007e00007f000077800073c00071e00070f000707800703c00701e00700f007007807003c0'),
76: (15, -22, 22, '70007000700070007000700070007000700070007000700070007000700070007000700070007ffe7ffe7ffe'),
77: (21, -22, 22, '7c00f87c00f87c00f87e01f87e01b87601b87703b873033873073873873871863871ce3871cc3870cc3870fc38707838707838707838700038700038700038700038'),
78: (18, -22, 22, '7801c07c01c07c01c07e01c07e01c07701c07701c07381c07381c071c1c071c1c070e1c07071c07071c07039c07039c0701dc0701fc0700fc0700fc07007c07007c0'),
79: (21, -22, 22, '00fc0007ff000fffc01f03e03c01e03800f07800707000707000387000387000387000387000387000387000707800703800f03c01e01f03e00fffc007ff0000fc00'),
80: (16, -22, 22, '7fe07ff87ffc703c701e700e700e700e701e703c7ffc7ff87fe0700070007000700070007000700070007000'),
81: (21, -22, 26, '00fc0007ff000fffc01f03e03c01e03800f07800707000707000387000387000387000387000387000387000707800703800f03c01e01f03c00fff8007ff0000fe00000f000007800003c00001c0'),
82: (18, -22, 22, '7fe0007ff8007ffc00703e00701e00700e00700e00700e00701e00703c007ff8007ff0007ff000707800701c00701e00700e00700f007007007003807003807001c0'),
83: (16, -22, 22, '0ff03ffc7ffc780cf000e000e000e000f0007f003ff00ff800fc001e000e000e000e000ec03efffcfff83fe0'),
84: (20, -22, 22, '7fffe07fffe07fffe0007000007000007000007000007000007000007000007000007000007000007000007000007000007000007000007000007000007000007000'),
85: (18, -22, 22, '7003807003807003807003807003807003807003807003807003807003807003807003807003807003807003807003807003807807803c0f001ffe000ffc0003f000'),
86: (21, -22, 22, 'f000707000707000e03800e03800e03801c01c01c01c03801e03800e03800e0700070700070700070e00038e00039c00039c0001dc0001f80000f80000f80000f000'),
87: (28, -22, 22, 'e00f0070e00f00e0700f00e0701f00e0701b80e0701b81c0381981c0383981c03831c1c03831c3801c30c3801c70c3801c70e3801c60e7000e6067000ee067000ee077000ec07e0007c03e0007c03e0007c03e0007803c00'),
88: (20, -22, 22, '3800e01c01c00e03800e0380070700038e00038e0001dc0000f80000f80000700000f80001f80001dc00039e00078e000707000e07801c03801c01c03801e07000e0'),
89: (19, -22, 22, 'e001c07003803803803807001c0e000e0e000e1c0007380003b80003f00001e00000e00000e00000e00000e00000e00000e00000e00000e00000e00000e00000e000'),
90: (19, -22, 22, '7fffc07fffc07fffc0000380000700000e00001c00003c0000380000700000e00001c0000380000380000700000e00001c00003800007000007fffc0ffffc0ffffc0'),
91: (7, -23, 27, '7e7e7e6060606060606060606060606060606060606060607e7e7e'),
92: (11, -22, 25, 'e000e000600070007000300030003800180018001c000c000c000e000e000600070007000300030003800180018001c001c0'),
93: (8, -23, 27, '7e7e7e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e7e7e7e'),
94: (19, -22, 8, '00e00001f00003f800071c000e0e001c07003803807001c0'),
95: (17, 4, 3, '7fff007fff007fff00'),
96: (8, -24, 6, '7030381c0c06'),
97: (15, -16, 16, '0fe03ff03ff8303c000c000c0ffe3ffe3ffe780e700e701e783e7ffe3fee0f8e'),
98: (16, -23, 23, '600060006000600060006000600063e067f87ffc7c3c781e700e700e60066006700e700e781e7c3c7ffc67f863e0'),
99: (14, -16, 16, '03f00ffc1ffc3c0c780070007000700070007000700078003c0c1ffc0ffc03f0'),
100: (16, -23, 23, '000600060006000600060006000607c61fe63ffe3c3e781e700e700e60066006700e700e781e3c3e3ffe1fe607c6'),
101: (16, -16, 16, '03f00ff81ffc3c1e700670077fff7fff7fff7000700078023c0e1ffe0ffc03f0'),
102: (12, -23, 23, '03e007e00fe00e001c001c001c007fc07fc07fc01c001c001c001c001c001c001c001c001c001c001c001c001c00'),
103: (16, -16, 22, '07c61fe63ffe3c3e780e700e700e60066006700e700e780e3c3e3ffe1fe607ce000e001e103c1ffc1ff80fe0'),
104: (15, -23, 23, '600060006000600060006000600063e067f87ffc7c3c701c700c700c600c600c600c600c600c600c600c600c600c'),
105: (4, -23, 23, '7070700000000070707070707070707070707070707070'),
106: (7, -23, 29, '0e0e0e000000000e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0e0c0c1cfcf8f0'),
107: (16, -23, 23, '6000600060006000600060006000601c6038607061e063c067807e007c007e006700638061c060f06078603c601e'),
108: (4, -23, 23, '7070707070707070707070707070707070707070707070'),
109: (25, -16, 16, '63e07c0067f1fe007ffbff007c3f0f00701e0700701c0380701c0380601c0380601c0380601c0380601c0380601c0380601c0380601c0380601c0380601c0380'),
110: (15, -16, 16, '63e067f87ffc7c3c701c700c700c600c600c600c600c600c600c600c600c600c'),
111: (16, -16, 16, '07e01ff83ffc3c3e780e700e7007700770077007700e780e3c3e3ffc1ff807e0'),
112: (16, -16, 22, '63e067f87ffc7c3c781e700e700e60066006700e700e781e7c3c7ffc67f863e0600060006000600060006000'),
113: (16, -16, 22, '07c61fe63ffe3c3e781e700e700e60066006700e700e781e3c3e3ffe1fe607c6000600060006000600060006'),
114: (11, -16, 16, '63c067c07fc07c00700070007000600060006000600060006000600060006000'),
115: (14, -16, 16, '0fe03ff07ff07010600070003c001fc001f000380038003870787ff87ff00fc0'),
116: (12, -21, 21, '1c001c001c001c001c007fe07fe07fe01c001c001c001c001c001c001c001c001c001c001fe00fe007e0'),
117: (15, -16, 16, '600c600c600c600c600c600c600c600c600c600c601c701c787c7ffc3fcc0f8c'),
118: (17, -16, 16, '700380700700380700380700180e001c0e001c0c000e1c000e1c0006380007380007300003f00003f00003e00001e000'),
119: (23, -16, 16, 'e0381c60781c707c1c707c1870ec3830ec3838ce3838c63019c6701d86701d87601d83e00f83e00f03e00f03c00f01c0'),
120: (17, -16, 16, '3807001c0e001c1e000e1c0007380003f00003f00001e00001e00003f0000778000e38000e1c001c0e00380f00700700'),
121: (17, -16, 22, '7003803007003807003806001c0e001c0c000c1c000e1c0006180007380007300003700003e00001e00001e00001c00001c0000180000380003f00003f00003e0000'),
122: (14, -16, 16, '7ff87ff87ff80030006000c00180038007000e001c00380070007ff8fff8fff8'),
123: (13, -23, 28, '00f003f003f0038007000700070007000700070007000f007e007c007e000f0007000700070007000700070007000700038003f003f000f0'),
124: (4, -23, 30, '606060606060606060606060606060606060606060606060606060606060'),
125: (13, -23, 28, '78007e007e000f000700070007000700070007000700078003f001f003f00380070007000700070007000700070007000f007e007e007800'),
126: (19, -12, 6, '0000001f00207fe0e0e0ffc0801f00000000'),
}


# --- text engine -----------------------------------------------------------
# Glyphs are drawn at an integer scale; a faux-bold pass (a second draw
# offset by half a scale step) thickens headlines and kickers.

def _glyph(code):
    return FONT.get(code, FONT[32])


def text_width(text, scale, bold=False):
    w = 0
    for ch in text:
        gw, _, _, _ = _glyph(ord(ch))
        w += (gw + 1) * scale
    if bold:
        w += max(1, scale // 2)
    return w - scale if text else 0


def draw_glyph(cv, code, x, baseline, scale, color, bold=False):
    w, yoff, h, hexrows = _glyph(code)
    if h == 0:
        return
    data = bytes.fromhex(hexrows)
    nbytes = (w + 7) // 8
    offsets = (0,) if not bold else (0, max(1, scale // 2))
    for ox in offsets:
        for r in range(h):
            row = data[r * nbytes:(r + 1) * nbytes]
            for cx in range(w):
                if row[cx // 8] >> (7 - cx % 8) & 1:
                    cv.rect(x + ox + cx * scale,
                            baseline + (yoff + r) * scale,
                            scale, scale, color)


def draw_text(cv, text, x, baseline, scale, color, bold=False):
    cx = x
    for ch in text:
        gw, _, _, _ = _glyph(ord(ch))
        draw_glyph(cv, ord(ch), cx, baseline, scale, color, bold)
        cx += (gw + 1) * scale
    return cx


def wrap(text, scale, max_w, bold=False):
    """Greedy word wrap; returns a list of lines that fit max_w."""
    words = text.split(" ")
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale, bold) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_scale(text, max_w, scales=(3, 2, 1), bold=False):
    for s in scales:
        if text_width(text, s, bold) <= max_w:
            return s
    return 1


# --- the day's news --------------------------------------------------------
# Summaries written for this page from the day's reporting (17 Nov 2026).

MASTHEAD = "THE WORLD IN ONE DAY"
DATE_LINE = "TUESDAY, 17 NOVEMBER 2026"

LEAD = {
    "kicker": "UKRAINE - WAR IN EUROPE",
    "color": RED,
    "headline": "BRIDGES FALL ON BOTH SIDES IN THE UKRAINE WAR",
    "deck": "Kyiv says its forces hit the bridge to Crimea for a second "
            "day, collapsing a section. Russian missiles hit two bridges "
            "over the Dnipro.",
}

STORIES = [
    {
        "kicker": "THE GULF - IRAN AND THE US",
        "color": TEAL,
        "headline": "Iran drones target US radar in Bahrain",
        "deck": "Bahrain says it shot them down; a third US carrier "
                "reaches the Gulf.",
    },
    {
        "kicker": "DIPLOMACY - APEC IN SHENZHEN",
        "color": NAVY_SOFT,
        "headline": "Xi, Trump and Putin to meet in Shenzhen",
        "deck": "China confirms the first three-way talks of the three "
                "leaders.",
    },
    {
        "kicker": "MARKETS - TECH",
        "color": BLUE,
        "headline": "Nvidia reports after a scandal shook the chip giant",
        "deck": "First results since Jensen Huang quit, as US chip curbs "
                "tighten.",
    },
    {
        "kicker": "GAZA - AID AND WINTER",
        "color": PLUM,
        "headline": "Winter rains deepen the crisis in Gaza",
        "deck": "UN warns 1.4 million face acute hunger; allies press "
                "for aid.",
    },
]

ALSO = ("Cyclone Akvan nears India's east coast  -  Japan scrambles jets "
        "over Russian planes  -  India take the ODI series in New Zealand")

FOOTER = "All stories as reported on Tuesday, 17 November 2026."


# --- layout ----------------------------------------------------------------

MARGIN = 36
CW = W - 2 * MARGIN  # 952


def draw_globe(cv, cx, cy, r, color):
    cv.circle(cx, cy, r, color)
    cv.ellipse_arc(cx, cy, r // 2, r, color)
    cv.hline(cx - r, cy, 2 * r, color)
    cv.ellipse_arc(cx, cy, r, r // 2, color)


def render():
    cv = Canvas(W, H, PAPER)

    # Masthead band.
    cv.rect(0, 0, W, 104, NAVY)
    draw_globe(cv, 62, 52, 30, GOLD)
    scale = fit_scale(MASTHEAD, 780, bold=True)
    tw = text_width(MASTHEAD, scale, bold=True)
    draw_text(cv, MASTHEAD, (W - tw) // 2, 52 + 11 * scale, scale,
              (255, 255, 255), bold=True)
    cv.hline(0, 104, W, GOLD, 3)

    # Date strip.
    y = 104
    draw_text(cv, DATE_LINE, MARGIN, y + 24, 1, INK, bold=True)
    right = "ONE DAY - ONE PAGE"
    draw_text(cv, right, W - MARGIN - text_width(right, 1), y + 24, 1,
              GREY)
    cv.hline(MARGIN, y + 32, CW, RULE, 2)

    # Lead story.
    y = 152
    cv.rect(MARGIN, y + 2, 10, 18, LEAD["color"])
    draw_text(cv, LEAD["kicker"], MARGIN + 18, y + 20, 1, LEAD["color"],
              bold=True)
    y += 30
    for line in wrap(LEAD["headline"], 2, CW, bold=True):
        draw_text(cv, line, MARGIN, y + 44, 2, INK, bold=True)
        y += 52
    y += 6
    for line in wrap(LEAD["deck"], 1, CW):
        draw_text(cv, line, MARGIN, y + 22, 1, INK)
        y += 32
    y += 14
    cv.hline(MARGIN, y, CW, RULE, 2)
    y += 16

    # Four stacked stories.
    for st in STORIES:
        cv.rect(MARGIN, y + 2, 10, 18, st["color"])
        draw_text(cv, st["kicker"], MARGIN + 18, y + 20, 1, st["color"],
                  bold=True)
        y += 30
        for line in wrap(st["headline"], 1, CW, bold=True):
            draw_text(cv, line, MARGIN, y + 22, 1, INK, bold=True)
            y += 30
        for line in wrap(st["deck"], 1, CW):
            draw_text(cv, line, MARGIN, y + 22, 1, (64, 64, 64))
            y += 30
        y += 12
        cv.hline(MARGIN, y, CW, FAINT_RULE, 1)
        y += 14

    # Also today.
    draw_text(cv, "ALSO TODAY", MARGIN, y + 20, 1, RED, bold=True)
    y += 30
    for line in wrap(ALSO, 1, CW):
        draw_text(cv, line, MARGIN, y + 22, 1, INK)
        y += 30
    y += 12
    cv.hline(MARGIN, y, CW, RULE, 2)
    y += 10
    draw_text(cv, FOOTER, MARGIN, y + 18, 1, GREY)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = png_bytes(render())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print(f"wrote {path}: {len(data)} bytes, {W}x{H}")


if __name__ == "__main__":
    main()
