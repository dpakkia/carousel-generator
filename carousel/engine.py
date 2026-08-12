"""The renderer: runs a style's op recipes against a deck's copy.

One slide = one transparent canvas + the ordered list of ops the style defines
for that slide kind. The context carries everything an op needs: the image, the
style's tokens, the deck's text, and the layout cursor that lets blocks stack
without hardcoded coordinates.
"""
import copy
import zlib

from PIL import Image, ImageDraw

from . import ops
from . import values
from . import locales
from .style import Style, StyleError
from .deck import strings_for
from .config import HANDLE, WORDMARK


class RenderContext:
    """What an op is handed: the canvas, the tokens, the copy, the cursor."""

    def __init__(self, style, img, variables, data):
        self.style = style
        self.img = img
        self.draw = ImageDraw.Draw(img)
        self.vars = variables
        self.data = data
        self.last_block = None

    @property
    def size(self):
        return self.img.size

    # ------------------------------------------------------------- resolution
    def num(self, value, default=None):
        return values.number(value, self.vars, default)

    def box(self, value, default=None):
        return values.box(value, self.vars) if value is not None else default

    def color(self, value, default=None):
        return self.style.color(value, default)

    def set_cursor(self, y):
        self.vars["cursor"] = float(y)

    def text_value(self, value):
        """Resolve an op's `value`: a deck field, a template, or a literal."""
        if value is None:
            return None
        if not isinstance(value, str):
            return str(value)
        if value.startswith("$"):
            return self.data.get(value[1:], "")
        if "{" in value:
            try:
                return value.format(**self.data)
            except (KeyError, IndexError, ValueError):
                return value
        return value


def render_slide(style, kind, data, variables=None):
    """Render one slide of `kind` ("cover" | "secret" | "cta")."""
    img = Image.new("RGBA", (style.width, style.height), (0, 0, 0, 0))

    env = style.base_variables()
    env["TXTW"] = style.width - 2 * style.margin
    env["cursor"] = 0.0
    for name, expr in style.vars.items():           # style-declared shorthands
        env[name] = values.number(expr, env)
    for key, value in (variables or {}).items():
        env[key] = value
    for key, value in data.items():                 # numbers usable in expressions
        if isinstance(value, (int, float)):
            env[key] = value

    ctx = RenderContext(style, img, env, data)
    for index, spec in enumerate(style.recipe(kind)):
        _run(ctx, spec, style, kind, index)
    return img


def _run(ctx, spec, style, kind, index):
    if not isinstance(spec, dict) or "op" not in spec:
        raise StyleError(f"{style.name}/{kind}[{index}]: every step needs an \"op\"")
    if not values.truthy(spec.get("when"), ctx.vars):
        return
    params = {k: v for k, v in spec.items() if k not in ("op", "when", "note")}
    try:
        ops.get(spec["op"])(ctx, **params)
    except Exception as e:
        # Always name the failing step: styles are usually authored from a brand
        # brief by someone who cannot read a Python traceback.
        raise StyleError(
            f"{style.name} · {kind} slide · step {index + 1} "
            f"(op {spec['op']!r}): {e}") from e


def slide_data(content, kind, number=None, index=None, count=None,
               total=None, style=None):
    """Everything a recipe can reference: the deck's copy, the brand, the chrome.

    Deck fields are `$title`, `$headline`, `{index:02d}`…; the fixed words a
    style draws around them (`$scroll`, `$follow`) come from the deck's locale,
    already filled in with the brand's handle.
    """
    data = {
        "title": content.get("title", ""),
        "subtitle": content.get("subtitle", ""),
        "badge": content.get("badge", ""),
        "question": content.get("cta_q", ""),
        "cta_q": content.get("cta_q", ""),
        "name": content.get("name", ""),
        "handle": content.get("handle", HANDLE),
        "wordmark": content.get("wordmark", WORDMARK),
        "headline": "",
        "body": "",
        "kind": kind,
        "slide": number or 1,
        "index": index or 0,
        "count": count or len(content.get("secrets", [])),
        "total": total or (len(content.get("secrets", [])) + 2),
    }
    if kind == "secret" and index:
        headline, body = content["secrets"][index - 1]
        data["headline"] = headline
        data["body"] = body

    # Chrome last: it may interpolate the brand fields above. Style defaults
    # sit under the locale, the deck's own `strings` block over it.
    data.update(locales.resolve(content.get("locale"), data,
                                style_strings=getattr(style, "strings", None),
                                deck_strings=strings_for(content)))
    return data


def render_deck(style, content):
    """Render every slide of a deck in posting order."""
    secrets = content.get("secrets", [])
    total = len(secrets) + 2
    style = apply_variant(style, content)

    images = [render_slide(style, "cover",
                           slide_data(content, "cover", 1, total=total, style=style))]
    for i, _ in enumerate(secrets, start=1):
        images.append(render_slide(style, "secret", slide_data(
            content, "secret", i + 1, i, len(secrets), total, style=style)))
    images.append(render_slide(style, "cta", slide_data(
        content, "cta", total, total=total, style=style)))
    return images


def apply_variant(style, content):
    """Pick one of a style's palette variants for this deck, if it has any.

    A style may declare `variants`, each a palette overlay. The deck chooses one
    by name via its "palette" field; otherwise the deck's name selects one
    deterministically, so a given deck always renders in the same colours but a
    run of decks cycles through the family.
    """
    variants = style.data.get("variants")
    if not variants:
        return style

    order = style.data.get("variant_order") or sorted(variants)
    wanted = (content.get("palette") or "").strip().lower()
    if wanted not in variants:
        seed = zlib.crc32((content.get("name") or "deck").encode())
        wanted = order[seed % len(order)]

    picked = Style(copy.deepcopy(style.data), style.path)
    picked.palette = dict(style.palette)
    picked.palette.update(variants[wanted])
    picked.data["active_variant"] = wanted
    return picked
