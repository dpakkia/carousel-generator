"""Loading and resolving a style definition.

A style is a JSON document with five parts:

    canvas   slide size and the margin every recipe measures from
    palette  named colours — recipes refer to "amber", never to an RGB triple
    fonts    named roles ("display", "body", "label") bound to families in fonts/
    type     named text styles: font role + size + leading + colour + tracking
    slides   the ordered op recipes for "cover", "secret" and "cta"

`extends` pulls in another style file and merges over it, so a family of
styles can share brand furniture and differ only where they mean to.
"""
import os
import json
import copy

from . import fonts as font_registry
from .config import W as DEFAULT_W, H as DEFAULT_H

STYLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles")

# Merged as dictionaries when a style extends another; anything else is replaced.
_MERGE_KEYS = ("canvas", "palette", "fonts", "type", "vars", "slides",
               "meta", "strings")


class StyleError(ValueError):
    """A style file is malformed or refers to something that does not exist."""


class Style:
    def __init__(self, data, path=None):
        self.data = data
        self.path = path
        self.name = data.get("name") or (
            os.path.splitext(os.path.basename(path))[0] if path else "style")
        self.label = data.get("label", self.name)

        canvas = data.get("canvas", {})
        self.width = int(canvas.get("width", DEFAULT_W))
        self.height = int(canvas.get("height", DEFAULT_H))
        self.margin = int(canvas.get("margin", 96))

        self.palette = data.get("palette", {})
        self.fonts = data.get("fonts", {})
        self.type_styles = data.get("type", {})
        self.vars = data.get("vars", {})
        self.slides = data.get("slides", {})

        # Art direction for the generated background plates. A look and the
        # photography behind it are one decision, so a style may carry its own;
        # a deck can still override, and config supplies the fallback.
        self.image_style = data.get("image_style")

        # Words this style invented — decorative furniture that is part of the
        # look rather than of any brand's language. A locale file overrides
        # them, so anything genuinely translatable still belongs in a locale.
        self.strings = data.get("strings", {})

    # ----------------------------------------------------------------- loading
    @classmethod
    def load(cls, ref, seen=None):
        """Load a style by name ("v1"), or by path to a .json file."""
        path = resolve_path(ref)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        seen = seen or set()
        parent_ref = data.pop("extends", None)
        if parent_ref:
            if parent_ref in seen:
                raise StyleError(f"circular extends chain at {parent_ref!r}")
            seen.add(parent_ref)
            parent = cls.load(parent_ref, seen).data
            data = merge(parent, data)

        return cls(data, path)

    # ------------------------------------------------------------ token lookup
    def color(self, value, default=None):
        """Resolve a colour: a palette name, "#RRGGBB", or an [r,g,b(,a)] list."""
        if value is None:
            return default
        if isinstance(value, str):
            if value.startswith("#"):
                return _hex(value)
            if value in self.palette:
                return self.color(self.palette[value])
            raise StyleError(
                f"{self.name}: unknown colour {value!r} "
                f"(palette has: {', '.join(sorted(self.palette)) or 'nothing'})")
        if isinstance(value, (list, tuple)):
            return tuple(int(c) for c in value)
        raise StyleError(f"{self.name}: cannot read colour {value!r}")

    def text_style(self, name, overrides=None):
        """A resolved text style dict: font spec, size, leading, colour…"""
        if isinstance(name, dict):
            base = dict(name)
        else:
            if name not in self.type_styles:
                raise StyleError(
                    f"{self.name}: unknown type style {name!r} "
                    f"(defined: {', '.join(sorted(self.type_styles)) or 'none'})")
            base = dict(self.type_styles[name])
        if overrides:
            base.update({k: v for k, v in overrides.items() if v is not None})
        return base

    def font_spec(self, role):
        """The font definition behind a role name like "display"."""
        if isinstance(role, dict):
            return role
        if role in self.fonts:
            return self.fonts[role]
        raise StyleError(
            f"{self.name}: unknown font role {role!r} "
            f"(defined: {', '.join(sorted(self.fonts)) or 'none'})")

    def font(self, text_style, size=None):
        """Build the PIL font for a resolved text style."""
        spec = dict(self.font_spec(text_style.get("font", "body")))
        for key in ("weight", "variant", "axes"):     # per-use overrides
            if key in text_style:
                spec[key] = text_style[key]
        return font_registry.load(spec, int(size or text_style.get("size", 38)))

    def bold_font(self, text_style, size=None):
        """The font used for `**bold**` runs inside this text style."""
        spec = dict(self.font_spec(text_style.get("font", "body")))
        bold_role = text_style.get("bold_font")
        if bold_role:
            spec = dict(self.font_spec(bold_role))
        elif "axes" in spec:
            axes = dict(spec["axes"])
            axes["wght"] = min(900, int(axes.get("wght", 400)) + 200)
            spec["axes"] = axes
        elif spec.get("variant") is not None or spec.get("family", "").lower() == "spacemono":
            spec["variant"] = "bold"
        else:
            spec["weight"] = font_registry.heavier(
                text_style.get("weight", spec.get("weight", "Regular")))
        return font_registry.load(spec, int(size or text_style.get("size", 38)))

    # -------------------------------------------------------------- variables
    def base_variables(self):
        """The variables every expression in this style can reference."""
        return {
            "W": self.width,
            "H": self.height,
            "MX": self.margin,
            "MARGIN": self.margin,
            "CX": self.width / 2,
            "CY": self.height / 2,
        }

    def recipe(self, kind):
        if kind not in self.slides:
            raise StyleError(
                f"{self.name}: no recipe for {kind!r} slides "
                f"(has: {', '.join(sorted(self.slides)) or 'none'})")
        return self.slides[kind]


# --------------------------------------------------------------------- helpers
def resolve_path(ref):
    """Turn "v1" / "v1.json" / a real path into an existing style file path."""
    if os.path.isfile(ref):
        return ref
    for candidate in (ref, f"{ref}.json"):
        p = os.path.join(STYLE_DIR, candidate)
        if os.path.isfile(p):
            return p
    raise StyleError(f"no style named {ref!r} in {STYLE_DIR}")


def available():
    """Every style name shipped in carousel/styles/, sorted."""
    if not os.path.isdir(STYLE_DIR):
        return []
    return sorted(os.path.splitext(f)[0] for f in os.listdir(STYLE_DIR)
                  if f.endswith(".json") and not f.startswith("_"))


def rotate(index, names=None):
    """The style for deck number `index`, cycling through the available styles.

    Deck 1 gets the first style, deck 2 the second, and the sequence wraps: with
    seven styles, deck 8 comes back to the first. The point is that consecutive
    posts never repeat a look, so it rotates over however many styles are
    installed rather than a fixed cycle — a fork with three styles rotates
    through three.
    """
    names = list(names) if names is not None else available()
    if not names:
        raise StyleError(f"no styles to rotate through in {STYLE_DIR}")
    if index is None or index < 1:
        raise StyleError(
            f"cannot rotate to a style without a deck number (got {index!r})")
    return names[(index - 1) % len(names)]


def rotation_table(count=None, names=None):
    """[(deck number, style name)] for the first `count` decks — for showing."""
    names = list(names) if names is not None else available()
    count = count or (len(names) + 2)
    return [(n, rotate(n, names)) for n in range(1, count + 1)]


def merge(base, over):
    """Deep-merge `over` onto `base` for the known section keys."""
    out = copy.deepcopy(base)
    for key, value in over.items():
        if key in _MERGE_KEYS and isinstance(value, dict) and isinstance(out.get(key), dict):
            merged = dict(out[key])
            merged.update(value)
            out[key] = merged
        else:
            out[key] = copy.deepcopy(value)
    return out


def _hex(s):
    s = s.lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) not in (6, 8):
        raise StyleError(f"bad hex colour #{s}")
    return tuple(int(s[i:i + 2], 16) for i in range(0, len(s), 2))
