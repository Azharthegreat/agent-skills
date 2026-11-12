# -*- coding: utf-8 -*-
"""
make_thumbnail.py - build a custom thumbnail for the promo (REQUIRED: always upload a custom
thumbnail, never let the platform auto-pick a frame).

Usage:
    python make_thumbnail.py <spec.json> <assets_dir> <out_dir>

Reads spec["thumbnail"]:
    { "headline": "WHO'S CALLING?", "sub": "Caller ID for any number",
      "badge": "FREE", "card_image": "card1.png", "icon": "icon.png" }

Writes two files:
    thumb_16x9.png  (1280x720)  - YouTube custom thumbnail
    thumb_9x16.png  (1080x1920) - cover/poster for vertical platforms

No em dashes. Keep the headline to 2-4 big words so it reads on a small tile.
"""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont, ImageFilter

spec = json.load(open(sys.argv[1], encoding="utf-8"))
ASSETS, OUT = sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
T = spec.get("thumbnail", {})
FONTS = spec.get("fonts", {"black": "ariblk.ttf", "bold": "arialbd.ttf", "regular": "arial.ttf"})
FDIRS = ["", r"C:\Windows\Fonts", "/usr/share/fonts/truetype/dejavu", "/Library/Fonts"]
def _ff(n):
    for d in FDIRS:
        p = n if d == "" else os.path.join(d, n)
        if os.path.isfile(p): return p
    return n
FBLK, FB = _ff(FONTS["black"]), _ff(FONTS["bold"])
def f(p, s): return ImageFont.truetype(p, s)
def ap(p): return p if os.path.isabs(p) else os.path.join(ASSETS, p)
B = spec.get("brand", {})
BT, BB = tuple(B.get("blue_top", [8, 46, 86])), tuple(B.get("blue_bot", [16, 86, 150]))

def grad(w, h, top, bot):
    img = Image.new("RGB", (w, h), top); d = ImageDraw.Draw(img)
    for y in range(h):
        t = y/(h-1); d.line([(0, y), (w, y)], fill=tuple(int(top[i]+(bot[i]-top[i])*t) for i in range(3)))
    return img

def rounded(im, r):
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, *im.size], radius=r, fill=255)
    o = im.convert("RGBA"); o.putalpha(m); return o

def wrap_words(words, per_line=2):
    return [" ".join(words[i:i+per_line]) for i in range(0, len(words), per_line)]

def compose(w, h, card_w, headline_size):
    img = grad(w, h, BT, BB); d = ImageDraw.Draw(img)
    # card preview on the right / lower
    if T.get("card_image") and os.path.isfile(ap(T["card_image"])):
        c = Image.open(ap(T["card_image"])).convert("RGB")
        cw = card_w; ch = int(c.height*cw/c.width); c = rounded(c.resize((cw, ch)), 26)
        if w > h:  # landscape: card on right
            cx, cy = w-cw-60, (h-ch)//2
        else:       # portrait: card lower, under the headline block
            cx, cy = (w-cw)//2, int(h*0.30)
        sh = Image.new("RGBA", (cw+60, ch+60), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([30, 36, 30+cw, 36+ch], radius=26, fill=(0, 0, 0, 110))
        sh = sh.filter(ImageFilter.GaussianBlur(18)); img.paste(sh, (cx-30, cy-36), sh)
        img.paste(c, (cx, cy), c)
    # headline (top-left for landscape, top-center for portrait). Shrink to fit: a longer headline
    # than "WHO'S CALLING?" ran off the canvas and under the card at a fixed size.
    lines = wrap_words(T.get("headline", "WHO'S CALLING").split(), 2 if w > h else 2)
    max_w = (w - card_w - 60 - 70 - 40) if (w > h and T.get("card_image")) else (w - 140)
    widest = max(d.textlength(ln, font=f(FBLK, headline_size)) for ln in lines)
    if widest > max_w:
        headline_size = max(40, int(headline_size * max_w / widest))
    y = 80 if w > h else 90
    for ln in lines:
        if w > h:
            d.text((70, y), ln, font=f(FBLK, headline_size), fill=(255, 255, 255))
        else:
            tw = d.textlength(ln, font=f(FBLK, headline_size)); d.text(((w-tw)/2, y), ln, font=f(FBLK, headline_size), fill=(255, 255, 255))
        y += int(headline_size*1.05)
    if T.get("sub"):
        sz = int(headline_size*0.33)
        if w > h: d.text((74, y+14), T["sub"], font=f(FB, sz), fill=(175, 210, 240))
        else:
            tw = d.textlength(T["sub"], font=f(FB, sz)); d.text(((w-tw)/2, y+14), T["sub"], font=f(FB, sz), fill=(175, 210, 240))
    # FREE badge
    if T.get("badge"):
        bs = f(FBLK, int(headline_size*0.5)); bw = d.textlength(T["badge"], font=bs)
        pad = 26; bx = w-int(bw)-pad*2-50; by = h-int(headline_size*0.5)-pad*2-50
        d.rounded_rectangle([bx, by, bx+int(bw)+pad*2, by+int(headline_size*0.5)+pad*2], radius=20, fill=(255, 196, 0))
        d.text((bx+pad, by+pad-6), T["badge"], font=bs, fill=(20, 30, 50))
    # app icon bottom-left
    ic = ap(T.get("icon", spec.get("icon", "icon.png")))
    if os.path.isfile(ic):
        iw = int(h*0.14); icon = rounded(Image.open(ic).convert("RGBA").resize((iw, iw)), int(iw*0.22))
        img.paste(icon, (60, h-iw-60), icon)
    return img

compose(1280, 720, 440, 150).save(os.path.join(OUT, "thumb_16x9.png"))
compose(1080, 1920, 940, 150).save(os.path.join(OUT, "thumb_9x16.png"))
print("thumbnails written: thumb_16x9.png, thumb_9x16.png")
