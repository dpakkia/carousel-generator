"""Font registry — resolves the family names used in style JSON to real files.

A style never names a path. It says `{"family": "inter", "weight": "Black"}`,
and this module finds Inter.ttf in fonts/. Drop any TTF into that directory and
its lowercased stem becomes an available family name, so adding a typeface to
the platform is a file copy plus a line of JSON.

Variable fonts are driven either by a named instance (`weight: "SemiBold"`) or
by explicit axes (`axes: {"wght": 620, "opsz": 64}`) for families like Fraunces
whose named instances are too coarse.
"""
import os
import glob

from PIL import ImageFont

from .config import FONT_DIR, DEJAVU, DEJAVU_BOLD

_files = None
_cache = {}

# Weight ladder used to resolve the bold counterpart of a run of `**text**`.
WEIGHT_LADDER = ["Thin", "ExtraLight", "Light", "Regular", "Medium",
                 "SemiBold", "Bold", "ExtraBold", "Black"]


def families():
    """Map of family name -> {variant: path}, discovered from fonts/.

    `SpaceMono-Bold.ttf` registers family "spacemono", variant "bold";
    `Inter.ttf` registers family "inter", variant "" (the default file).
    """
    global _files
    if _files is None:
        _files = {}
        for path in sorted(glob.glob(os.path.join(FONT_DIR, "*.tt[fc]"))
                           + glob.glob(os.path.join(FONT_DIR, "*.otf"))):
            stem = os.path.splitext(os.path.basename(path))[0]
            family, _, variant = stem.partition("-")
            _files.setdefault(family.lower(), {})[variant.lower()] = path
    return _files


def path_for(family, variant=""):
    """The TTF path for a family, or None. `variant` matches the -Suffix.

    With no variant asked for, prefer the bare file (Inter.ttf) and then an
    explicit Regular — never fall through to whichever file sorts first, or a
    family shipped only as -Regular/-Bold would default to Bold.
    """
    fam = families().get((family or "").lower())
    if not fam:
        return None
    wanted = (variant or "").lower()
    if wanted and wanted in fam:
        return fam[wanted]
    for fallback in ("", "regular", "book"):
        if fallback in fam:
            return fam[fallback]
    return next(iter(fam.values()))


def load(spec, size):
    """Build a PIL font from a style's font spec dict at `size`.

    spec keys:
      family  — "inter", "fraunces", "spacemono" (any file in fonts/)
      weight  — named instance of a variable font, e.g. "Bold"
      variant — file suffix to prefer, e.g. "bold" for SpaceMono-Bold.ttf
      axes    — explicit variable axes, e.g. {"opsz": 64, "wght": 620}
                (applied in the font's own axis order)
    """
    if isinstance(spec, str):                     # shorthand: "inter:Black"
        family, _, weight = spec.partition(":")
        spec = {"family": family, "weight": weight or None}

    family = spec.get("family", "inter")
    weight = spec.get("weight")
    variant = spec.get("variant", "")
    axes = spec.get("axes")

    key = (family, weight, variant, tuple(sorted((axes or {}).items())), size)
    if key in _cache:
        return _cache[key]

    path = path_for(family, variant)
    font = None
    if path:
        try:
            font = ImageFont.truetype(path, size)
            if axes:
                _apply_axes(font, axes, size)
            elif weight:
                _apply_named(font, weight)
        except Exception:
            font = None

    if font is None:                              # last resort, keeps rendering alive
        heavy = weight in ("Bold", "ExtraBold", "Black", "SemiBold") or spec.get("bold")
        fallback = DEJAVU_BOLD if heavy else DEJAVU
        try:
            font = ImageFont.truetype(fallback, size)
        except Exception:
            font = ImageFont.load_default()

    _cache[key] = font
    return font


def _apply_named(font, weight):
    try:
        font.set_variation_by_name(weight)
    except Exception:
        try:
            font.set_variation_by_name(weight.encode())
        except Exception:
            pass


# Four-letter OpenType tags -> the human axis names PIL reports.
_AXIS_ALIASES = {
    "opsz": "optical size",
    "wght": "weight",
    "wdth": "width",
    "slnt": "slant",
    "ital": "italic",
    "soft": "softness",
    "wonk": "wonky",
}


# Optical size is meant to track the type size: small text wants sturdier,
# more open shapes than a 96px headline does. When a style drives axes
# explicitly but leaves opsz out, scale it with the size rather than pinning
# the font's default.
OPTICAL_RATIO = 0.7


def _apply_axes(font, axes, size):
    """Set variable axes by name or OpenType tag, in the font's own axis order.

    PIL wants every axis supplied positionally, so unmentioned axes are filled
    with their declared default — except optical size, which follows the type
    size unless the style pins it.
    """
    try:
        declared = font.get_variation_axes()
    except Exception:
        return

    wanted = {}
    for key, value in axes.items():
        name = _AXIS_ALIASES.get(key.lower(), key.lower())
        wanted[name] = value

    values = []
    for axis in declared:
        name = axis.get("name", b"")
        if isinstance(name, bytes):
            name = name.decode(errors="ignore")
        name = name.strip().lower()
        if name in wanted:
            values.append(wanted[name])
        elif name == "optical size":
            lo = axis.get("minimum", 9)
            hi = axis.get("maximum", 144)
            values.append(max(lo, min(hi, int(size * OPTICAL_RATIO))))
        else:
            values.append(axis.get("default"))

    try:
        font.set_variation_by_axes(values)
    except Exception:
        pass


def heavier(weight, steps=2):
    """The bold counterpart of a named weight, at least Bold."""
    try:
        i = WEIGHT_LADDER.index(weight)
    except ValueError:
        i = WEIGHT_LADDER.index("Regular")
    lo = WEIGHT_LADDER.index("Bold")
    return WEIGHT_LADDER[min(max(i + steps, lo), len(WEIGHT_LADDER) - 1)]
