"""Flatten slide overlays onto their background plates.

Each slide_NN.png is a transparent text layer; each bg_NN.png is the generated
photographic plate behind it. Composing them gives final_NN.jpg — the file you
actually post. JPEG, not PNG: Instagram re-compresses PNGs harshly, and its
Graph API rejects them outright on container creation (error 2207032).
"""
import os
import re
import glob

from PIL import Image

from .config import W, H, CHARCOAL


def fit(img, size):
    """Cover-crop `img` to `size` without distorting it."""
    tw, th = size
    iw, ih = img.size
    scale = max(tw / iw, th / ih)
    resized = img.resize((max(1, int(iw * scale + 0.5)),
                          max(1, int(ih * scale + 0.5))), Image.LANCZOS)
    rw, rh = resized.size
    left = (rw - tw) // 2
    top = (rh - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def compose_slide(slide_path, plate_path=None, size=(W, H), ground=CHARCOAL):
    """One slide over one plate. A missing plate falls back to brand charcoal."""
    base = Image.new("RGB", size, ground)
    if plate_path and os.path.isfile(plate_path):
        plate = Image.open(plate_path).convert("RGB")
        if plate.size != size:
            plate = fit(plate, size)
        base.paste(plate, (0, 0))

    overlay = Image.open(slide_path).convert("RGBA")
    if overlay.size != size:
        overlay = overlay.resize(size, Image.LANCZOS)
    base.paste(overlay, (0, 0), overlay)
    return base


def compose_folder(folder, size=(W, H), quality=92, ground=CHARCOAL):
    """Compose every slide in a deck folder. Returns the final_*.jpg paths."""
    slides = sorted(glob.glob(os.path.join(folder, "slide_*.png")))
    if not slides:
        raise FileNotFoundError(f"no slide_*.png in {folder}")

    outputs = []
    for slide in slides:
        m = re.search(r"slide_(\d+)\.png$", os.path.basename(slide))
        if not m:
            continue
        n = m.group(1)
        plate = os.path.join(folder, f"bg_{n}.png")
        if not os.path.isfile(plate):
            for ext in ("jpg", "jpeg", "webp"):
                alt = os.path.join(folder, f"bg_{n}.{ext}")
                if os.path.isfile(alt):
                    plate = alt
                    break
        out = os.path.join(folder, f"final_{n}.jpg")
        compose_slide(slide, plate, size, ground).save(
            out, "JPEG", quality=quality, subsampling=0, optimize=True)
        outputs.append(out)
    return outputs


def latest_deck(root):
    """The highest-numbered deck folder under `root`, or None."""
    dirs = [d for d in glob.glob(os.path.join(root, "*")) if os.path.isdir(d)
            and re.match(r"(TODO-|DONE-)?\d+", os.path.basename(d))]
    return sorted(dirs)[-1] if dirs else None
