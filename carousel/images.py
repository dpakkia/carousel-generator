"""Generate the background plates for a deck from its image prompts.

Plates are expensive and art-directed: once bg_03.png is right, regenerating it
because you edited slide 5 is a real loss. So this module **never overwrites an
existing plate** unless you ask it to, and can target a single slide.

Prompts come from the deck's content.json (`image_prompts`), one per slide, in
slide order. Requires OPENAI_API_KEY in the environment or a .env beside the
deck; install the optional dependency with `pip install openai`.
"""
import os
import base64
from io import BytesIO

from PIL import Image

from .config import W, H
from . import deck as deck_io

MODEL = "gpt-image-2"
SIZE = "1088x1360"       # divisible by 16 and exactly 4:5; cropped to 1080x1350
QUALITY = "medium"       # low | medium | high — low is plenty for dark plates


class ImageError(RuntimeError):
    pass


def fit(img, size=(W, H)):
    """Cover-crop to the slide aspect without distorting."""
    tw, th = size
    iw, ih = img.size
    scale = max(tw / iw, th / ih)
    r = img.resize((max(1, int(iw * scale + 0.5)), max(1, int(ih * scale + 0.5))),
                   Image.LANCZOS)
    rw, rh = r.size
    left, top = (rw - tw) // 2, (rh - th) // 2
    return r.crop((left, top, left + tw, top + th))


def plate_path(folder, n):
    return os.path.join(folder, f"bg_{n:02d}.png")


def pending(folder, content, only=None, force=False):
    """Which slides still need a plate: [(slide_number, prompt)].

    only  — restrict to these 1-based slide numbers
    force — include slides whose plate already exists (it will be overwritten)
    """
    prompts = content.get("image_prompts", [])
    total = deck_io.total_slides(content)
    todo = []
    for n in range(1, total + 1):
        if only and n not in only:
            continue
        prompt = prompts[n - 1] if n - 1 < len(prompts) else ""
        if not prompt:
            continue
        if os.path.isfile(plate_path(folder, n)) and not force:
            continue
        todo.append((n, prompt))
    return todo


def generate(folder, content, only=None, force=False, model=MODEL,
             size=SIZE, quality=QUALITY, dry_run=False, log=print):
    """Generate the missing plates for a deck. Returns the paths written."""
    todo = pending(folder, content, only, force)
    if not todo:
        log("every plate already exists — nothing to generate "
            "(pass --force to replace them)")
        return []

    if dry_run:
        for n, prompt in todo:
            log(f"would generate bg_{n:02d}.png  ←  {prompt[:70]}…")
        return []

    client = _client()
    written = []
    for n, prompt in todo:
        log(f"generating bg_{n:02d}.png …")
        img = _one(client, prompt, model, size, quality)
        path = plate_path(folder, n)
        fit(img).save(path, "PNG")
        written.append(path)
    return written


def _client():
    try:
        from openai import OpenAI
    except ImportError:
        raise ImageError(
            "the openai package is not installed — run: pip install openai") from None
    if not os.environ.get("OPENAI_API_KEY"):
        raise ImageError(
            "OPENAI_API_KEY is not set. Export it, or put it in a .env file "
            "and load it before running.")
    return OpenAI()


def _one(client, prompt, model, size, quality):
    result = client.images.generate(model=model, prompt=prompt, size=size,
                                    quality=quality, n=1)
    data = result.data[0]
    if getattr(data, "b64_json", None):
        return Image.open(BytesIO(base64.b64decode(data.b64_json))).convert("RGB")
    raise ImageError("the image API returned no image data")


def load_dotenv(path):
    """Minimal .env reader — avoids a dependency for one line of config."""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
