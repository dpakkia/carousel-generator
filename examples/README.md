# Examples

## `starter/`

A complete `content.json` in English, with the brand fields set to placeholders.
Copy it, replace the copy and the handle, and render:

```bash
carousel render examples/starter/content.json --style v3
```

It is also what the seven-style preview in the main README is rendered from, and
what `carousel preview` is most useful against while you design a style.

## `scintilla-visiva/`

The real deck and workflow this tool was built for: an Italian photography and
video page. Useful as a worked example of three things the schema alone does not
show you.

- **`content.json`** — a finished deck in Italian, with `locale`, `handle` and
  `wordmark` set, `**bold**` markup used the way it is meant to be (one or two
  spans per body), and a full caption.
- **`USER-GUIDE.md`** — the whole editorial loop that feeds the generator:
  sourcing material, synthesising it, and writing it up in the template that
  `carousel import` reads. If you want a repeatable way to *fill* the deck
  rather than just render it, start here.
- **`INSTRUCTIONS.md`** — the brief handed to an AI assistant to turn an article
  into a `content.json`, including the length budgets and the house rules for
  image prompts. A good starting point for your own brief.
- **`CAPTION.md`** — how the post caption is structured, separately from the
  slides.

These are one brand's conventions, not requirements. The voice is Italian and
the deck format is "N secrets"; nothing in the tool depends on either.
