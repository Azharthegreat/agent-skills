# -*- coding: utf-8 -*-
"""
make_scenes.py - render 1080x1920 promo-video scene frames from a JSON spec.

Usage:
    python make_scenes.py <spec.json> <assets_dir> <out_dir>

Each scene in spec["scenes"] becomes s1.png, s2.png, ... in <out_dir>.
Supported scene "type": hook | screenshot | card | statement | cta
See examples/video_spec.example.json for the full shape.

Design rules (proven, do not quietly change):
- Vertical 1080x1920. Brand blue gradient for hook/statement/cta, light gradient for card/screenshot.
- Card scenes must show the WHOLE card (never crop out a data field).
- No em dashes anywhere. Use "-" or split into sentences.
- CTA always carries the honest disclosure lines from the spec.
"""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont, ImageFilter

spec_path, ASSETS, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
spec = json.load(open(spec_path, encoding="utf-8"))
os.makedirs(OUT, exist_ok=True)
W, H = 1080, 1920

FONTS = spec.get("fonts", {"black": "ariblk.ttf", "bold": "arialbd.ttf", "regular": "arial.ttf"})
# Resolve fonts: absolute path as-is, else look in C:/Windows/Fonts (and common Linux dirs).
FONT_DIRS = ["", r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu", "/Library/Fonts"]
def _find_font(name):
    for d in FONT_DIRS:
        p = name if d == "" else os.path.join(d, name)
        if os.path.isfile(p):
            return p
    return name  # let PIL raise if truly missing
FB = _find_font(FONTS["bold"]); FBLK = _find_font(FONTS["black"]); FR = _find_font(FONTS["regular"])
def f(path, s): return ImageFont.truetype(path, s)

B = spec.get("brand", {})
BLUE_T = tuple(B.get("blue_top", [8, 46, 86]))
BLUE_B = tuple(B.get("blue_bot", [16, 86, 150]))
ACCENT = tuple(B.get("accent", [14, 99, 176]))
DARK = tuple(B.get("dark", [22, 32, 43]))
GREY = tuple(B.get("grey", [120, 132, 146]))
LIGHT_T = tuple(B.get("light_top", [235, 241, 249]))
LIGHT_B = tuple(B.get("light_bot", [252, 253, 255]))

def vgrad(top, bot):
    img = Image.new("RGB", (W, H), top); d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bot[i]-top[i])*t) for i in range(3)))
    return img

def ctext(d, y, text, font, fill, ls=0):
    if ls == 0:
        w = d.textlength(text, font=font); d.text(((W-w)/2, y), text, font=font, fill=fill); return
    total = sum(d.textlength(ch, font=font)+ls for ch in text) - ls; x = (W-total)/2
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill); x += d.textlength(ch, font=font)+ls

def rounded(img, radius):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, img.size[0], img.size[1]], radius=radius, fill=255)
    out = img.convert("RGBA"); out.putalpha(m); return out

def shadow_paste(base, card, cx, cy, radius=34):
    cw, ch = card.size
    sh = Image.new("RGBA", (cw+80, ch+80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([40, 46, 40+cw, 46+ch], radius=radius, fill=(10, 30, 60, 90))
    sh = sh.filter(ImageFilter.GaussianBlur(22)); base.paste(sh, (cx-40, cy-46), sh)

def ap(p):  # resolve an asset path relative to ASSETS unless already absolute
    return p if os.path.isabs(p) else os.path.join(ASSETS, p)

def render_hook(s):
    img = vgrad(BLUE_T, BLUE_B); d = ImageDraw.Draw(img)
    if s.get("kicker"): ctext(d, 150, s["kicker"].upper(), f(FB, 34), (150, 195, 235), ls=14)
    cx, cy, r = W//2, 560, 150
    d.ellipse([cx-r-16, cy-r-16, cx+r+16, cy+r+16], outline=(90, 150, 210), width=4)
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(235, 242, 250))
    qf = f(FBLK, 180); qw = d.textlength(s.get("circle_text", "?"), font=qf)
    d.text((cx-qw/2, cy-135), s.get("circle_text", "?"), font=qf, fill=(14, 86, 150))
    if s.get("label"): ctext(d, 760, s["label"], f(FB, 58), (255, 255, 255))
    if s.get("sublabel"): ctext(d, 840, s["sublabel"], f(FR, 46), (170, 205, 240))
    ctext(d, 1040, s["title"], f(FBLK, 112), (255, 255, 255))
    for i, l in enumerate(s.get("sub", [])): ctext(d, 1240+i*64, l, f(FR, 48), (200, 220, 240))
    return img

def render_screenshot(s):
    img = vgrad(LIGHT_T, LIGHT_B); d = ImageDraw.Draw(img)
    if s.get("kicker"): ctext(d, 140, s["kicker"].upper(), f(FB, 36), ACCENT, ls=10)
    if s.get("title"): ctext(d, 210, s["title"], f(FBLK, 70), DARK)
    im = Image.open(ap(s["image"])).convert("RGB")
    hw = s.get("width", 860); hh = int(im.height*hw/im.width); im = rounded(im.resize((hw, hh)), 28)
    hx = (W-hw)//2; hy = s.get("y", 360); shadow_paste(img, im.convert("RGB"), hx, hy); img.paste(im, (hx, hy), im)
    return img

def render_card(s):
    img = vgrad(LIGHT_T, LIGHT_B); d = ImageDraw.Draw(img)
    if s.get("caption"): ctext(d, 120, s["caption"].upper(), f(FB, 40), ACCENT)
    im = Image.open(ap(s["image"])).convert("RGB")
    cw = s.get("width", 946); ch = int(im.height*cw/im.width); im = rounded(im.resize((cw, ch)), 30)
    cx = (W-cw)//2; cy = s.get("y", 240); shadow_paste(img, im.convert("RGB"), cx, cy); img.paste(im, (cx, cy), im)
    if s.get("brand"): ctext(d, 1500, s["brand"], f(FB, 42), (90, 105, 120))
    if s.get("brand_sub"): ctext(d, 1570, s["brand_sub"], f(FR, 38), GREY)
    return img

def render_statement(s):
    img = vgrad(BLUE_T, BLUE_B); d = ImageDraw.Draw(img)
    if s.get("lead"): ctext(d, 430, s["lead"], f(FR, 52), (190, 215, 238))
    y = 560
    for l in s.get("lines", []): ctext(d, y, l, f(FBLK, 96), (255, 255, 255)); y += 150
    if s.get("tail"): ctext(d, max(y+40, 1250), s["tail"], f(FB, 56), (150, 195, 235))
    return img

def render_cta(s):
    img = vgrad((10, 60, 108), (8, 40, 78)); d = ImageDraw.Draw(img)
    icon_path = ap(s.get("icon", spec.get("icon", "icon.png")))
    if os.path.isfile(icon_path):
        iw = 300; icon = rounded(Image.open(icon_path).convert("RGBA").resize((iw, iw)), 60)
        img.paste(icon, ((W-iw)//2, 430), icon)
    ctext(d, 790, s["title"], f(FBLK, 96), (255, 255, 255))
    if s.get("subtitle"): ctext(d, 910, s["subtitle"], f(FB, 50), (170, 205, 240))
    bw, bh, by = 640, 128, 1120; bx = (W-bw)//2
    d.rounded_rectangle([bx, by, bx+bw, by+bh], radius=64, fill=(255, 255, 255))
    ctext(d, by+36, s.get("button", "Free on Google Play"), f(FB, 52), (12, 66, 116))
    for i, l in enumerate(s.get("notes", [])): ctext(d, 1420+i*52, l, f(FR, 34), (150, 175, 205))
    return img

RENDER = {"hook": render_hook, "screenshot": render_screenshot, "card": render_card,
          "statement": render_statement, "cta": render_cta}

for i, scene in enumerate(spec["scenes"], 1):
    img = RENDER[scene["type"]](scene)
    img.save(os.path.join(OUT, f"s{i}.png"))
print("scenes written:", len(spec["scenes"]))
