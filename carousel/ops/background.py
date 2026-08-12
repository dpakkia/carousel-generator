"""Light and shade: the ops that make type legible over a photograph.

A slide is a transparent overlay laid over a bg plate, so these ops never paint
an opaque background — they lay down gradients, blooms and washes that let the
photo through while giving the copy a floor to sit on.
"""
from PIL import Image, ImageDraw, ImageFilter

from . import op


@op("vscrim")
def vscrim(ctx, top=0, bottom=200, color="scrim", **_):
    """Vertical scrim: alpha ramps from `top` at y=0 to `bottom` at the foot."""
    w, h = ctx.size
    top_a, bot_a = ctx.num(top), ctx.num(bottom)
    ramp = Image.new("L", (1, h))
    px = ramp.load()
    for y in range(h):
        px[0, y] = int(round(top_a + (bot_a - top_a) * y / (h - 1)))
    layer = Image.new("RGBA", (w, h), ctx.color(color) + (0,))
    layer.putalpha(ramp.resize((w, h)))
    ctx.img.alpha_composite(layer)


@op("hscrim")
def hscrim(ctx, left=0, right=200, color="scrim", **_):
    """Horizontal scrim: alpha ramps from `left` at x=0 to `right` at the edge."""
    w, h = ctx.size
    l_a, r_a = ctx.num(left), ctx.num(right)
    ramp = Image.new("L", (w, 1))
    px = ramp.load()
    for x in range(w):
        px[x, 0] = int(round(l_a + (r_a - l_a) * x / (w - 1)))
    layer = Image.new("RGBA", (w, h), ctx.color(color) + (0,))
    layer.putalpha(ramp.resize((w, h)))
    ctx.img.alpha_composite(layer)


@op("rscrim")
def rscrim(ctx, x=None, y=None, r=400, alpha=180, color="scrim", **_):
    """Soft radial scrim, darkest at its centre and fading outward."""
    w, h = ctx.size
    cx = ctx.num(x, w / 2)
    cy = ctx.num(y, h / 2)
    rad = ctx.num(r)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse([cx - rad, cy - rad, cx + rad, cy + rad],
                                 fill=int(ctx.num(alpha)))
    layer = Image.new("RGBA", (w, h), ctx.color(color) + (0,))
    layer.putalpha(mask.filter(ImageFilter.GaussianBlur(rad * 0.45)))
    ctx.img.alpha_composite(layer)


@op("glow")
def glow(ctx, x=None, y=None, r=300, color="accent", alpha=60, spread=0.55, **_):
    """A blurred disc of light — a bloom that reads as if it came from the photo."""
    w, h = ctx.size
    cx = ctx.num(x, w / 2)
    cy = ctx.num(y, h / 2)
    rad = ctx.num(r)
    layer = Image.new("RGBA", ctx.img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse([cx - rad, cy - rad, cx + rad, cy + rad],
                                  fill=ctx.color(color) + (int(ctx.num(alpha)),))
    ctx.img.alpha_composite(layer.filter(
        ImageFilter.GaussianBlur(rad * ctx.num(spread))))


@op("wash")
def wash(ctx, blobs=(), strength=0.58, resolution=0.2, blur=0.10, **_):
    """Painterly duotone wash: blurred colour blobs rendered small, then upscaled.

    Working at a fraction of full resolution and scaling up with BICUBIC
    smooths the gradient and removes banding for free. Blob coordinates are
    given in normal slide coordinates and scaled down internally.
    """
    w, h = ctx.size
    scale = ctx.num(resolution)
    lw, lh = max(8, int(w * scale)), max(8, int(h * scale))

    small = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    for blob in blobs:
        bx = ctx.num(blob.get("x"), w / 2) * scale
        by = ctx.num(blob.get("y"), h / 2) * scale
        br = ctx.num(blob.get("r"), 200) * scale
        fill = ctx.color(blob.get("color", "accent")) + (int(ctx.num(blob.get("alpha", 160))),)
        layer = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse([bx - br, by - br, bx + br, by + br], fill=fill)
        small.alpha_composite(layer.filter(ImageFilter.GaussianBlur(br * 0.6)))

    small = small.filter(ImageFilter.GaussianBlur(lw * ctx.num(blur)))
    big = small.resize((w, h), Image.BICUBIC)
    s = ctx.num(strength)
    big.putalpha(big.getchannel("A").point(lambda v: int(v * s)))
    ctx.img.alpha_composite(big)


@op("panel")
def panel(ctx, box=None, color="scrim", alpha=150, radius=0, blur=0,
          outline=None, width=2, **_):
    """A translucent card behind copy — the frosted-panel legibility floor.

    The plate still shows at the margins and faintly through the fill, so the
    photograph stays part of the design instead of being buried by it.
    """
    w, h = ctx.size
    x0, y0, x1, y1 = ctx.box(box, [0, 0, w, h])
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    fill = ctx.color(color) + (int(ctx.num(alpha)),)
    edge = (ctx.color(outline) + (255,)) if outline else None
    rad = ctx.num(radius)
    if rad:
        d.rounded_rectangle([x0, y0, x1, y1], radius=rad, fill=fill,
                            outline=edge, width=int(ctx.num(width)))
    else:
        d.rectangle([x0, y0, x1, y1], fill=fill,
                    outline=edge, width=int(ctx.num(width)))
    b = ctx.num(blur)
    if b:
        layer = layer.filter(ImageFilter.GaussianBlur(b))
    ctx.img.alpha_composite(layer)
