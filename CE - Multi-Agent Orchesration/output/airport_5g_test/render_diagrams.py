"""Render ASCII diagrams as branded PNG images for the board report."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import subprocess, sys

OUT = Path("/Users/scottewalt/Documents/CE - AGENTS/CE - Multi-Agent Orchesration/output/airport_5g_test")

# Brand colors
BG = (26, 26, 46)        # #1A1A2E deep navy
ACCENT = (0, 180, 216)   # #00B4D8 cyan
TEXT = (224, 230, 236)    # light text on dark
LABEL = (171, 184, 195)  # #ABB8C3 muted
BORDER = (0, 119, 182)   # #0077B6

# Try to find a good monospace font
FONT_CANDIDATES = [
    "/System/Library/Fonts/SFMono-Regular.otf",
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Monaco.ttf",
    "/Library/Fonts/Courier New.ttf",
]
font_path = None
for f in FONT_CANDIDATES:
    if Path(f).exists():
        font_path = f
        break

TITLE_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Avenir Next.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
]
title_path = None
for f in TITLE_CANDIDATES:
    if Path(f).exists():
        title_path = f
        break

TITLES = [
    "Timeline Overlay: Construction-Driven Decision Windows",
    "Hypothesis A: Zone-Optimized Federated Architecture",
    "Hypothesis B: Carrier-Managed Unified Platform",
    "Hypothesis C: Distributed Edge Architecture",
    "Hypothesis D: Phased Convergence Architecture",
]

for i in range(5):
    txt_file = OUT / f"diagram_{i}.txt"
    if not txt_file.exists():
        continue

    content = txt_file.read_text().rstrip("\n")
    lines = content.split("\n")

    # Calculate dimensions
    font_size = 16
    try:
        mono_font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    except Exception:
        mono_font = ImageFont.load_default()

    try:
        title_font = ImageFont.truetype(title_path, 22) if title_path else ImageFont.load_default()
    except Exception:
        title_font = ImageFont.load_default()

    # Measure text
    max_width = max(len(l) for l in lines) if lines else 40
    char_w = font_size * 0.62  # approximate for monospace
    char_h = font_size * 1.4

    pad_x, pad_y = 50, 30
    title_h = 60
    img_w = int(max_width * char_w + pad_x * 2)
    img_h = int(len(lines) * char_h + pad_y * 2 + title_h)

    # Minimum width
    img_w = max(img_w, 700)

    img = Image.new("RGB", (img_w, img_h), BG)
    draw = ImageDraw.Draw(img)

    # Accent line at top
    draw.rectangle([0, 0, img_w, 4], fill=ACCENT)

    # Title
    title = TITLES[i] if i < len(TITLES) else f"Diagram {i+1}"
    draw.text((pad_x, pad_y - 5), title, font=title_font, fill=ACCENT)

    # Diagram lines
    y = pad_y + title_h
    for line in lines:
        # Color box-drawing characters in accent, text in light
        x = pad_x
        for ch in line:
            if ch in "┌┐└┘├┤┬┴┼─│▼▲►◄╔╗╚╝║═╠╣╬╦╩":
                color = ACCENT
            elif ch in "│┤├":
                color = ACCENT
            else:
                color = TEXT
            draw.text((x, y), ch, font=mono_font, fill=color)
            x += char_w
        y += char_h

    # Bottom accent line
    draw.rectangle([0, img_h - 3, img_w, img_h], fill=BORDER)

    out_path = OUT / f"diagram_{i}.png"
    img.save(str(out_path), "PNG")
    print(f"Rendered: {out_path.name} ({img_w}x{img_h})")

print("Done.")
