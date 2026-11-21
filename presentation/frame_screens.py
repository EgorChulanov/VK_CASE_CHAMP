"""Place actual browser screenshots inside the transparent cutouts of device frames."""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

assets = Path(__file__).resolve().parent / "assets"
captures = Path(sys.argv[1])
for frame, screen, output in [
    ("mac", "overview", "mac-shop"),
    ("phone", "card", "phone-shop"),
    ("phone", "clip", "phone-clip"),
    ("phone", "order", "phone-order"),
]:
    device = Image.open(assets / (frame + "-frame.webp")).convert("RGBA")
    w, h = device.size
    alpha = device.getchannel("A").point(lambda v: 0 if v < 16 else 255)
    ImageDraw.floodfill(alpha, (w // 2, h // 2), 128)
    cutout = alpha.point(lambda v: 255 if v == 128 else 0)
    left, top, right, bottom = cutout.getbbox()
    shot = Image.open(captures / (screen + ".png")).convert("RGBA")
    target = (right - left, bottom - top)
    # The display is filled edge to edge. The original frame covers the bezel and camera cutout.
    fitted = ImageOps.fit(shot, target, Image.Resampling.LANCZOS, centering=(0.5, 0))
    composed = Image.new("RGBA", (w, h))
    composed.paste(fitted, (left, top), cutout.crop((left, top, right, bottom)))
    composed.alpha_composite(device)
    composed.save(assets / (output + ".webp"), quality=95, method=6)
