# Contributing

The point of this project is that the interesting work happens in **data**, not
in Python. Before writing code, check whether what you want is a new style file
or a new locale — most additions are.

Working with an AI agent? [AGENTS.md](AGENTS.md) states what it is expected to
do and the standard each job is held to.

## Setup

```bash
pip install -e .
python -m unittest discover tests
```

No linter config, no CI, no pre-commit hooks. Match the surrounding style:
four-space indent, docstrings that say *why* rather than restating the signature,
comments only where the reason isn't obvious from the code.

## Adding a style

Write a JSON file in `carousel/styles/` and check it:

```bash
carousel styles --check carousel/styles/yours.json
carousel preview examples/starter/content.json --styles yours
```

Read [docs/STYLES.md](docs/STYLES.md) first — it is the full schema and op
reference. Two rules that keep a style usable by other people:

- **No literal chrome.** Words like "Swipe →" or "Follow @you" belong in
  `carousel/locales/`, referenced as `$scroll`, `$follow`. A test fails if a
  recipe hardcodes them, because a hardcoded string is invisible to translation.
- **No fixed coordinates for text that can grow.** Use `measure` and the layout
  cursor so a long title pushes what follows down instead of colliding with it.

## Adding a language

Copy `carousel/locales/en.json`, translate the values, keep every key. A test
checks that all locale files carry the same keys, so a missing one fails loudly
rather than rendering an English word into an otherwise translated slide.

## Adding an op

An op is a decorated function in `carousel/ops/`. Keep them small and general —
an op should describe a *drawing primitive*, not one style's decoration:

```python
@op("halo")
def halo(ctx, x=None, y=None, r=100, color="accent", **_):
    """A ring of light."""
    ...
```

Always accept `**_` so unknown keys (like `note`) pass through harmlessly, and
resolve every numeric parameter through `ctx.num()` so expressions work.
Document it in the op reference table in `docs/STYLES.md`.

## Fonts

Only add a font you are allowed to redistribute, and record its licence in
`fonts/README.md`. Most commercial font licences forbid bundling.

## Tests

New behaviour needs a test. Aim them at what would actually break a deck —
copy that overflows a slide, a style that renders blank, a locale key that went
missing, a stale slide surviving a re-render — rather than at implementation
detail.

```bash
python -m unittest discover tests
```

## Pull requests

Say what changed and why in the description. If it changes rendered output,
include a before/after image — `carousel preview` produces one in a command.
