#!/usr/bin/env python3
"""One contact sheet of a whole reference set: every image at its own ratio, never cropped.

  contact_sheet.py OUT.jpg PATH [PATH ...] [--max 80] [--width 2400] [--row 240] [--box NAME ...]

PATHs are image files or folders (searched one level for jpg/png/webp). If there are more than --max
images they are sampled evenly across the whole set, never just the first ones. Each tile is labelled
with its folder and file name so a reading can point at it. --box outlines tiles whose label contains
NAME (use it to mark our own work among the references).
"""
import argparse, pathlib
from PIL import Image, ImageDraw, ImageFont

EXTS = {'.jpg', '.jpeg', '.png', '.webp'}


def collect(paths):
    out = []
    for p in map(pathlib.Path, paths):
        if p.is_dir():
            out += sorted(f for f in p.rglob('*') if f.suffix.lower() in EXTS and not f.name.startswith('_'))
        elif p.suffix.lower() in EXTS:
            out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out'); ap.add_argument('paths', nargs='+')
    ap.add_argument('--max', type=int, default=80); ap.add_argument('--width', type=int, default=2400)
    ap.add_argument('--row', type=int, default=240); ap.add_argument('--box', nargs='*', default=[])
    a = ap.parse_args()
    files = collect(a.paths)
    if not files:
        raise SystemExit('no images found')
    if len(files) > a.max:  # even sample across the whole set
        step = len(files) / a.max
        files = [files[int(i * step)] for i in range(a.max)]
    ims = []
    for f in files:
        try:
            im = Image.open(f); im.thumbnail((1200, 1200)); ims.append((f, im.convert('RGB')))
        except Exception:
            pass
    gap, label_h, W = 8, 22, a.width
    rows, row = [], []
    for f, im in ims:  # justified rows: fill each row to the sheet width at a shared height
        row.append((f, im))
        ratio_sum = sum(i.width / i.height for _, i in row)
        if ratio_sum * a.row + gap * (len(row) - 1) >= W:
            rows.append(row); row = []
    if row:
        rows.append(row)
    layout, y = [], gap
    for r in rows:
        ratio_sum = sum(i.width / i.height for _, i in r)
        h = (W - gap * (len(r) + 1)) / ratio_sum
        if r is rows[-1] and h > a.row * 1.4:
            h = a.row  # don't blow up a short last row
        x = gap
        for f, im in r:
            w = im.width / im.height * h
            layout.append((f, im, int(x), int(y), int(w), int(h))); x += w + gap
        y += h + label_h + gap
    sheet = Image.new('RGB', (W, int(y)), (245, 245, 243))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 13)
    except Exception:
        font = ImageFont.load_default()
    for f, im, x, y0, w, h in layout:
        sheet.paste(im.resize((max(1, w), max(1, h))), (x, y0))
        label = f'{f.parent.name}/{f.stem}'
        shown = label
        while shown and d.textlength(shown, font=font) > w:  # keep each label inside its own tile
            shown = shown[1:]
        d.text((x, y0 + h + 4), shown if shown == label else '…' + shown[1:], fill=(60, 60, 60), font=font)
        if any(b in label for b in a.box):
            d.rectangle([x - 4, y0 - 4, x + w + 4, y0 + h + 4], outline=(220, 30, 90), width=5)
    sheet.save(a.out, quality=85)
    print(f'{len(layout)} images on {a.out} ({W}x{int(y)})')


if __name__ == '__main__':
    main()
