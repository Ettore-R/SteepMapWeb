#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Share-image maker (ETT-11).

Builds one 1200x630 social card per featured tour (the size Google, Facebook and
X/Twitter expect for large previews): the tour's first photo, cropped, with a dark
gradient and the tour name, region and grade on top. Output: media/og/<slug>.jpg

Run from the repo root:  python scripts/make_share_images.py
Needs Pillow (pip install pillow) and an internet connection (it downloads the photos).
"""
import json, os, sys, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1200, 630
FONT_BOLD = r"C:\Windows\Fonts\arialbd.ttf"
FONT_REG = r"C:\Windows\Fonts\arial.ttf"
GRADE_LABEL = {"Easy": "Easy", "Medium": "Medium", "Hard": "Hard", "Very Hard": "Very Hard"}


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "steep-share-images/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return Image.open(r).convert("RGB")


def cover(img):
    """Crop to the card's aspect ratio, centred, then resize."""
    scale = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def card(tour):
    photo = fetch(tour["photos"][0]) if tour.get("photos") else Image.new("RGB", (W, H), (10, 20, 32))
    img = cover(photo)

    # dark gradient from the bottom, so the text is always readable
    shade = Image.new("L", (1, H))
    for y in range(H):
        t = y / H
        shade.putpixel((0, y), int(255 * max(0.0, (t - 0.35) / 0.65) * 0.88))
    shade = shade.resize((W, H))
    img = Image.composite(Image.new("RGB", (W, H), (5, 12, 22)), img, shade)

    draw = ImageDraw.Draw(img)
    title = tour.get("title_i18n", {}).get("en") or tour["title"]
    region = tour.get("region") or ""
    grade = GRADE_LABEL.get(tour["stats"]["grade"], tour["stats"]["grade"])
    stats = f'{tour["stats"]["distance_km"]} km  ·  {tour["stats"]["elev_gain_m"]} m ascent  ·  {grade}'

    # wordmark top-left
    draw.text((64, 52), "STEEP", font=font(FONT_BOLD, 40), fill=(255, 255, 255))
    draw.text((64 + 128, 62), "map", font=font(FONT_REG, 30), fill=(200, 210, 225))

    # title, sized to fit on up to two lines
    size = 84
    while size > 40:
        f = font(FONT_BOLD, size)
        words, lines, line = title.split(), [], ""
        for w in words:
            trial = (line + " " + w).strip()
            if draw.textlength(trial, font=f) <= W - 128:
                line = trial
            else:
                lines.append(line)
                line = w
        lines.append(line)
        if len(lines) <= 2:
            break
        size -= 6
    y = H - 210 - (len(lines) - 1) * size
    for ln in lines:
        draw.text((64, y), ln, font=f, fill=(255, 255, 255))
        y += size + 6

    if region:
        draw.text((64, H - 118), region, font=font(FONT_REG, 36), fill=(214, 226, 240))
    draw.text((64, H - 66), stats, font=font(FONT_BOLD, 32), fill=(255, 138, 76))
    return img


def main():
    manifest = json.load(open(os.path.join(ROOT, "data", "featured", "manifest.json"), encoding="utf-8"))
    out_dir = os.path.join(ROOT, "media", "og")
    os.makedirs(out_dir, exist_ok=True)
    for e in manifest["tours"]:
        tour = json.load(open(os.path.join(ROOT, "data", "featured", f"{e['slug']}.json"), encoding="utf-8"))
        tour["region"] = e["region"]
        try:
            img = card(tour)
        except Exception as err:  # keep going if one photo is unreachable
            print(f"  {e['slug']}: failed ({err})", file=sys.stderr)
            continue
        out = os.path.join(out_dir, f"{e['slug']}.jpg")
        img.save(out, "JPEG", quality=88, optimize=True, progressive=True)
        print(f"  {e['slug']}: {W}x{H} -> media/og/{e['slug']}.jpg")


if __name__ == "__main__":
    main()
