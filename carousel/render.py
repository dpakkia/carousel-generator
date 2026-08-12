"""Render a deck to transparent slide overlays.

Orchestration only: resolve the style, ask the engine for the slide images,
write them out alongside deck.txt and caption.txt. Styles never touch the
filesystem and this module never draws.
"""
import os
import re
import glob

from . import deck as deck_io
from . import engine
from .style import Style


def build(content, style, out_folder=None, root=None, prune=True):
    """Render `content` in `style`; return (folder, slide paths, pruned paths).

    style      a Style, or any name/path Style.load accepts
    out_folder render into an existing deck folder (a re-skin: the bg plates
               are reused, nothing is regenerated). Defaults to a new
               auto-numbered TODO-NN-<name> under `root`.
    prune      delete slide_NN.png / final_NN.jpg left over above the current
               slide count, which otherwise survive a deck that lost a secret
               and get posted by mistake.
    """
    if not isinstance(style, Style):
        style = Style.load(style)

    root = root or os.getcwd()
    total = deck_io.total_slides(content)
    folder = deck_io.folder_for(content, root, out_folder)
    os.makedirs(folder, exist_ok=True)

    images = engine.render_deck(style, content)

    paths = []
    for i, im in enumerate(images, start=1):
        p = os.path.join(folder, f"slide_{i:02d}.png")
        im.save(p, "PNG")                       # keep alpha — these are overlay layers
        paths.append(p)

    removed = prune_stale(folder, total) if prune else []

    deck_io.write_deck_txt(folder, content, total)
    deck_io.write_caption(folder, content)
    return folder, paths, removed


def prune_stale(folder, total):
    """Remove slide/final files numbered above `total` (a shrunken deck)."""
    removed = []
    for pattern in ("slide_*.png", "final_*.jpg"):
        for p in glob.glob(os.path.join(folder, pattern)):
            m = re.search(r"_(\d+)\.", os.path.basename(p))
            if m and int(m.group(1)) > total:
                os.remove(p)
                removed.append(p)
    return sorted(removed)
