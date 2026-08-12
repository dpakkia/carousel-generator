"""Canvas geometry, font locations and brand constants.

Everything here is shared by all seven styles. To rebrand the generator,
this is the only file you need to touch: change HANDLE/WORDMARK and drop
your own TTFs into fonts/.
"""
import os

# Repo root = parent of the carousel/ package, so fonts/ resolves whether the
# package is run in place or installed with `pip install -e .`.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "fonts")

# 4:5 — Instagram's max-real-estate ratio (works for Telegram too).
W, H = 1080, 1350

INTER = os.path.join(FONT_DIR, "Inter.ttf")
FRAUNCES = os.path.join(FONT_DIR, "Fraunces.ttf")
MONO_R = os.path.join(FONT_DIR, "SpaceMono-Regular.ttf")
MONO_B = os.path.join(FONT_DIR, "SpaceMono-Bold.ttf")

# Last-resort fallback if a bundled font fails to load (Linux path; harmless
# when absent — PIL raises and the caller keeps its own fallback).
DEJAVU = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
DEJAVU_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

HANDLE = "@scintillavisiva"
WORDMARK = "SCINTILLA VISIVA"

# The house look for generated background plates. Every scaffolded image prompt
# carries this clause, which is what keeps a deck visually coherent slide to
# slide — rewrite it here to re-art-direct every future deck at once.
IMAGE_STYLE = ("Cinematic and moody, deep charcoal near-black, warm amber-gold "
               "forge glow, a subtle cool-teal accent, fine film grain, "
               "premium editorial photography.")

# Brand ground. Also the fallback plate colour in compose.py when a slide has
# no bg_NN.png behind it.
CHARCOAL = (21, 23, 28)
