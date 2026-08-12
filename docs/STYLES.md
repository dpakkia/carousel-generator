# Writing a style

A style is a JSON document describing a look completely: its colours, its
typefaces, its type scale, and the ordered drawing recipe for each of the three
slide kinds. No part of a look lives in Python.

```
carousel/styles/
  _base.json   shared ground (leading underscore = not listed as a style)
  v1.json … v7.json
```

Create a new one by dropping a file in that directory. It appears in
`carousel styles` immediately.

---

## Document structure

```json
{
  "name": "midnight",
  "label": "Midnight Press",
  "extends": "_base",
  "meta": { "description": "…", "tags": ["dark"] },

  "image_style": "the photography this look sits on",

  "canvas":  { "width": 1080, "height": 1350, "margin": 96 },
  "palette": { "scrim": [12, 14, 20], "ink": "#F0F0EB" },
  "fonts":   { "sans": { "family": "inter" } },
  "vars":    { "TXTW": "W - 2 * MX" },
  "type":    { "title": { "font": "sans", "weight": "Black", "size": 92,
                          "leading": 104, "color": "ink" } },
  "variants": { "warm": { "accent": [232, 150, 60] } },

  "slides": { "cover": [ … ], "secret": [ … ], "cta": [ … ] }
}
```

### extends

Pulls in another style and merges over it. `canvas`, `palette`, `fonts`, `type`,
`vars`, `slides` and `meta` merge key by key; everything else is replaced. Use it
to share brand furniture across a family of looks.

### canvas

`width`, `height`, `margin`. The margin is what recipes measure from — it is
available in every expression as `MX`.

### palette

Named colours. A recipe refers to `"amber"`, never to an RGB triple. Values may
be `[r, g, b]`, `[r, g, b, a]` or `"#RRGGBB"`. A name may also point at another
name.

Referencing a colour that does not exist is an error naming the palette, rather
than a slide that silently renders in black.

### fonts

Named roles bound to families discovered in `fonts/`. Any TTF dropped there is
available under its lowercased filename stem: `Inter.ttf` → `inter`,
`SpaceMono-Bold.ttf` → family `spacemono`, variant `bold`.

```json
"fonts": {
  "sans":  { "family": "inter" },
  "mono":  { "family": "spacemono" },
  "serif": { "family": "fraunces", "axes": { "wght": 620 } }
}
```

| Key | Meaning |
|-----|---------|
| `family` | file stem in `fonts/` |
| `weight` | named instance of a variable font: `"Regular"`, `"Bold"`, `"Black"` |
| `variant` | file suffix to prefer: `"bold"` picks `SpaceMono-Bold.ttf` |
| `axes` | explicit variable axes: `{ "wght": 620, "opsz": 72 }` |

Axes accept OpenType tags (`wght`, `opsz`, `wdth`, `slnt`) or full axis names.
When you drive axes but leave `opsz` out, optical size follows the type size —
which is what an optical-size axis is for.

### type

The type scale. Each entry names a font role plus its metrics; recipes then refer
to the entry by name.

| Key | Meaning |
|-----|---------|
| `font` | a role from `fonts` |
| `size` | px |
| `leading` | line height in px; also how far the cursor advances |
| `color` | palette name, or `null` for hollow type |
| `tracking` | letter-spacing in px |
| `weight` / `variant` / `axes` | per-style font overrides |
| `bold_font` | the role `**bold**` runs switch to |
| `stroke_width`, `stroke_color` | outline; pair with `"color": null` |

Without `bold_font`, bold runs resolve automatically: two steps up the weight
ladder for named weights, `+200 wght` for axis-driven fonts, the `-Bold` file for
families that ship one.

### image_style

The art direction for the background plates this look sits on. A brutalist look
and a duotone look want different photography behind them, so the clause travels
with the style rather than with the install:

```json
"image_style": "Stark documentary photography, near-monochrome with one warm accent, hard light, raw texture."
```

It is appended to every prompt `carousel new`, `import` and `prompts` scaffold,
alongside a negative-space clause chosen per slide kind. Nearest wins: a deck's
own `image_style` overrides the style's, which overrides `IMAGE_STYLE` in
`carousel/config.py`.

Prompts are stored in `content.json`, so re-skinning a deck does not re-derive
them. `carousel prompts <deck> --style vN` rewrites them; existing plates on
disk are never touched.

### variants

Optional palette overlays. A deck picks one with its own `"palette": "teal-indigo"`
field; otherwise the deck's `name` selects one deterministically, so a given deck
always renders the same colours while a run of decks cycles through the family.
`variant_order` fixes the rotation order.

---

## Slide recipes

`slides` holds three ordered lists: `cover`, `secret`, `cta`. The `secret` recipe
runs once per secret. Each entry is an op:

```json
{ "op": "glow", "x": 250, "y": 230, "r": 360, "color": "teal", "alpha": 26 }
```

`note` is ignored by the renderer — use it to explain intent. `when` guards an op
with an expression: `{"op": "rule", "when": "index > 1", …}`.

### Values

Any numeric field accepts:

| Form | Meaning |
|------|---------|
| `560` | a literal |
| `"W - 2 * MX"` | arithmetic over the slide's variables |
| `{"after": 24}` | 24px below where the previous text block ended |
| `{"of": "H", "mul": 0.5, "add": 20}` | a fraction of a variable |

Variables always available: `W`, `H`, `MX`/`MARGIN`, `CX`, `CY`, `cursor`, plus
the numeric slots `slide`, `index`, `count`, `total`, plus anything in `vars` and
anything a `measure` op has produced. `min`, `max`, `abs`, `round` and `int` are
callable; nothing else is.

### Text slots

`value` may be a literal, `"$field"` for a deck field verbatim (keeping its
`**bold**` markup), or a `"{field}"` template with format specs.

**From the deck's copy:**
`$title` · `$subtitle` · `$badge` · `$headline` · `$body` · `$question`

**From the brand:** `$handle` · `$wordmark` — empty when the deck sets neither,
and a text op with nothing to draw simply draws nothing, so an unbranded deck
renders cleanly rather than printing a placeholder.

**Counters:** `{index:02d}` · `{count:02d}` · `{slide}` · `{total}`

**Chrome, from the deck's language** (see below):
`$scroll` · `$scroll_caps` · `$scroll_plain` · `$continue` · `$save` ·
`$save_caps` · `$follow` · `$follow_caps` · `$section` · `{figure}` ·
`{number_abbr}` · `$focus_lock`

### Chrome and language

The fixed words a style draws around the copy — "Swipe →", "Follow @you", the
label above each point — are neither look nor content, so they live in
`carousel/locales/<lang>.json` and a recipe references them by name:

```json
{ "op": "text", "value": "$scroll", "type": "cue", "align": "right" }
```

**Never write those words as literals in a recipe.** A hardcoded "Swipe →" is
invisible to translation and silently pins your style to one language; a test
fails the build if one appears. Everything else — a deck's title, an arrow
glyph, a format string like `4:5 · 1080×1350` — is fine as a literal.

A deck chooses its language with `"locale": "it"`, and can override any single
string without a new locale file:

```json
{ "locale": "en", "strings": { "save": "Pin this for later" } }
```

Strings may interpolate the brand: `"follow": "Follow {handle}"` is resolved
before the recipe sees it. To add a language, copy `en.json`, translate the
values, and keep every key.

### Flow

Text and pill ops advance a **cursor** to the bottom of what they drew, unless
given `"advance": false`. The next block then positions itself relatively, so a
long title pushes the subtitle down instead of colliding with it.

`measure` computes text metrics without drawing, publishing `<name>_h`,
`<name>_w` and `<name>_lines`. That is how a panel wraps itself around copy drawn
later, and how a block anchors to the foot of a slide:

```json
{ "op": "measure", "name": "t", "value": "$title", "type": "title" },
{ "op": "cursor",  "to": "BASE - (60 + t_h)" },
{ "op": "panel",   "box": ["MX", "cursor", "W - MX", "BASE"] },
{ "op": "text",    "value": "$title", "type": "title", "y": { "after": 60 } }
```

---

## Op reference

Run `carousel styles --ops` for the live list.

### Light and shade

| Op | Key parameters | Draws |
|----|----------------|-------|
| `vscrim` | `top`, `bottom`, `color` | vertical alpha ramp — the legibility floor |
| `hscrim` | `left`, `right`, `color` | horizontal alpha ramp |
| `rscrim` | `x`, `y`, `r`, `alpha`, `color` | soft radial darkening |
| `glow` | `x`, `y`, `r`, `color`, `alpha`, `spread` | blurred disc of light |
| `wash` | `blobs[]`, `strength`, `resolution`, `blur` | painterly duotone gradient |
| `panel` | `box`, `color`, `alpha`, `radius`, `blur`, `outline` | translucent card behind copy |

`wash` blobs are `{x, y, r, color, alpha}` in normal slide coordinates. Rendering
happens at `resolution` (default 0.2) and upscales, which smooths the gradient
and removes banding.

### Structure

| Op | Key parameters |
|----|----------------|
| `rect` | `box`, `fill`, `outline`, `width`, `radius` |
| `frame` | `inset`, `color`, `width` |
| `line` | `x1`, `y1`, `x2`, `y2`, `color`, `width`, `alpha` |
| `rule` | `x`, `y`, `length` or `to`, `color`, `width`, `alpha` |
| `ellipse` | `x`, `y`, `r`, `fill`, `outline` |
| `polygon` | `x`, `y`, `r`, `sides`, `rotation`, `fill` |
| `spark` | `x`, `y`, `r`, `color`, `pinch` |
| `sparks` | `at[]`, `color` |
| `grid` | `divisions`, `color`, `alpha`, `intersections` |
| `corner_marks` | `inset`, `length`, `color`, `alpha` |
| `bracket` | `box`, `length`, `color`, `alpha` |
| `reticle` | `x`, `y`, `r`, `gap`, `tail`, `dot` |
| `ticks` | `x`, `to`, `y`, `count`, `length`, `minor` |

### Type

| Op | Key parameters |
|----|----------------|
| `text` | `value`, `type`, `x`, `y`, `width`, `align`, `advance`, `uppercase`, `max_lines`, `stroke_width` |
| `pill` | `value`, `type`, `x`, `y`, `fill`, `outline`, `radius`, `pad_x`, `pad_y`, `height` |
| `measure` | `value`, `type`, `name`, `width` |
| `cursor` | `to`, `by` |

`align` is `left`, `center` or `right`, resolved inside the column given by
`width` starting at `x`.

---

## Adding an op

Ops are ordinary functions. Write one in `carousel/ops/`, decorate it, and every
style can call it:

```python
from . import op

@op("halo")
def halo(ctx, x=None, y=None, r=100, color="accent", **_):
    """A ring of light."""
    cx = ctx.num(x, ctx.size[0] / 2)
    cy = ctx.num(y, ctx.size[1] / 2)
    rad = ctx.num(r)
    ctx.draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad],
                     outline=ctx.color(color), width=3)
```

The context gives you `ctx.num()` for expressions, `ctx.color()` for palette
lookups, `ctx.box()` for boxes, `ctx.text_value()` for deck slots, `ctx.draw`
and `ctx.img`, and `ctx.set_cursor()` if the op affects flow. Always accept
`**_` so unknown keys (like `note`) pass harmlessly.
