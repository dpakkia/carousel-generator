"""Structure and furniture: rules, frames, blocks, marks and viewfinder geometry.

These are the ops that give a style its skeleton — the hard frame of a
brutalist layout, the hairline rules of an editorial one, the focus brackets
and thirds grid of the teaching style.
"""
from PIL import ImageDraw

from . import op


@op("rect")
def rect(ctx, box=None, fill=None, outline=None, width=2, radius=0, **_):
    """A rectangle: filled, outlined, or both. `radius` rounds the corners."""
    x0, y0, x1, y1 = ctx.box(box, [0, 0, ctx.size[0], ctx.size[1]])
    kwargs = dict(fill=ctx.color(fill) if fill else None,
                  outline=ctx.color(outline) if outline else None,
                  width=int(ctx.num(width)))
    rad = ctx.num(radius)
    if rad:
        ctx.draw.rounded_rectangle([x0, y0, x1, y1], radius=rad, **kwargs)
    else:
        ctx.draw.rectangle([x0, y0, x1, y1], **kwargs)


@op("frame")
def frame(ctx, inset=None, color="paper", width=3, **_):
    """A hairline frame inset from the slide edge."""
    w, h = ctx.size
    i = ctx.num(inset, ctx.style.margin)
    ctx.draw.rectangle([i, i, w - i, h - i],
                       outline=ctx.color(color), width=int(ctx.num(width)))


def _stroke(ctx, color, alpha):
    """A colour with optional alpha — hairlines that sit *in* the image."""
    rgb = ctx.color(color)
    if alpha is None:
        return rgb
    return tuple(rgb[:3]) + (int(ctx.num(alpha)),)


@op("line")
def line(ctx, x1=0, y1=0, x2=0, y2=0, color="accent", width=2, alpha=None, **_):
    """A straight rule between two points."""
    ctx.draw.line([ctx.num(x1), ctx.num(y1), ctx.num(x2), ctx.num(y2)],
                  fill=_stroke(ctx, color, alpha), width=int(ctx.num(width)))


@op("rule")
def rule(ctx, x=None, y=0, length=100, color="accent", width=2, alpha=None,
         to=None, **_):
    """A horizontal rule: from `x` for `length`, or from `x` to `to`."""
    x0 = ctx.num(x, ctx.style.margin)
    x1 = ctx.num(to) if to is not None else x0 + ctx.num(length)
    yy = ctx.num(y)
    ctx.draw.line([x0, yy, x1, yy],
                  fill=_stroke(ctx, color, alpha), width=int(ctx.num(width)))


@op("ellipse")
def ellipse(ctx, x=None, y=None, r=20, fill=None, outline=None, width=2, **_):
    cx = ctx.num(x, ctx.size[0] / 2)
    cy = ctx.num(y, ctx.size[1] / 2)
    rad = ctx.num(r)
    ctx.draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad],
                     fill=ctx.color(fill) if fill else None,
                     outline=ctx.color(outline) if outline else None,
                     width=int(ctx.num(width)))


@op("spark")
def spark(ctx, x=None, y=None, r=10, color="accent", pinch=0.16, **_):
    """A four-pointed star. `pinch` sets how needle-like the points are."""
    cx = ctx.num(x, ctx.size[0] / 2)
    cy = ctx.num(y, ctx.size[1] / 2)
    rad = ctx.num(r)
    ri = rad * ctx.num(pinch)
    ctx.draw.polygon(
        [(cx, cy - rad), (cx + ri, cy - ri), (cx + rad, cy), (cx + ri, cy + ri),
         (cx, cy + rad), (cx - ri, cy + ri), (cx - rad, cy), (cx - ri, cy - ri)],
        fill=ctx.color(color))


@op("sparks")
def sparks(ctx, at=(), color="accent", **_):
    """A scatter of sparks: `at` is a list of {x, y, r} around the slide."""
    for s in at:
        spark(ctx, x=s.get("x"), y=s.get("y"), r=s.get("r", 8),
              color=s.get("color", color))


@op("polygon")
def polygon(ctx, x=None, y=None, r=20, sides=4, rotation=0, fill=None,
            outline=None, width=2, **_):
    """A regular polygon — diamonds, triangles, hexagon markers."""
    cx = ctx.num(x, ctx.size[0] / 2)
    cy = ctx.num(y, ctx.size[1] / 2)
    ctx.draw.regular_polygon((cx, cy, ctx.num(r)), int(ctx.num(sides)),
                             rotation=ctx.num(rotation),
                             fill=ctx.color(fill) if fill else None,
                             outline=ctx.color(outline) if outline else None)


@op("grid")
def grid(ctx, divisions=3, color="line", width=1, inset=None, alpha=None,
         intersections=0, **_):
    """A rule-of-thirds (or n-ths) grid — the viewfinder scaffold.

    `intersections` draws a small cross at each crossing point, which is what
    makes the grid read as a camera overlay rather than a table.
    """
    w, h = ctx.size
    n = max(2, int(ctx.num(divisions)))
    i = ctx.num(inset, ctx.style.margin)
    col = _stroke(ctx, color, alpha)
    wd = int(ctx.num(width))
    xs = [w * k / n for k in range(1, n)]
    ys = [h * k / n for k in range(1, n)]
    for x in xs:
        ctx.draw.line([x, i, x, h - i], fill=col, width=wd)
    for y in ys:
        ctx.draw.line([i, y, w - i, y], fill=col, width=wd)

    tick = ctx.num(intersections)
    if tick:
        bright = _stroke(ctx, color, None if alpha is None
                         else min(255, ctx.num(alpha) + 60))
        for x in xs:
            for y in ys:
                ctx.draw.line([x - tick, y, x + tick, y], fill=bright, width=wd)
                ctx.draw.line([x, y - tick, x, y + tick], fill=bright, width=wd)


@op("corner_marks")
def corner_marks(ctx, inset=None, length=40, color="line", width=3, alpha=None, **_):
    """L-shaped crop marks in the four corners."""
    w, h = ctx.size
    i = ctx.num(inset, ctx.style.margin)
    ln = ctx.num(length)
    col = _stroke(ctx, color, alpha)
    wd = int(ctx.num(width))
    for cx, sx in ((i, 1), (w - i, -1)):
        for cy, sy in ((i, 1), (h - i, -1)):
            ctx.draw.line([cx, cy, cx + ln * sx, cy], fill=col, width=wd)
            ctx.draw.line([cx, cy, cx, cy + ln * sy], fill=col, width=wd)


@op("bracket")
def bracket(ctx, box=None, length=36, color="accent", width=4, alpha=None, **_):
    """Focus brackets: corner ticks around a region, not a closed rectangle."""
    x0, y0, x1, y1 = ctx.box(box, [0, 0, ctx.size[0], ctx.size[1]])
    ln = ctx.num(length)
    col = _stroke(ctx, color, alpha)
    wd = int(ctx.num(width))
    for x, sx in ((x0, 1), (x1, -1)):
        for y, sy in ((y0, 1), (y1, -1)):
            ctx.draw.line([x, y, x + ln * sx, y], fill=col, width=wd)
            ctx.draw.line([x, y, x, y + ln * sy], fill=col, width=wd)


@op("reticle")
def reticle(ctx, x=None, y=None, r=26, gap=10, tail=14, color="accent",
            width=3, alpha=None, dot=3, **_):
    """A focus-confirm mark: a ring, four crosshair arms, and a centre dot."""
    cx = ctx.num(x, ctx.size[0] / 2)
    cy = ctx.num(y, ctx.size[1] / 2)
    rad = ctx.num(r)
    g = ctx.num(gap)
    t = ctx.num(tail)
    col = _stroke(ctx, color, alpha)
    wd = int(ctx.num(width))
    ctx.draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=col, width=wd)
    ctx.draw.line([cx - rad - t, cy, cx - g, cy], fill=col, width=wd)
    ctx.draw.line([cx + g, cy, cx + rad + t, cy], fill=col, width=wd)
    ctx.draw.line([cx, cy - rad - t, cx, cy - g], fill=col, width=wd)
    ctx.draw.line([cx, cy + g, cx, cy + rad + t], fill=col, width=wd)
    d = ctx.num(dot)
    if d:
        ctx.draw.ellipse([cx - d, cy - d, cx + d, cy + d], fill=col)


@op("ticks")
def ticks(ctx, y=None, x=None, to=None, count=9, length=12, minor=6,
          color="accent", width=2, alpha=None, **_):
    """A measured tick axis: a baseline with major and minor graduations."""
    w = ctx.size[0]
    x0 = ctx.num(x, ctx.style.margin)
    x1 = ctx.num(to, w - ctx.style.margin)
    yy = ctx.num(y, ctx.style.margin)
    n = max(1, int(ctx.num(count)))
    col = _stroke(ctx, color, alpha)
    wd = int(ctx.num(width))
    major = ctx.num(length)
    small = ctx.num(minor)

    ctx.draw.line([x0, yy, x1, yy], fill=col, width=wd)
    step = max(1, n // 3)
    for k in range(n + 1):
        px = x0 + (x1 - x0) * k / n
        h = major if k % step == 0 else small
        ctx.draw.line([px, yy - h, px, yy], fill=col, width=wd)
