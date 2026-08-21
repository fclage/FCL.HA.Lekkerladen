"""Generate Home Assistant brand images (no external brand marks)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "custom_components" / "lekkerladen" / "brand"

GREEN = (15, 163, 112, 255)
GREEN_DARK = (10, 110, 76, 255)
CREAM = (247, 250, 246, 255)
INK = (18, 42, 34, 255)
WHITE = (255, 255, 255, 255)
NIGHT = (18, 28, 24, 255)
NIGHT_GREEN = (46, 196, 140, 255)


def _rounded_rect(size: int, fill: tuple[int, int, int, int], radius_ratio: float = 0.22) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r = int(size * radius_ratio)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=fill)
    return img


def _plug_icon(size: int, fg: tuple[int, int, int, int]) -> Image.Image:
    """Simple EV plug + bolt, drawn in a square canvas."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    # Charging stand body
    body = (
        int(s * 0.34),
        int(s * 0.28),
        int(s * 0.66),
        int(s * 0.72),
    )
    d.rounded_rectangle(body, radius=int(s * 0.08), fill=fg)
    # Cable handle
    d.rounded_rectangle(
        (int(s * 0.42), int(s * 0.16), int(s * 0.58), int(s * 0.32)),
        radius=int(s * 0.04),
        fill=fg,
    )
    # Two pins
    pin_w = int(s * 0.07)
    pin_h = int(s * 0.12)
    d.rounded_rectangle(
        (int(s * 0.39), int(s * 0.70), int(s * 0.39) + pin_w, int(s * 0.70) + pin_h),
        radius=pin_w // 2,
        fill=fg,
    )
    d.rounded_rectangle(
        (int(s * 0.54), int(s * 0.70), int(s * 0.54) + pin_w, int(s * 0.70) + pin_h),
        radius=pin_w // 2,
        fill=fg,
    )
    return img


def _bolt(size: int, fg: tuple[int, int, int, int]) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    pts = [
        (int(s * 0.56), int(s * 0.30)),
        (int(s * 0.40), int(s * 0.52)),
        (int(s * 0.50), int(s * 0.52)),
        (int(s * 0.44), int(s * 0.70)),
        (int(s * 0.62), int(s * 0.48)),
        (int(s * 0.52), int(s * 0.48)),
    ]
    d.polygon(pts, fill=fg)
    return img


def make_icon(size: int, dark: bool = False) -> Image.Image:
    bg = NIGHT if dark else CREAM
    accent = NIGHT_GREEN if dark else GREEN
    base = _rounded_rect(size, bg)
    # inner circle
    pad = int(size * 0.14)
    d = ImageDraw.Draw(base)
    d.ellipse((pad, pad, size - pad, size - pad), fill=accent)
    plug = _plug_icon(size, WHITE)
    # punch a bolt in the stand
    bolt = _bolt(size, accent if not dark else NIGHT)
    # Composite plug then bolt on top of body cut
    base.alpha_composite(plug)
    # Recolor bolt by drawing on the green body
    base.alpha_composite(bolt)
    # Soft shadow-less; slight inner highlight
    return base


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("segoeui.ttf", "SegoeUI.ttf", "arial.ttf", "Arial.ttf", "calibri.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_logo(height: int, dark: bool = False) -> Image.Image:
    icon = make_icon(height, dark=dark)
    font = _font(int(height * 0.38))
    text = "Lekkerladen"
    tmp = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    tw = ImageDraw.Draw(tmp).textlength(text, font=font)
    width = height + int(tw) + int(height * 0.45)
    bg = NIGHT if dark else CREAM
    img = Image.new("RGBA", (int(width), height), bg)
    img.paste(icon, (0, 0), icon)
    d = ImageDraw.Draw(img)
    color = WHITE if dark else INK
    d.text((height + int(height * 0.12), height * 0.28), text, font=font, fill=color)
    return img


def save_png(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Flatten onto opaque background matching the icon
    bg = Image.new("RGB", img.size, img.getpixel((2, 2))[:3])
    bg.paste(img, mask=img.split()[-1])
    bg.save(path, "PNG", optimize=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    save_png(make_icon(256), OUT / "icon.png")
    save_png(make_icon(512), OUT / "icon@2x.png")
    save_png(make_icon(256, dark=True), OUT / "dark_icon.png")
    save_png(make_icon(512, dark=True), OUT / "dark_icon@2x.png")
    save_png(make_logo(256), OUT / "logo.png")
    save_png(make_logo(512), OUT / "logo@2x.png")
    save_png(make_logo(256, dark=True), OUT / "dark_logo.png")
    save_png(make_logo(512, dark=True), OUT / "dark_logo@2x.png")
    print(f"Wrote brand images to {OUT}")


if __name__ == "__main__":
    main()
