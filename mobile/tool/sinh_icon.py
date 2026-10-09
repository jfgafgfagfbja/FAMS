"""Sinh bo icon + splash cho app FAMS (Android, iOS, web) tu mot dau nhan ve bang code.

Dau nhan: khung quet khuon mat (4 goc) + bong nguoi o giua, mau nen #8E1B2E.
Chay: python tool/sinh_icon.py   (ghi de icon trong android/, ios/, web/)
Can: pip install pillow
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw

BRAND = (142, 27, 46, 255)  # #8E1B2E
WHITE = (255, 255, 255, 255)
SS = 4  # he so ve phong to roi thu nho lai cho min
MOBILE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def draw_mark(size: int, color=WHITE) -> Image.Image:
    """Ve dau nhan (khung 4 goc + bong nguoi) tren anh trong suot canh `size`."""
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # --- khung quet: 4 goc chu L ---
    pad = 0.035 * s
    stroke = max(1, int(round(0.078 * s)))
    arm = 0.27 * s
    r = stroke / 2
    lo, hi = pad + r, s - pad - r
    corners = [
        [(lo, lo + arm), (lo, lo), (lo + arm, lo)],  # tren trai
        [(hi - arm, lo), (hi, lo), (hi, lo + arm)],  # tren phai
        [(hi, hi - arm), (hi, hi), (hi - arm, hi)],  # duoi phai
        [(lo + arm, hi), (lo, hi), (lo, hi - arm)],  # duoi trai
    ]
    for pts in corners:
        d.line(pts, fill=color, width=stroke, joint="curve")
        for x, y in pts:  # dau tron o hai dau moi canh
            d.ellipse((x - r, y - r, x + r, y + r), fill=color)

    # --- bong nguoi: dau tron + vai, ve rieng roi cat phang day vai ---
    body = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    bd = ImageDraw.Draw(body)
    head_cy, head_r = 0.395 * s, 0.137 * s
    bd.ellipse((0.5 * s - head_r, head_cy - head_r, 0.5 * s + head_r, head_cy + head_r), fill=color)
    bd.ellipse((0.235 * s, 0.575 * s, 0.765 * s, 1.03 * s), fill=color)
    cut = int(0.845 * s)  # giu phan vai nam trong khung
    img.alpha_composite(body.crop((0, 0, s, cut)))

    return img.resize((size, size), Image.LANCZOS)


def plate(size: int, mark_frac: float, radius_frac: float = 0.0,
          bg=BRAND, transparent_bg: bool = False) -> Image.Image:
    """Nen (vuong hoac bo goc) kem dau nhan o giua."""
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    if not transparent_bg:
        if radius_frac > 0:
            ImageDraw.Draw(img).rounded_rectangle((0, 0, s - 1, s - 1),
                                                  radius=int(radius_frac * s), fill=bg)
        else:
            img.paste(bg, (0, 0, s, s))
    m = int(mark_frac * s)
    img.alpha_composite(draw_mark(m), (((s - m) // 2), ((s - m) // 2)))
    return img.resize((size, size), Image.LANCZOS)


def save(img: Image.Image, *parts: str, flatten_on=None) -> None:
    path = os.path.join(MOBILE, *parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if flatten_on is not None:  # icon iOS khong duoc co kenh alpha
        bg = Image.new("RGB", img.size, flatten_on)
        bg.paste(img, mask=img.split()[3])
        bg.save(path)
    else:
        img.save(path)
    print("  ", os.path.relpath(path, MOBILE).replace("\\", "/"), f"{img.size[0]}px")


# ---------------------------------------------------------------- Android
print("Android - icon khoi chay (legacy, bo goc):")
for bucket, px in [("mdpi", 48), ("hdpi", 72), ("xhdpi", 96), ("xxhdpi", 144), ("xxxhdpi", 192)]:
    save(plate(px, 0.60, radius_frac=0.21), "android", "app", "src", "main", "res",
         f"mipmap-{bucket}", "ic_launcher.png")

print("Android - icon thich ung (lop truoc + don sac, 108dp):")
for bucket, px in [("mdpi", 108), ("hdpi", 162), ("xhdpi", 216), ("xxhdpi", 324), ("xxxhdpi", 432)]:
    # 0.46 x 108dp = 49.7dp, duong cheo 70.3dp < 72dp -> khong bi mat niet khi mat na tron
    fg = plate(px, 0.46, transparent_bg=True)
    save(fg, "android", "app", "src", "main", "res", f"mipmap-{bucket}", "ic_launcher_foreground.png")
    save(fg, "android", "app", "src", "main", "res", f"mipmap-{bucket}", "ic_launcher_monochrome.png")

print("Android - logo splash (trang, nen trong suot):")
for bucket, px in [("mdpi", 120), ("hdpi", 180), ("xhdpi", 240), ("xxhdpi", 360), ("xxxhdpi", 480)]:
    save(draw_mark(px), "android", "app", "src", "main", "res", f"drawable-{bucket}", "splash_logo.png")

# ---------------------------------------------------------------- iOS
print("iOS - AppIcon (vuong, khong alpha):")
IOS_ICONS = {
    "Icon-App-20x20@1x.png": 20, "Icon-App-20x20@2x.png": 40, "Icon-App-20x20@3x.png": 60,
    "Icon-App-29x29@1x.png": 29, "Icon-App-29x29@2x.png": 58, "Icon-App-29x29@3x.png": 87,
    "Icon-App-40x40@1x.png": 40, "Icon-App-40x40@2x.png": 80, "Icon-App-40x40@3x.png": 120,
    "Icon-App-60x60@1x.png": 60, "Icon-App-60x60@2x.png": 120, "Icon-App-60x60@3x.png": 180,
    "Icon-App-76x76@1x.png": 76, "Icon-App-76x76@2x.png": 152, "Icon-App-76x76@3x.png": 228,
    "Icon-App-83.5x83.5@2x.png": 167,
    "Icon-App-1024x1024@1x.png": 1024,
}
for name, px in IOS_ICONS.items():
    save(plate(px, 0.62), "ios", "Runner", "Assets.xcassets", "AppIcon.appiconset", name,
         flatten_on=BRAND[:3])

print("iOS - LaunchImage (trang, nen trong suot):")
for name, px in [("LaunchImage.png", 120), ("LaunchImage@2x.png", 240), ("LaunchImage@3x.png", 360)]:
    save(draw_mark(px), "ios", "Runner", "Assets.xcassets", "LaunchImage.imageset", name)

# ---------------------------------------------------------------- Web
print("Web - favicon + icon PWA:")
save(plate(32, 0.70), "web", "favicon.png")
for px in (192, 512):
    save(plate(px, 0.62, radius_frac=0.21), "web", "icons", f"Icon-{px}.png")
    # maskable: dau nhan nam trong vung an toan 80%, nen phu kin
    save(plate(px, 0.46), "web", "icons", f"Icon-maskable-{px}.png")

print("\nXong.")
