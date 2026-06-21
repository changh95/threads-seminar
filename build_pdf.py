#!/usr/bin/env python3
"""
Offline PDF renderer for the Threads Seminar deck.

Reproduces the ivory matte texture (radial ivory gradient + fine paper grain)
and renders each 16:9 slide with Korean support. Uses pycairo, which resolves
Noto Sans CJK KR via fontconfig and embeds glyphs as vectors — no browser, no
network needed. Slide content is data-driven (SLIDES) so it grows with index.html.

Usage:  python3 build_pdf.py   ->  threads-seminar.pdf
"""

import io
import os
import cairo
import numpy as np
from PIL import Image, ImageFilter

# ---------- geometry (16:9) ----------
W, H = 1280.0, 720.0

# ---------- palette (mirrors index.html :root) ----------
IVORY_BASE  = (0xF6, 0xF1, 0xE7)
IVORY_LIGHT = (0xFB, 0xF8, 0xF0)
IVORY_DEEP  = (0xEC, 0xE4, 0xD4)
INK         = (0x2B, 0x27, 0x23)
INK_SOFT    = (0x6B, 0x63, 0x58)
ACCENT      = (0xCC, 0x78, 0x5C)   # Anthropic clay

def rgb(c): return (c[0] / 255.0, c[1] / 255.0, c[2] / 255.0)

# Anthropic-style sans. Noto Sans CJK KR mirrors the web's Noto Sans KR and
# carries both Latin and Korean glyphs.
FONT = "Noto Sans CJK KR"

# ---------- ivory matte background (PIL -> cairo surface) ----------
def make_background_surface(scale=2):
    w, h = int(W * scale), int(H * scale)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = w * 0.5, h * 0.30
    d = np.sqrt(((xx - cx) / (w * 0.6)) ** 2 + ((yy - cy) / (h * 0.6)) ** 2)
    t = np.clip(d, 0, 1)

    light = np.array(IVORY_LIGHT, np.float32)
    base  = np.array(IVORY_BASE,  np.float32)
    deep  = np.array(IVORY_DEEP,  np.float32)
    a = np.clip(t / 0.45, 0, 1)[..., None]
    b = np.clip((t - 0.45) / 0.55, 0, 1)[..., None]
    grad = light * (1 - a) + base * a
    grad = grad * (1 - b) + deep * b

    rng = np.random.default_rng(7)
    noise = rng.normal(0, 1, (h, w)).astype(np.float32)
    nimg = Image.fromarray(((noise - noise.min()) /
            (np.ptp(noise) + 1e-6) * 255).astype(np.uint8))
    nimg = nimg.filter(ImageFilter.GaussianBlur(0.4))
    noise = np.asarray(nimg, np.float32) / 255.0 - 0.5
    grad += noise[..., None] * 7.0

    img = Image.fromarray(np.clip(grad, 0, 255).astype(np.uint8), "RGB")
    # cairo wants BGRA premultiplied; load via PNG bytes for simplicity
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return cairo.ImageSurface.create_from_png(buf)

BG = None  # built in main()

# ---------- text helpers (cairo toy API, top-left origin, y down) ----------
def set_font(c, size, bold=False):
    c.select_font_face(FONT, cairo.FONT_SLANT_NORMAL,
                       cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    c.set_font_size(size)

def text_w(c, s):
    return c.text_extents(s).x_advance

def wrap(c, text, max_w):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = wd if not cur else cur + " " + wd
        if text_w(c, trial) <= max_w:
            cur = trial
        else:
            if cur: lines.append(cur)
            cur = wd
    if cur: lines.append(cur)
    return lines

def draw_text(c, s, x, y, color, align="left"):
    """Draw one line; (x,y) is the baseline-left (or centre) point."""
    c.set_source_rgb(*rgb(color))
    if align == "center":
        x -= text_w(c, s) / 2
    c.move_to(x, y)
    c.show_text(s)

def accent_rule(c, x, y, w=64, h=3, center=False):
    c.set_source_rgb(*rgb(ACCENT))
    if center: x -= w / 2
    c.rectangle(x, y, w, h)
    c.fill()

def paint_bg(c):
    c.save()
    sx = W / BG.get_width()
    sy = H / BG.get_height()
    c.scale(sx, sy)
    c.set_source_surface(BG, 0, 0)
    c.paint()
    c.restore()

# ---------- slide renderers ----------
def render_title(c, s):
    paint_bg(c)
    cx = W / 2
    pre, tail = s["pre"], s["tail"]

    # Single line: [pre] [blank] [tail] — auto-fit width to ~90% of the page
    size = 64
    while size > 24:
        set_font(c, size, bold=True)
        blank_w = size * 1.7
        gap = size * 0.30
        total = text_w(c, pre) + gap + blank_w + gap + text_w(c, tail)
        if total <= W * 0.90:
            break
        size -= 2

    set_font(c, size, bold=True)
    y = H * 0.46
    lx = cx - total / 2
    draw_text(c, pre, lx, y, INK, align="left")
    bx = lx + text_w(c, pre) + gap
    c.set_source_rgb(*rgb(ACCENT))
    c.rectangle(bx, y + size * 0.12, blank_w, max(5, size * 0.10))
    c.fill()
    draw_text(c, tail, bx + blank_w + gap, y, INK, align="left")

    # presenter + date
    set_font(c, 26, bold=False)
    py = y + size * 1.5
    label = "발표  "
    name = s.get("presenter", "")
    lw = text_w(c, label); nw = text_w(c, name)
    start = cx - (lw + nw) / 2
    draw_text(c, label, start, py, INK_SOFT, align="left")
    draw_text(c, name, start + lw, py, INK, align="left")

    set_font(c, 19, bold=False)
    draw_text(c, s.get("date", ""), cx, py + 36, ACCENT, align="center")

def render_content(c, s):
    paint_bg(c)
    x = W * 0.10
    accent_rule(c, x, H * 0.26)
    set_font(c, 50, bold=True)
    y = H * 0.40
    for ln in wrap(c, s["title"], W * 0.8):
        draw_text(c, ln, x, y, INK, align="left"); y += 62
    y += 16
    if s.get("body"):
        set_font(c, 23, bold=False)
        for ln in wrap(c, s["body"], W * 0.62):
            draw_text(c, ln, x, y, INK_SOFT, align="left"); y += 38

def load_surface(path):
    """Load any image (png/jpg/webp/...) into a cairo ImageSurface via PIL."""
    img = Image.open(path).convert("RGBA")
    buf = io.BytesIO(); img.save(buf, "PNG"); buf.seek(0)
    return cairo.ImageSurface.create_from_png(buf)

def draw_image_fit(c, path, bx, by, bw, bh, shadow=True):
    img = load_surface(path)
    iw, ih = img.get_width(), img.get_height()
    scale = min(bw / iw, bh / ih)
    w, h = iw * scale, ih * scale
    x = bx + (bw - w) / 2
    y = by + (bh - h) / 2
    if shadow:
        c.set_source_rgba(0, 0, 0, 0.10)
        c.rectangle(x + 6, y + 8, w, h)
        c.fill()
    c.save()
    c.translate(x, y)
    c.scale(scale, scale)
    c.set_source_surface(img, 0, 0)
    c.paint()
    c.restore()

def render_bullets(c, s):
    paint_bg(c)
    bullets = s["bullets"]
    has_img = bool(s.get("image"))
    x = W * 0.09
    size = 34 if has_img else 40
    line_h = size * 1.75
    block_h = line_h * len(bullets)
    y = (H - block_h) / 2 + size

    for b in bullets:
        c.set_source_rgb(*rgb(ACCENT))
        c.rectangle(x, y - size * 0.30, size * 0.32, size * 0.32)
        c.fill()
        set_font(c, size, bold=False)
        draw_text(c, b, x + size * 0.85, y, INK, align="left")
        y += line_h

    if has_img:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), s["image"])
        draw_image_fit(c, path, W * 0.46, H * 0.16, W * 0.48, H * 0.68)

import glob, math, json

# Justified gallery: 3 rows, each row scaled to fill the full width (Google-
# Photos style). Maximises image size while staying non-overlapping. A tiny
# per-image tilt + gaps keep the scrapbook feel without collisions.
CELL_PAD = 6              # white frame padding
ROWS = [3, 3, 3]         # images per row
GAP = 26
MARGIN_X, MARGIN_Y = 26, 24
ROT_SEQ = [-2, 1.5, -1.5,  2, -1.5, 1.5,  -1.5, 2, -1.5]

def compute_scatter(files):
    metas = []
    for p in files:
        with Image.open(p) as im:
            metas.append((p, im.size[0], im.size[1]))
    rows, k = [], 0
    for n in ROWS:
        rows.append(metas[k:k+n]); k += n
    avail_w = W - 2*MARGIN_X
    # width-justify each row -> row height
    row_h = []
    for row in rows:
        sum_aspect = sum(iw/ih for _, iw, ih in row)
        rw = avail_w - GAP*(len(row)-1)
        row_h.append(rw / sum_aspect)
    # fit vertically
    avail_h = H - 2*MARGIN_Y - GAP*(len(rows)-1)
    if sum(row_h) > avail_h:
        f = avail_h / sum(row_h)
        row_h = [h*f for h in row_h]
    cards, idx, y = [], 0, MARGIN_Y
    for r, row in enumerate(rows):
        hr = row_h[r]
        widths = [hr*(iw/ih) for _, iw, ih in row]
        total = sum(widths) + GAP*(len(row)-1)
        x = MARGIN_X + (avail_w - total)/2
        for (p, iw, ih), wd in zip(row, widths):
            cards.append({"cx": x + wd/2, "cy": y + hr/2, "w": wd, "h": hr,
                          "rot": ROT_SEQ[idx], "src": os.path.basename(p)})
            x += wd + GAP; idx += 1
        y += hr + GAP
    return cards

def render_scatter(c, s):
    paint_bg(c)
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), s["folder"])
    files = sorted(glob.glob(os.path.join(folder, "*.png")))
    for card, path in zip(compute_scatter(files), files):
        img = load_surface(path)
        iw, ih = img.get_width(), img.get_height()
        w, h, pad = card["w"], card["h"], CELL_PAD
        c.save()
        c.translate(card["cx"], card["cy"])
        c.rotate(math.radians(card["rot"]))
        c.set_source_rgba(0, 0, 0, 0.18)
        c.rectangle(-w/2 + 5, -h/2 + 7, w, h); c.fill()
        c.set_source_rgb(1, 1, 1)
        c.rectangle(-w/2 - pad, -h/2 - pad, w + 2*pad, h + 2*pad); c.fill()
        c.save()
        c.translate(-w/2, -h/2); c.scale(w/iw, h/ih)
        c.set_source_surface(img, 0, 0); c.paint()
        c.restore()
        c.set_source_rgba(0, 0, 0, 0.12); c.set_line_width(1)
        c.rectangle(-w/2 - pad, -h/2 - pad, w + 2*pad, h + 2*pad); c.stroke()
        c.restore()

def _seg_widths(c, segs, blank_w):
    ws = []
    for txt, _col, kind in segs:
        ws.append(blank_w if kind == "blank" else text_w(c, txt))
    return ws

def draw_statement(c, cx, y, segs, size, blank_w, gap_factor=0.18):
    """Draw a centred line of coloured segments; 'blank' draws a clay underline."""
    set_font(c, size, bold=True)
    ws = _seg_widths(c, segs, blank_w)
    gap = size * gap_factor
    total = sum(ws) + gap * (len(segs) - 1)
    x = cx - total / 2
    for (txt, col, kind), w in zip(segs, ws):
        if kind == "blank":
            c.set_source_rgb(*rgb(ACCENT))
            c.rectangle(x, y + size * 0.12, w, max(5, size * 0.10)); c.fill()
        else:
            c.set_source_rgb(*rgb(col))
            c.move_to(x, y); c.show_text(txt)
        x += w + gap

def _fit_statement_size(c, segs, blank_factor, gap_factor=0.18, start=64, min_size=24):
    size = start
    while size > min_size:
        set_font(c, size, bold=True)
        blank_w = size * blank_factor
        ws = _seg_widths(c, segs, blank_w)
        gap = size * gap_factor
        if sum(ws) + gap * (len(segs) - 1) <= W * 0.90:
            return size, blank_w
        size -= 2
    return size, size * blank_factor

def render_center_blank(c, s):
    paint_bg(c)
    segs = [(s["pre"], INK, "text"), ("", None, "blank"), (s["tail"], INK, "text")]
    size, blank_w = _fit_statement_size(c, segs, blank_factor=1.7)
    draw_statement(c, W / 2, H * 0.54, segs, size, blank_w)

def render_center_images(c, s):
    paint_bg(c)
    # trailing space in pre gives the gap before the answer; key+tail stay joined
    segs = [(s["pre"] + " ", INK, "text"), (s["key"], ACCENT, "text"),
            (s["tail"], INK, "text")]
    size, _ = _fit_statement_size(c, segs, blank_factor=0, gap_factor=0)
    draw_statement(c, W / 2, H * 0.22, segs, size, 0, gap_factor=0)
    # two images below, side by side
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), s["folder"])
    imgs = sorted(glob.glob(os.path.join(folder, "*")))
    imgs = [p for p in imgs if p.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
    gap = W * 0.04
    box_w = (W * 0.86 - gap) / 2
    x0 = (W - (box_w * 2 + gap)) / 2
    by, bh = H * 0.34, H * 0.56
    for i, p in enumerate(imgs[:2]):
        draw_image_fit(c, p, x0 + i * (box_w + gap), by, box_w, bh)

def render_center_text(c, s):
    paint_bg(c)
    color = {"ink": INK, "clay": ACCENT, "soft": INK_SOFT}.get(s.get("color", "ink"), INK)
    size = s.get("size")
    if size is None:
        size = 66
        while size > 20:
            set_font(c, size, bold=True)
            if text_w(c, s["text"]) <= W * 0.9:
                break
            size -= 2
    set_font(c, size, bold=True)
    draw_text(c, s["text"], W / 2, H * 0.57, color, align="center")

def render_equation(c, s):
    paint_bg(c)
    hl = s.get("highlight", "both")
    mcol = ACCENT if hl in ("model", "both") else INK
    hcol = ACCENT if hl in ("harness", "both") else INK
    segs = [("Agent = ", INK, "text"), ("Model", mcol, "text"),
            (" + ", INK, "text"), ("Harness", hcol, "text")]
    size, _ = _fit_statement_size(c, segs, blank_factor=0, gap_factor=0)
    bottom = s.get("bottom")
    ey = H * 0.44 if bottom else H * 0.56
    draw_statement(c, W / 2, ey, segs, size, 0, gap_factor=0)
    if bottom:
        bsize = 50
        while bsize > 22:
            set_font(c, bsize, bold=True)
            if text_w(c, bottom) <= W * 0.86:
                break
            bsize -= 2
        set_font(c, bsize, bold=True)
        draw_text(c, bottom, W / 2, H * 0.64, INK, align="center")

def render_center_paragraph(c, s):
    paint_bg(c)
    text = s["text"]
    size = s.get("size", 52)
    maxw = W * 0.82
    set_font(c, size, bold=True)
    lines = wrap(c, text, maxw)
    while len(lines) > 3 and size > 28:
        size -= 3
        set_font(c, size, bold=True)
        lines = wrap(c, text, maxw)
    line_h = size * 1.45
    y = H / 2 - (len(lines) - 1) * line_h / 2 + size * 0.35
    for ln in lines:
        draw_text(c, ln, W / 2, y, INK, align="center")
        y += line_h

def render_single_image(c, s):
    paint_bg(c)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), s["path"])
    draw_image_fit(c, path, W * 0.04, H * 0.05, W * 0.92, H * 0.90)

def render_qa(c, s):
    paint_bg(c)
    lx = W * 0.27           # centre of left text column
    set_font(c, s.get("title_size", 112), bold=True)
    draw_text(c, s["title"], lx, H * 0.49, INK, align="center")
    if s.get("subtitle"):
        set_font(c, 30, bold=True)
        draw_text(c, s["subtitle"], lx, H * 0.61, ACCENT, align="center")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), s["path"])
    draw_image_fit(c, path, W * 0.52, H * 0.10, W * 0.42, H * 0.80)

def render_image_bullets(c, s):
    paint_bg(c)
    # left: image
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), s["path"])
    draw_image_fit(c, path, W * 0.04, H * 0.13, W * 0.46, H * 0.74, shadow=True)
    # right: bullet list (two marker styles)
    items = s["bullets"]
    rx = W * 0.555
    maxw = W * 0.40
    size = s.get("size", 23)
    while size > 14:
        set_font(c, size, bold=False)
        line_h = size * 1.32
        gap = size * 0.62
        blocks = []
        for kind, txt in items:
            indent = size * 1.1 if kind == "dash" else size * 1.1
            blocks.append(wrap(c, txt, maxw - indent))
        total = sum(len(b) * line_h for b in blocks) + gap * (len(items) - 1)
        if total <= H * 0.82:
            break
        size -= 1
    y = (H - total) / 2 + size
    for (kind, txt), lines in zip(items, blocks):
        my = y - size * 0.32
        if kind == "star":
            c.set_source_rgb(*rgb(ACCENT))
            c.rectangle(rx, my, size * 0.34, size * 0.34); c.fill()
            tx = rx + size * 1.1
        else:  # dash sub-item
            c.set_source_rgba(*rgb(ACCENT), 0.65)
            c.rectangle(rx + size * 0.9, my + size * 0.12, size * 0.42, size * 0.10); c.fill()
            tx = rx + size * 1.1 + size * 0.9
        col = INK if kind == "star" else INK_SOFT
        set_font(c, size, bold=False)
        for ln in lines:
            draw_text(c, ln, tx, y, col, align="left")
            y += line_h
        y += gap

def render_caption_image(c, s):
    paint_bg(c)
    size = s.get("size", 60)
    set_font(c, size, bold=True)
    draw_text(c, s["text"], W / 2, H * 0.24, INK, align="center")
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), s["path"])
    draw_image_fit(c, path, W * 0.18, H * 0.34, W * 0.64, H * 0.54, shadow=False)

def render_gif_grid(c, s):
    paint_bg(c)
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), s["folder"])
    stills = sorted(glob.glob(os.path.join(folder, "*_still.png")))
    pw, ph, gx, gy = 366, 183, 30, 42
    top_y = (H - (ph*2 + gy)) / 2
    row1_x = (W - (pw*3 + gx*2)) / 2
    row2_x = (W - (pw*2 + gx)) / 2
    coords = [(row1_x + i*(pw+gx), top_y) for i in range(3)]
    coords += [(row2_x + i*(pw+gx), top_y + ph + gy) for i in range(2)]
    for (x, y), p in zip(coords, stills):
        draw_image_fit(c, p, x, y, pw, ph, shadow=False)

_COLORS = {"ink": INK, "clay": ACCENT, "soft": INK_SOFT}

def render_two_lines(c, s):
    paint_bg(c)
    cx = W / 2
    tcol = _COLORS.get(s.get("top_color", "ink"), INK)
    bcol = _COLORS.get(s.get("bottom_color", "ink"), INK)
    tsize = s.get("top_size", 66)
    bsize = s.get("bottom_size", 66)
    ty = s.get("top_y", 0.46)
    by = s.get("bottom_y", 0.61)
    top, hl = s["top"], s.get("top_highlight")
    if hl and hl in top:
        pre, post = top.split(hl, 1)
        segs = [(pre, tcol, "text"), (hl, ACCENT, "text"), (post, tcol, "text")]
        draw_statement(c, cx, ty * H, segs, tsize, 0, gap_factor=0)
    else:
        set_font(c, tsize, bold=True)
        draw_text(c, top, cx, ty * H, tcol, align="center")
    set_font(c, bsize, bold=True)
    draw_text(c, s["bottom"], cx, by * H, bcol, align="center")

def render_two_images(c, s):
    paint_bg(c)
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), s["folder"])
    left  = sorted(glob.glob(os.path.join(folder, "left_*")))[0]
    right = sorted(glob.glob(os.path.join(folder, "right_*")))[0]
    box_w = W * 0.40
    box_h = H * 0.66
    gap = W * 0.04
    total = box_w * 2 + gap
    x0 = (W - total) / 2
    by = (H - box_h) / 2
    draw_image_fit(c, left,  x0, by, box_w, box_h)
    draw_image_fit(c, right, x0 + box_w + gap, by, box_w, box_h)

RENDERERS = {"title": render_title, "content": render_content,
             "bullets": render_bullets, "scatter": render_scatter,
             "two_images": render_two_images,
             "center_blank": render_center_blank,
             "center_images": render_center_images,
             "two_lines": render_two_lines,
             "gif_grid": render_gif_grid,
             "center_text": render_center_text,
             "equation": render_equation,
             "single_image": render_single_image,
             "paragraph": render_center_paragraph,
             "caption_image": render_caption_image,
             "qa": render_qa,
             "image_bullets": render_image_bullets}

# ---------- slide deck (mirror of index.html) ----------
SLIDES = [
    {"type": "title",
     "pre": "AI 툴 중에 가장 좋은건",
     "tail": "이다",
     "presenter": "슬램슬램",
     "date": "2026.06.21"},
    {"type": "bullets",
     "bullets": [
        "로컬 LLM",
        "피지컬 AI",
        "AI 반도체",
        "로보틱스 & SLAM",
        "컴퓨터 비전 AI",
     ],
     "image": "slide2/right_profile.png"},
    {"type": "scatter",
     "folder": "slide3"},
    {"type": "two_images",
     "folder": "slide4"},
    {"type": "center_blank",
     "pre": "AI 툴 중에 가장 좋은건", "tail": "이다"},
    {"type": "center_images",
     "pre": "AI 툴 중에 가장 좋은건", "key": "딥리서치", "tail": "다",
     "folder": "slide6"},
    {"type": "two_lines",
     "top": "Agentic AI", "bottom": "하네스 엔지니어링"},
    {"type": "gif_grid",
     "folder": "slide8"},
    {"type": "center_text", "text": "6x", "size": 220, "color": "clay"},
    {"type": "equation"},
    {"type": "center_text", "text": "피지컬 AI가 아직 어려운 이유"},
    {"type": "single_image", "path": "slide 12/slide12_still.png"},
    {"type": "center_text", "text": "진짜 문제는 무엇인가?"},
    {"type": "equation", "highlight": "model",
     "bottom": "방법 1: 내가 더 좋은 모델이 된다"},
    {"type": "paragraph", "text": "문제: 내가 더 똑똑해져야함. 학습 필요"},
    {"type": "equation", "highlight": "harness",
     "bottom": "방법 2: 내가 더 좋은 하네스가 된다"},
    {"type": "paragraph",
     "text": "문제: 내가 풀려고 하는 문제를 정확히 알아야함. "
             "어떤 툴과 워크플로우를 써야하는지 알아야함"},
    {"type": "caption_image", "text": "어떤 방법을 써야하는가?",
     "path": "slide18/loop_still.png"},
    {"type": "two_lines", "top": "그래서, 딥리서치", "top_highlight": "딥리서치",
     "bottom": "[Curiosity]", "bottom_color": "clay",
     "top_size": 64, "bottom_size": 44, "top_y": 0.48, "bottom_y": 0.61},
    {"type": "image_bullets", "path": "slide 20/slide20_still.png",
     "bullets": [
        ("star", "HBM vs GDDR vs LPDDR"),
        ("star", "PCIe vs UCIe vs BoW"),
        ("dash", "Mac Mini의 메모리 구조와 LLM 추론 성능 한계 분석"),
        ("dash", "DGX SPARK vs Apple Mac 메모리 아키텍처 비교"),
        ("star", "NVIDIA vs AMD GPU 아키텍처"),
        ("star", "Groq의 SRAM 기반 아키텍처가 NVIDIA 보다 10배 빠른 이유"),
        ("star", "퓨리오사 & 리벨리온 NPU 아키텍처"),
        ("star", "vLLM vs SGLang - 서빙 방식 및 attention 구현체의 복잡도 분석"),
        ("star", "Systolic array 기반의 dense transformer 연산 방법론 분석"),
        ("dash", "FPGA 공부 로드맵"),
     ]},
    {"type": "qa", "title": "Q&A", "subtitle": "감사합니다 · 슬램슬램",
     "title_size": 96,
     "path": "slide 21/726294972_17971381512115292_8465929942780449733_n.jpg"},
]

def main():
    global BG
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "dump-scatter":
        folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slide3")
        files = sorted(glob.glob(os.path.join(folder, "*.png")))
        print(json.dumps(compute_scatter(files)))
        return
    BG = make_background_surface()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "threads-seminar.pdf")
    surface = cairo.PDFSurface(out, W, H)
    c = cairo.Context(surface)
    for s in SLIDES:
        RENDERERS[s["type"]](c, s)
        c.show_page()
    surface.finish()
    print("wrote", out, f"({len(SLIDES)} slides)")

if __name__ == "__main__":
    main()
