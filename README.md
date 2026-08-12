# Carousel Generator

Generates finished Instagram carousel decks (1080×1350, 4:5) from two JSON files:
**what the deck says** and **how it looks**. Nothing about a look is hardcoded —
palettes, type scales and the drawing recipe for every slide all live in data, so
a new style is a JSON file, not a code change.

```
content.json ──┐
               ├──► slide_NN.png ──┐
styles/v3.json ┘   (transparent)   ├──► final_NN.jpg   ← what you post
                                   │
bg_NN.png ─────────────────────────┘
(generated plates)
```

---

## Quickstart

```bash
pip install -r requirements.txt

# see what looks are available
python -m carousel.cli styles

# render the example deck in the Bold Poster style
python -m carousel.cli render example/content.json --style v3

# flatten the slides over their background plates
python -m carousel.cli compose decks/TODO-01-luce-naturale-ritratti
```

Installing the package puts a `carousel` command on your PATH:

```bash
pip install -e .
carousel render example/content.json --style v5
```

---

## The two files

| File | Owns | You change it when |
|------|------|--------------------|
| `content.json` | title, subtitle, badge, `secrets[]`, `cta_q`, `image_prompts[]`, caption | you write a new deck |
| `carousel/styles/*.json` | palette, fonts, type scale, slide recipes | you design a new look |

They are fully independent: the same content renders in any style, and any style
renders any content. Re-skinning a finished deck costs one command and reuses the
existing background plates.

### content.json

```json
{
  "name": "luce-naturale-ritratti",
  "title": "4 segreti per ritratti in luce naturale",
  "subtitle": "senza flash, senza pannelli",
  "badge": "4 SEGRETI",
  "secrets": [
    ["Cerca l'ombra, non il sole", "Mettiti **all'ombra aperta**: la luce arriva morbida."]
  ],
  "cta_q": "Qual è il posto dove torni sempre a fotografare?",
  "image_prompts": ["<cover>", "<secret 1>", "…", "<cta>"],
  "caption": "<full Instagram caption>"
}
```

`secrets[]` drives the whole deck: **N secrets → N+2 slides** (cover + secrets +
CTA), and `image_prompts[]` maps 1:1 onto those slides. Body copy supports
`**bold**` markup. Run `carousel check content.json` to catch a mismatched
prompt count or badge number before you render.

---

## The three stages

They are deliberately separate commands, because generating plates costs money
and they are art-directed — editing copy must never silently redraw them.

| Stage | Command | Produces |
|-------|---------|----------|
| 1. Render | `carousel render content.json -s v3` | `slide_NN.png` (transparent overlays), `deck.txt`, `caption.txt` |
| 2. Plates | `carousel plates <folder>` | `bg_NN.png` from the image prompts |
| 3. Compose | `carousel compose <folder>` | `final_NN.jpg` — the files you post |

`carousel build content.json -s v3` runs all three.

**`plates` never overwrites an existing plate.** It generates only what's
missing; use `--only 3,5` to target specific slides and `--force` to deliberately
replace. Needs `OPENAI_API_KEY` (see `.env.example`) and `pip install openai`.

Composing writes JPEG, not PNG, on purpose: Instagram's Graph API rejects PNG
uploads with error `2207032`.

---

## The styles

| Name | Label | Character |
|------|-------|-----------|
| `v1` | Forge Glow | Amber bloom on charcoal, giant numerals, brand spark |
| `v2` | Editorial Panel | Frosted translucent card, teal accent, lighter type |
| `v3` | Bold Poster | Oversized bottom-anchored type, ember accent bar |
| `v4` | Editorial Brutalist | Cream blocks in a hard frame, mono masthead, signal red |
| `v5` | Editorial Serif | Fraunces magazine display, hairline rules, deep margins |
| `v6` | Luminous Duotone | Blurred jewel-tone wash that blooms with the photo |
| `v7` | Kinetic Teaching | Viewfinder grid, focus brackets, Space Mono HUD |

Preview them all against your own copy:

```bash
carousel preview content.json --out preview/
```

---

## Writing a style

A style is JSON with five sections — `canvas`, `palette`, `fonts`, `type` and
`slides`. The recipe under `slides` is an ordered list of drawing ops:

```json
{
  "name": "midnight",
  "extends": "_base",
  "palette": { "scrim": [12, 14, 20], "ink": [240, 240, 235], "hot": [255, 92, 60] },
  "type": {
    "title": { "font": "sans", "weight": "Black", "size": 92, "leading": 104, "color": "ink" }
  },
  "slides": {
    "cover": [
      { "op": "vscrim", "top": 40, "bottom": 210 },
      { "op": "glow", "x": 540, "y": 1000, "r": 520, "color": "hot", "alpha": 70 },
      { "op": "measure", "name": "t", "value": "$title", "type": "title" },
      { "op": "cursor", "to": "H - 200 - t_h" },
      { "op": "text", "value": "$title", "type": "title", "x": "MX", "y": { "after": 0 } }
    ]
  }
}
```

Three ideas carry most of the expressiveness:

- **Expressions.** Any number can be arithmetic over the slide's variables:
  `"W - 2 * MX"`, `"H - 96"`. Parsed with `ast` against a whitelist, so a style
  file can do maths but cannot run code.
- **The cursor.** Text ops advance a layout cursor, so the next block sits at
  `{"after": 24}` instead of a magic coordinate. Copy of any length flows.
- **`measure`.** Measures text without drawing it and exposes `<name>_h`,
  `<name>_w` and `<name>_lines` — this is how a panel sizes itself to copy drawn
  after it, or a block anchors to the foot of the slide.

Full schema and the complete op reference: **[docs/STYLES.md](docs/STYLES.md)**.
List the ops any time with `carousel styles --ops`.

---

## Rebranding

Everything brand-specific is in two places:

- `carousel/config.py` — `HANDLE` and `WORDMARK`
- `fonts/` — drop in any TTF; its lowercased filename stem becomes a family name
  you can reference from a style's `fonts` section

Per-deck overrides are also possible: a `content.json` may carry its own
`handle` and `wordmark`.

---

## Layout

```
carousel/
  config.py       canvas size, font paths, brand constants
  style.py        loads style JSON, resolves palette/type/font tokens
  values.py       the expression evaluator
  fonts.py        font registry and variable-axis handling
  typography.py   wrapping, **bold** markup, letter-spacing, drawing runs
  engine.py       runs a style's recipes against a deck
  ops/            the drawing primitives styles call
  deck.py         content.json I/O, validation, folder naming
  render.py       orchestration
  compose.py      slides + plates -> final JPEGs
  images.py       background plate generation
  cli.py          command line
  styles/*.json   the looks
fonts/            bundled TTFs
docs/             style reference and the editorial workflow
example/          a complete content.json
tests/
```

## Tests

```bash
python -m unittest discover tests
```

Covers every shipped style rendering a full deck, the expression sandbox, deck
validation, font resolution, and the stale-slide pruning that stops an orphaned
`slide_09.png` from being posted after a deck loses a secret.
