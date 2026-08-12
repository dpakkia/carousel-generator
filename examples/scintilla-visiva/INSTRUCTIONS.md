# INSTRUCTIONS.md — Scintilla Visiva carousel content

## Purpose

This repo renders branded 1080×1350 Instagram/Telegram carousel slides for
**Scintilla Visiva** — an Italian photography/video education page with a mentor
voice: direct, concrete, a little provocative, zero fluff.

A deck is two JSON files: **`content.json`** (what it says) and a **style**
(how it looks). Seven styles ship, all reading the same `content.json`:

| Style | Look |
|-------|------|
| `v1` | Forge Glow — charcoal ground, amber spark, teal accent (the default) |
| `v2` | Editorial Panel — copy on a frosted translucent card, teal-led |
| `v3` | Bold Poster — oversized bottom-anchored type, ember accent |
| `v4` | Editorial Brutalist — cream blocks, signal-red marker, mono labels |
| `v5` | Editorial Serif — Fraunces magazine serif, hairline rules, negative space |
| `v6` | Luminous Duotone — painterly jewel-tone gradient (per-deck palette) |
| `v7` | Kinetic Teaching — viewfinder grid, focus brackets, mono diagram furniture |

Fonts are bundled in `fonts/`. To re-skin an existing deck without making a new
folder, render into it with `--out` and recompose.

## Style rotation across decks

Decks rotate through the styles so the feed never repeats a look back-to-back.
**`TODO-01` is `v1`.** From index 2 onward the cycle is:

```
v2, v3, v4, v5, v6, v7, v1   →   style(N) = CYCLE[(N - 2) % 7]
```

So `02→v2, 03→v3, 04→v4, 05→v5, 06→v6, 07→v7, 08→v1, 09→v2, 10→v3, 11→v4, …`.

This rule is built in — use `--style auto` and the deck number decides:

```
carousel render content.json --style auto
```

It reads the number from the target folder when re-rendering one, or from the
next index for a new deck, and prints which style it chose. `carousel styles
--rotation` shows the mapping.

To re-skin an existing deck, render into its folder and recompose — the bg
plates are reused, never regenerated:

```
carousel render decks/TODO-XX-<name>/content.json --style v4 --out decks/TODO-XX-<name>
carousel compose decks/TODO-XX-<name>
```

When I paste an **article**, you:

1. Decide a short folder **name** and the deck content.
2. Write `content.json`.
3. Write one image-gen prompt per slide (inside `content.json`).
4. Run the generator — it creates the output folder and renders everything.

## When I give you an article

1. **Read `content.json` in this folder first** for the schema, and the style you are
   about to use (`carousel/styles/vN.json`) for its type sizes — respect the
   length budgets below so no text overflows a slide. All seven styles share the
   same schema and budgets. `carousel check <file>` validates a deck.
2. Write `content.json` → Steps A + B.
3. Run it → Step C.

## Step A — `content.json` (the deck)

Write `content.json` in the repo root with this shape:

```json
{
  "name": "<kebab folder name>",
  "title": "<cover title>",
  "subtitle": "<cover subtitle>",
  "badge": "<N> SEGRETI",
  "secrets": [["<headline>", "<body>"]],
  "cta_q": "<CTA question>",
  "image_prompts": ["<cover>", "<secret 01>", "<cta>"],
  "caption": "<full Instagram caption — see CAPTION.md>"
}
```

Also write the **`caption`** field (the post copy). Follow `CAPTION.md` for its
structure, voice, and length; the generator saves it to `caption.txt` in the
deck folder.

Rules:

- **Language & tone:** Italian, dare del "tu", imperativo, mentor voice,
  concrete, zero fluff. **No emoji anywhere.**
- **Secrets = the article's secrets.** Use them all; if more than 8, keep the 8
  strongest (Instagram caps at 10 slides = cover + 8 + CTA).
- **`badge`** = secret count + `" SEGRETI"` (e.g. `"5 SEGRETI"`).
- **Length budgets** — keep within these so text fits the rendered slides, and
  sanity-check against the font sizes in the script:
  - `title` ≤ 9 words (renders large, ~3 lines max).
  - `subtitle` ≤ 8 words, single line.
  - each `headline` ≤ 6 words (~28 characters).
  - each `body` ≤ 240 characters, max 2 sentences, imperative.
  - `cta_q` = a question that invites a comment, ≤ 14 words.
- **`name`:** short, lowercase, kebab-case (`foto-auto-pro`, `sony-a7iv-setup`,
  `color-grading`). **You decide it from the article.** Do NOT add `TODO-` or a
  number — the renderer prepends `TODO-` and an auto-incrementing index itself.
- **Valid JSON:** double-quoted strings; apostrophes (`l'`, `dell'`) and
  en-dashes (`–`) are fine; avoid raw `"` inside values.

## Step B — `image_prompts` (one per slide, in order)

Fill the `image_prompts` array in slide order — Slide 01 = cover, Slides
02…(N+1) = the secrets in order, final = CTA. These are **optional dark
background plates** (the script lays bone-colored text on flat charcoal; these
sit behind a slide if I choose), so each must leave room for text.

Every prompt:

- **Style (identical across the deck, for cohesion):** cinematic, moody, deep
  charcoal near-black, warm amber-gold forge-glow, a subtle cool-teal accent,
  fine film grain, premium/editorial.
- **Format:** 1080×1350 portrait (4:5).
- **Background-safe:** very dark, large near-black negative space where the text
  sits — lower half (cover), upper-left/left column (secrets), calm center
  (CTA). Low contrast, nothing busy.
- **Topical** to that slide — derive from the title for the cover, and from each
  secret's headline/body. The CTA returns to a spark / ember / forge motif.
- **Ends exactly with:** `No text, no letters, no watermark.`

## Step C — render

Render with the style this deck's index calls for:

```
carousel render content.json --style v1
```

It reads `content.json`, scans existing `TODO-*` folders and takes the next index
(one higher than the latest), creates `decks/TODO-XX-<name>/`, renders
`slide_01…NN.png` into it, and writes `deck.txt` (the copy + the image prompts)
and `caption.txt`. The slides are **transparent overlay layers** (a soft charcoal
scrim sits behind the text) — they are meant to be laid over the background
plates, not posted on their own. Report the created folder and the slide paths.

If the deck lost a secret, any orphaned `slide_NN.png` / `final_NN.jpg` above the
new slide count is removed automatically and reported.

## Step D — backgrounds, then compose

```
carousel plates  decks/TODO-XX-<name>     # bg_01…NN.png from the image prompts
carousel compose decks/TODO-XX-<name>     # final_01…NN.jpg = plate + slide
```

`plates` **only generates plates that do not exist yet** — an existing
`bg_03.png` is never overwritten. Use `--only 3,5` to target specific slides and
`--force` only when deliberately replacing one.

`compose` lays each `slide_NN.png` over its `bg_NN.png` and writes `final_NN.jpg`
(JPEG — Instagram's Graph API rejects PNG with error `2207032`) — **these are the
files to post.** A slide with no matching plate falls back to the brand charcoal
ground, so the deck always renders.

When only a background changed, recompose only; there is no need to re-render.

## What to return, every time

1. The chosen `name`, and confirmation that `content.json` was written.
2. The created folder `TODO-XX-<name>/` and the rendered `slide_*.png` paths.
3. A note that `deck.txt` (copy + image prompts) is in that folder.
4. After Step D: the `final_*.jpg` paths — the ones to post.
