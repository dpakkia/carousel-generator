"""Slide chrome, by language.

A style draws fixed words around your copy — "Swipe →", "Follow @you", the
section label above each point. Those words are not part of a look and they are
not part of a deck's content, so they live here: one file per language, shared
by every style.

    carousel/locales/en.json
    carousel/locales/it.json

A deck picks one with `"locale": "it"`. To add a language, copy a file and
translate the values; every shipped style speaks it immediately.
"""
import os
import json

LOCALE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")
DEFAULT = "en"

_cache = {}


class LocaleError(ValueError):
    """The requested language has no file."""


def available():
    """Every language shipped, sorted."""
    if not os.path.isdir(LOCALE_DIR):
        return []
    return sorted(os.path.splitext(f)[0] for f in os.listdir(LOCALE_DIR)
                  if f.endswith(".json"))


def load(name=None):
    """The strings for a language. Unknown names fall back to the default."""
    name = (name or DEFAULT).strip().lower()
    if name in _cache:
        return _cache[name]

    path = os.path.join(LOCALE_DIR, f"{name}.json")
    if not os.path.isfile(path):
        if name == DEFAULT:
            raise LocaleError(
                f"the default locale {DEFAULT!r} is missing from {LOCALE_DIR}")
        raise LocaleError(
            f"no locale {name!r} — available: {', '.join(available())}")

    with open(path, encoding="utf-8") as f:
        strings = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
    _cache[name] = strings
    return strings


def resolve(name, data, style_strings=None, deck_strings=None):
    """Locale strings with `{handle}`-style placeholders already filled in.

    Three layers, each overriding the last:

      style   defaults for words a style invented — v7's viewfinder HUD prop,
              say — which no locale file can be expected to know about
      locale  the universal chrome, translated
      deck    the final say, for a brand that words things its own way

    The locale sits *above* the style deliberately: anything genuinely
    translatable belongs in a locale file, and adding it there should win over
    a style's English placeholder rather than lose to it.
    """
    strings = {}
    for layer in (style_strings, load(name), deck_strings):
        if layer:
            strings.update({k: v for k, v in layer.items()
                            if isinstance(v, str) and not k.startswith("_")})

    out = {}
    for key, value in strings.items():
        try:
            out[key] = value.format(**data)
        except (KeyError, IndexError, ValueError):
            out[key] = value           # a stray brace is copy, not a placeholder
    return out
