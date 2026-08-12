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


def resolve(name, data, overrides=None):
    """Locale strings with `{handle}`-style placeholders already filled in.

    Resolved once per slide against the deck's own data, so a style can write
    `$follow` and get "Follow @you" without knowing the language or the handle.
    A deck may override any individual string via its own `strings` block.
    """
    strings = dict(load(name))
    if overrides:
        strings.update({k: v for k, v in overrides.items() if isinstance(v, str)})

    out = {}
    for key, value in strings.items():
        try:
            out[key] = value.format(**data)
        except (KeyError, IndexError, ValueError):
            out[key] = value           # a stray brace is copy, not a placeholder
    return out
