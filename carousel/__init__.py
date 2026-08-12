"""Carousel generator — data-driven Instagram carousel slides.

A deck's copy lives in content.json; a deck's look lives in a style JSON under
carousel/styles/. Rendering pairs the two:

    from carousel import deck, render
    content = deck.load("content.json")
    folder, slides, _ = render.build(content, "v1")

Styles are data all the way down — palette, type scale, and the ordered drawing
recipe for each slide kind. Adding a look means writing JSON, not Python.
"""
from .style import Style, available as available_styles
from . import deck, render, engine, ops

__all__ = ["Style", "available_styles", "deck", "render", "engine", "ops"]
__version__ = "1.0.0"
