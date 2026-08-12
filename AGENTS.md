# AGENTS.md

Notes for an AI agent working in this repository.

This tool renders Instagram carousels from two JSON files: a deck's copy and a
style. It is deliberately **incomplete** — it handles everything deterministic
(layout, wrapping, validation, composition) and leaves everything requiring
judgement to you. This file is the list of what "requiring judgement" means, and
the standard each of those jobs is held to.

Read `README.md` first for the pipeline, and `docs/STYLES.md` before touching a
style. Run the tests before and after any change:

```bash
python -m unittest discover tests
```

---

## The division of labour

The tool guarantees a deck **renders**. It cannot tell you the deck is **good**.

| The tool handles | You handle |
|---|---|
| Wrapping, alignment, flow, `**bold**` markup | Whether the sentence is worth reading |
| Length budgets, prompt/badge count validation | Whether the headline lands |
| Slide chrome in the deck's language | The deck's copy, in any language |
| Appending style + negative-space clauses to prompts | The *subject* of every image prompt |
| Protecting existing plates, pruning stale slides | Deciding a deck needs re-shooting |
| Rendering pixels | **Looking at them** |

That last row is the one most often skipped. Nothing in this repository inspects
the rendered image. Budgets are a pre-render proxy on character counts: copy can
pass every check and still collide with a busy plate. If you changed anything
visual and did not look at the output, you have not finished.

---

## Task: design a style from a brand

The flagship hand-off. A style is pure JSON — palette, type scale, and an
ordered drawing recipe per slide kind — so this needs no Python.

1. Read `docs/STYLES.md` in full, then two shipped styles as worked examples.
   Pick ones near the target: `v4` for structural/brutalist, `v5` for
   editorial/serif, `v6` for colour-led, `v7` for technical.
2. If the brand needs its own typefaces, put the files in `fonts/` first. The
   lowercased filename stem becomes the family name.
3. Write `carousel/styles/<name>.json`.
4. Validate, then **look**:
   ```bash
   carousel styles --check carousel/styles/<name>.json
   carousel preview examples/starter/content.json --styles <name>
   ```
   `--check` renders every slide kind and names the failing step precisely
   (`midnight · cover slide · step 7 (op 'text'): unknown colour 'chartreuse'`).
   `preview` gives you a contact sheet to open and judge.
5. Iterate until the type sits well with both short and long copy. Test with a
   deck whose titles wrap to three lines — most layout bugs only appear there.

Requirements for a style to be considered done:

- **No literal chrome.** Words like "Swipe →" or "Follow @you" come from
  `carousel/locales/`, referenced as `$scroll`, `$follow`. A test fails the
  build if a recipe hardcodes one, because a literal is invisible to
  translation.
- **No fixed coordinates for text that can grow.** Use `measure` and the layout
  cursor so a long title pushes what follows down instead of overlapping it.
- **Colours by palette name**, never raw RGB inside a recipe.
- **Set `image_style`** — the photography this look sits on. A brutalist style
  and a duotone style want different plates; that is a property of the look.
- **Renders in every shipped locale**, not just the one you were thinking in.

---

**Picking the style.** If the brand rotates looks across a series, use
`--style auto` rather than choosing by hand — it derives the style from the deck
number and prints what it picked. `carousel styles --rotation` shows the mapping.

## Task: write deck copy

The schema is in `README.md`; `examples/scintilla-visiva/INSTRUCTIONS.md` is a
worked example of a brief for exactly this job, for one specific brand.

Budgets — enforced as warnings, not errors, because they are about crowding:

| Field | Budget |
|---|---|
| `title` | 9 words |
| `subtitle` | 8 words |
| each headline | 6 words |
| each body | 240 characters |
| `cta_q` | 14 words |
| `secrets` | 8 max (Instagram caps the carousel at 10 slides) |

Beyond fitting:

- **One idea per point.** If a body needs "and also", it is two points or one
  weaker one.
- **Concrete beats clever.** A number, a setting, a specific action. If it
  cannot be said concretely it probably is not worth a slide.
- **The CTA must parse and be true.** Check the question actually makes sense
  as asked — a question that reads backwards is worse than a bland one.
- **Bold one or two spans per body**, on the terms that carry the takeaway.
  More than that and none of it reads as emphasis.
- Finish with `carousel check content.json`.

Match the language and register of the deck you were given. Do not quietly
translate copy into English.

---

## Task: write image prompt subjects

`carousel new`, `import` and `prompts` scaffold one prompt per slide, but **the
subject clause is a placeholder**: it is the slide's own copy pasted in.

```
Look for shade, not sun — Step into open shade, a porch, the north side of a
wall… Stark documentary photography, near-monochrome… No text, no watermark.
```

That is a sentence, not a photograph. Your job is to replace the subject with an
actual scene, and only the subject:

- **Keep the style clause and the negative-space clause.** They are what keeps
  the deck visually coherent and leaves room for the type. They are appended
  automatically from the style's `image_style`.
- **Describe a scene, not the lesson.** "Soft window light raking across a
  plaster wall, deep shadow at frame left" — not "how to use natural light".
- **Respect where the text goes.** Cover copy sits low, secret copy sits left,
  the CTA sits centred. The scaffold already says so; do not fight it.
- **Keep the deck coherent.** Same world, same light, same era across slides.
- Never ask for text, logos or watermarks in an image.

---

## Task: edit an existing deck

1. Load the deck's own `content.json` — never a different deck's.
2. Propose changes for review before writing. For a full pass, cover every
   element rather than leaving most untouched.
3. Preserve `**bold**` markup and the deck's `locale`, `handle`, `wordmark`.
4. Re-validate and re-render.

**Changing the number or order of points misaligns the background plates.**
Plates are named by slide position, so inserting a point mid-deck leaves every
later plate behind the wrong copy — and `check` stays quiet about it, because
nothing in a JSON file can see that plate 4 was shot for what is now slide 5.

Repair it with `carousel reindex <folder>`, **before re-rendering** — it reads
`deck.txt`, which a render overwrites. Preview with `--dry-run` first. It
handles reorders as well as shifts, never overwrites a plate, and sets the plate
of a deleted point aside as `orphan_NN.png`.

Do not regenerate the whole set to paper over a shift. That spends money to
destroy art direction you already had.

---

## Hard rules

- **Never regenerate a background plate that already exists** unless explicitly
  asked. They cost money and are art-directed. `carousel plates` refuses by
  default; do not reach for `--force` to save yourself a thought. If plates look
  wrong after an edit, suspect misalignment and run `carousel reindex` before
  concluding they need re-shooting.
- **Never hardcode slide chrome in a style.** It goes in `carousel/locales/`.
- **Never edit `deck.txt`.** It is regenerated from `content.json` on every
  render. Edit the source.
- **Never rewrite a style JSON with `json.dump`.** The recipes are hand-laid-out
  for reading; a naive dump explodes them from ~700 lines to ~3300. Edit
  textually, or by hand.
- **Never commit `.env`** or any key. `.env.example` is the template.
- **Compose to JPEG, not PNG.** Instagram's Graph API rejects PNG uploads with
  error `2207032`.

---

## Working on the code itself

`CONTRIBUTING.md` has the detail. In short:

- Most additions are **data, not code** — a style file or a locale file. Check
  which one you actually need before opening a `.py`.
- An op is a small decorated function in `carousel/ops/`. It should be a general
  drawing primitive, not one style's decoration. Accept `**_`, resolve numbers
  through `ctx.num()`, and document it in the op table in `docs/STYLES.md`.
- A new language is a copy of `carousel/locales/en.json` with every key kept. A
  test fails if a locale file gains or loses keys.
- Docstrings say *why*. The code already says what.
- New behaviour needs a test, aimed at what would break a deck — copy that
  overflows, a style that renders blank, a stale slide surviving a re-render.

`README.md` and `README.it.md` are kept at parity: same sections, same examples.
If you change one, change the other.
