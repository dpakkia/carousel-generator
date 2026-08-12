"""Type-setting ops: the copy itself, and the small furniture built from it.

`text` is the workhorse — everything from a 92px cover title to a page number
is the same op with a different text style. It understands `**bold**` markup,
wraps to a column, aligns within it, and can advance the layout cursor so the
next block positions itself with {"after": 24} instead of a magic number.
"""
from PIL import Image, ImageDraw

from .. import typography as ty
from . import op


def _prepare(ctx, value, type, size, color, leading, tracking, width, uppercase):
    """Shared setup for text and measure: resolve copy, font and wrapped lines."""
    body = ctx.text_value(value)
    if body and uppercase:
        body = body.upper()

    style = ctx.style.text_style(type, {"color": color, "size": size,
                                        "leading": leading, "tracking": tracking})
    px = ctx.num(size, style.get("size", 38))
    font = ctx.style.font(style, px)
    bold = ctx.style.bold_font(style, px)
    track = ctx.num(style.get("tracking", 0))
    lead = ctx.num(style.get("leading"), px * 1.3)
    col = ctx.num(width, ctx.vars.get("TXTW", ctx.size[0] - 2 * ctx.style.margin))
    lines = ty.wrap(ctx.draw, body, font, bold, col, track) if body else []
    return body, style, font, bold, track, lead, col, lines


@op("text")
def text(ctx, value=None, type="body", x=None, y=None, width=None,
         align="left", color=None, size=None, leading=None, tracking=None,
         advance=True, max_lines=None, uppercase=False,
         stroke_width=None, stroke_color=None, **_):
    """Draw a wrapped block of copy.

    value         literal string, "$field" for a deck field, or a "{field}" template
    type          a name from the style's `type` section
    width         the column to wrap and align within (defaults to the text column)
    advance       move the layout cursor to the bottom of this block
    stroke_width  draw an outline; pair with "color": null for hollow type
    """
    body, style, font, bold, track, lead, col, lines = _prepare(
        ctx, value, type, size, color, leading, tracking, width, uppercase)
    if not body:
        return

    fill_token = color if color is not None else style.get("color", "text")
    fill = ctx.color(fill_token) if fill_token else None
    stroke = ctx.num(stroke_width, style.get("stroke_width", 0))
    stroke_fill = ctx.color(stroke_color or style.get("stroke_color")) \
        if (stroke_color or style.get("stroke_color")) else None

    x0 = ctx.num(x, ctx.style.margin)
    y0 = ctx.num(y, ctx.vars.get("cursor", 0))
    if max_lines:
        lines = lines[:int(ctx.num(max_lines))]

    # Hollow type: a stroke with no fill. PIL falls back to its default white
    # ink when fill is None, so the counter has to be punched out explicitly —
    # on a scratch layer, or it would erase the scrim under the glyph too.
    hollow = stroke and fill is None and stroke_fill is not None
    if hollow:
        layer = Image.new("RGBA", ctx.size, (0, 0, 0, 0))
        surface = ImageDraw.Draw(layer)
        fill = (0, 0, 0, 0)
    else:
        surface = ctx.draw

    end = ty.draw_lines(surface, x0, y0, lines, font, bold, fill, lead,
                        align=align, width=col, tracking=track,
                        stroke_width=int(stroke), stroke_fill=stroke_fill)
    if hollow:
        ctx.img.alpha_composite(layer)
    if advance:
        ctx.set_cursor(end)
    ctx.last_block = {"x": x0, "y": y0, "width": col, "height": end - y0,
                      "lines": len(lines)}


@op("measure")
def measure(ctx, value=None, type="body", width=None, size=None, leading=None,
            tracking=None, uppercase=False, name=None, **_):
    """Measure copy without drawing it, exposing the result to later expressions.

    Sets `<name>_h`, `<name>_lines` and `<name>_w` as variables, which is what
    lets a panel size itself to text drawn after it, or a block anchor to the
    foot of the slide:

        {"op": "measure", "name": "title", "value": "$title", "type": "title"}
        {"op": "panel", "box": [56, "H - 132 - title_h - 104", "W - 56", "H - 132"]}
    """
    _, _, font, bold, track, lead, col, lines = _prepare(
        ctx, value, type, size, None, leading, tracking, width, uppercase)
    key = name or (value or "block").lstrip("$")
    widest = max((ty.line_width(ctx.draw, ln, font, bold, track) for ln in lines),
                 default=0.0)
    ctx.vars[f"{key}_lines"] = float(len(lines))
    ctx.vars[f"{key}_h"] = float(len(lines) * lead)
    ctx.vars[f"{key}_w"] = float(widest)


@op("pill")
def pill(ctx, value=None, type="label", x=None, y=None, color=None,
         fill=None, outline=None, radius=None, pad_x=28, pad_y=13, height=None,
         width=None, advance=True, uppercase=False, **_):
    """A badge: a rounded box sized to its own text.

    Used for the "5 POINTS" cover marker. `fill` paints it solid, `outline`
    draws it as a hairline pill; give both for a filled pill with a border.
    """
    body = ctx.text_value(value)
    if not body:
        return
    if uppercase:
        body = body.upper()

    style = ctx.style.text_style(type, {"color": color})
    px = style.get("size", 26)
    font = ctx.style.font(style, px)
    track = ctx.num(style.get("tracking", 0))

    tw = ty.text_width(ctx.draw, body, font, track)
    px_pad = ctx.num(pad_x)
    py_pad = ctx.num(pad_y)
    x0 = ctx.num(x, ctx.style.margin)
    y0 = ctx.num(y, ctx.vars.get("cursor", 0))
    box_w = ctx.num(width, tw + 2 * px_pad)
    box_h = ctx.num(height, px + 2 * py_pad)
    rad = ctx.num(radius, box_h / 2)

    kwargs = dict(fill=ctx.color(fill) if fill else None,
                  outline=ctx.color(outline) if outline else None,
                  width=2)
    if rad:
        ctx.draw.rounded_rectangle([x0, y0, x0 + box_w, y0 + box_h], radius=rad, **kwargs)
    else:
        ctx.draw.rectangle([x0, y0, x0 + box_w, y0 + box_h], **kwargs)

    ty._draw_word(ctx.draw, x0 + px_pad, y0 + py_pad, body, font,
                  ctx.color(style.get("color", "text")), track)
    if advance:
        ctx.set_cursor(y0 + box_h)
    ctx.last_block = {"x": x0, "y": y0, "width": box_w, "height": box_h, "lines": 1}


@op("cursor")
def cursor(ctx, to=None, by=None, **_):
    """Move the layout cursor without drawing — spacing between blocks."""
    if to is not None:
        ctx.set_cursor(ctx.num(to))
    if by is not None:
        ctx.set_cursor(ctx.vars.get("cursor", 0) + ctx.num(by))
