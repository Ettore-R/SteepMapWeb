"""
Trim the dark device-frame border off app screenshots.

- Reads originals from media/app/  (never modifies them)
- Writes trimmed copies to media/app/web/
- Only removes near-uniform dark border rows/columns, capped per side so we
  never cut into real content ("do not cut too much").
"""
import os
from PIL import Image

SRC = "media/app"
OUT = "media/app/web"

# Which files to process (screenshots only, not the map_* legends).
FILES = [
    "app_0.png", "app_1.png", "app_3.png", "app_4.png",
    "app_5.png", "app_6.png", "app_7.png",
    "desktop_app_0.png", "desktop_app_1.png",
    "desktop_app_3.png", "desktop_app_4.png",
]

DARK_LUMA = 125     # a pixel is "dark border" below this luma
DARK_SPREAD = 32    # ...and roughly gray (low channel spread)
ROW_FRAC = 0.88     # a line is border if >=88% of its pixels are dark-gray
MAX_TRIM = 0.10     # never trim more than 10% off any single side


def luma(p):
    return 0.299 * p[0] + 0.587 * p[1] + 0.714 * p[2]


def is_border_line(pixels):
    n = len(pixels)
    dark = 0
    for p in pixels:
        if luma(p) < DARK_LUMA and (max(p[:3]) - min(p[:3])) < DARK_SPREAD:
            dark += 1
    return dark / n >= ROW_FRAC


def trim(path_in, path_out):
    im = Image.open(path_in).convert("RGB")
    w, h = im.size
    px = im.load()

    # sample every Nth pixel along a line for speed
    step_x = max(1, w // 400)
    step_y = max(1, h // 400)

    def row(y):
        return [px[x, y] for x in range(0, w, step_x)]

    def col(x):
        return [px[x, y] for y in range(0, h, step_y)]

    top = 0
    while top < int(h * MAX_TRIM) and is_border_line(row(top)):
        top += 1
    bottom = h
    while bottom > h - int(h * MAX_TRIM) and is_border_line(row(bottom - 1)):
        bottom -= 1
    left = 0
    while left < int(w * MAX_TRIM) and is_border_line(col(left)):
        left += 1
    right = w
    while right > w - int(w * MAX_TRIM) and is_border_line(col(right - 1)):
        right -= 1

    cropped = im.crop((left, top, right, bottom))
    cropped.save(path_out, optimize=True)
    return (w, h), cropped.size, (left, top, w - right, h - bottom)


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in FILES:
        src = os.path.join(SRC, f)
        if not os.path.exists(src):
            print(f"  skip (missing): {f}")
            continue
        before, after, trimmed = trim(src, os.path.join(OUT, f))
        print(f"{f:20} {before[0]}x{before[1]} -> {after[0]}x{after[1]}  "
              f"trimmed L{trimmed[0]} T{trimmed[1]} R{trimmed[2]} B{trimmed[3]}")


if __name__ == "__main__":
    main()
