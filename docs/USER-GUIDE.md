# USER-GUIDE — from YouTube to a posted carousel

This is the full loop for **Scintilla Visiva**: how a handful of YouTube videos
become a researched blog post, and how that post becomes a finished, branded
carousel ready to publish. Four stages:

```
  YouTube sources  ─►  NotebookLM "book"  ─►  blog post  ─►  carousel deck
   (raw material)      (synthesis)            (the article)   (what you post)
```

Stages 1–3 are where you build knowledge and a point of view. Stage 4 is the
pipeline in this repo (`render` → `plates` → `compose`), driven by
`INSTRUCTIONS.md`. The blog post from Stage 3 is the *article* you paste to
Claude to start Stage 4.

The generator ships seven interchangeable **styles** — `v1` (forge glow, the
default), `v2` (frosted editorial panel), `v3` (bold bottom-anchored poster),
`v4` (editorial brutalist — cream blocks + signal red), `v5` (editorial serif —
Fraunces magazine look), `v6` (luminous duotone), and `v7` (kinetic teaching —
viewfinder grid + diagram furniture). They share one `content.json`, so you can
re-skin any deck by re-rendering with a different style and recomposing. All
fonts are bundled in `fonts/`; styles themselves are JSON, so a new look is a new
file — see `docs/STYLES.md`.

---

## Stage 1 — Source YouTube videos

Goal: gather 3–6 strong videos on **one** narrow topic (e.g. "foto d'auto",
"color grading dei ritratti", "setup Sony A7 IV per video"). One topic per deck.

1. **Pick the angle first**, then search for it. A deck answers one question
   ("come fare foto d'auto da pro?"). Don't collect generic content.
2. **Choose authoritative, dense sources** — working photographers/filmmakers,
   tutorials with concrete numbers (focal lengths, shutter speeds, settings),
   not vibes. The more concrete the source, the more concrete the deck.
3. **Prefer videos with transcripts/captions.** NotebookLM ingests a YouTube URL
   directly when captions exist. For each video, copy:
   - the URL,
   - the channel + title (for crediting later),
   - the 3–5 most concrete takeaways while you watch (timestamps help).
4. **Aim for overlap and disagreement.** Two sources that contradict each other
   give you a sharper "segreto" than five that agree.

Output of this stage: a short list of URLs + your rough notes.

---

## Stage 2 — Build the NotebookLM "book"

Goal: turn the raw videos into one synthesised, queryable knowledge base.

1. Open **NotebookLM** → **New notebook** → name it for the topic
   (`foto-auto`, `color-grading-ritratti`).
2. **Add sources:** paste each YouTube URL (Add source → YouTube). Add any
   supporting articles/PDFs you found. 3–6 sources is the sweet spot.
3. Let NotebookLM index, then **generate the synthesis** you'll write from:
   - **Briefing doc** — the one-paragraph-per-theme overview.
   - **Study guide / FAQ** — surfaces the concrete, teachable points.
   - (optional) **Audio Overview** — good for catching the *voice* and the
     punchy framings you can reuse.
4. **Interrogate it** with chat to pull out the deck's spine. Ask, e.g.:
   - "List the 5–8 most concrete, non-obvious techniques across all sources."
   - "For each, give the specific numbers/settings and the one-sentence reason."
   - "Where do the sources disagree?"
   - "What does a beginner get wrong here?"
   - **Always ask NotebookLM to cite the source** for each claim — those
     citations are your fact-check and your crediting.

Output of this stage: a notebook whose chat can hand you titled, sourced,
concrete points. That's the raw ore for the blog post.

---

## Stage 3 — Generate the blog post (the article)

Goal: a single structured post that *is* the article for Stage 4. Use the
NotebookLM synthesis to fill the template below. Keep the mentor voice:
**Italian, "tu", imperative, concrete, zero fluff, no emoji.**

This blog post is intentionally shaped like the deck: an intro, **N numbered
"secrets"** each with a headline + a 1–2 sentence concrete body, and a closing
question. That 1:1 mapping is what makes Stage 4 trivial.

### Blog-post template

```markdown
# <Titolo: la promessa in ≤ 9 parole>
<Sottotitolo: il vincolo o la tensione, ≤ 8 parole>

<Intro: 2–4 frasi. Il problema che il lettore ha adesso, e perché i soliti
consigli non bastano. Diretto, niente giri di parole.>

## I segreti

### 1. <Headline ≤ 6 parole>
<Corpo ≤ 240 caratteri, max 2 frasi, imperativo. Il "cosa" + il numero/azione
concreta + il perché. Cita la fonte fra parentesi se utile.>

### 2. <Headline ≤ 6 parole>
<Corpo ≤ 240 caratteri.>

### 3. <Headline ≤ 6 parole>
<Corpo ≤ 240 caratteri.>

<…fino a 8 segreti max — Instagram arriva a 10 slide = cover + 8 + CTA.>

## Chiudi
<CTA: una domanda che invita un commento, ≤ 14 parole.>

---
Fonti: <canale — titolo — URL>, <…>
```

### Rules that keep Stage 4 painless

- **≤ 8 secrets.** If NotebookLM gave you more, keep the 8 strongest.
- **Every body is concrete and ≤ 240 characters, max 2 sentences, imperative.**
  If you can't say it concretely, it's not a secret — cut it.
- **Headlines ≤ 6 words (~28 characters).** They become slide headlines verbatim.
- **No emoji anywhere.**
- Keep the **Fonti** line — it's your credit + audit trail (not posted, but kept).

---

## Stage 4 — Build the carousel (this repo)

Hand the blog post to Claude as "the article". Claude follows `INSTRUCTIONS.md`:

1. **`content.json`** — the blog template lines up 1:1 with the deck schema, so
   convert it directly:
   ```
   carousel import article.md
   ```
   That fills in the title, subtitle, every secret, the CTA, the badge, the
   folder name and a starting-point image prompt per slide, then reports any
   copy that runs past its length budget. Add the `caption` (see `CAPTION.md`)
   and re-check:
   ```
   carousel check content.json
   ```
   Starting without an article? `carousel new` asks for the same things
   one question at a time.
2. **Render the slides:**
   ```
   carousel render content.json --style v1
   ```
   Creates `decks/TODO-XX-<name>/` with `slide_01…NN.png` (transparent overlay
   layers), `deck.txt`, and `caption.txt`.
3. **Generate the background plates:**
   ```
   carousel plates decks/TODO-XX-<name>
   ```
   Writes the missing `bg_01…NN.png` from the deck's image prompts (needs
   `OPENAI_API_KEY`). Plates that already exist are left alone — pass
   `--only 3,5` to target slides, `--force` only to deliberately replace.
4. **Compose the finals:**
   ```
   carousel compose decks/TODO-XX-<name>
   ```
   Lays each slide over its plate → **`final_01…NN.jpg`** (JPEG, Instagram-
   friendly). These are the files you post. (No plate yet? It falls back to
   charcoal, so the deck still works.)

`carousel build content.json --style v1` runs all three stages in one go.

Want a different look? Re-render into the same folder and recompose — the plates
are reused, not regenerated:
```
carousel render decks/TODO-XX-<name>/content.json --style v2 --out decks/TODO-XX-<name>
carousel compose decks/TODO-XX-<name>
```

To see every style against your own copy before choosing:
```
carousel preview content.json --out preview/
```

Post `final_01 → final_NN` in order. Caption = the deck's `caption.txt`; credit
the sources from the **Fonti** line.

## The loop at a glance

| Stage | Tool | You get |
|------|------|---------|
| 1 Source | YouTube | 3–6 dense videos on one topic + notes |
| 2 Synthesise | NotebookLM | a sourced, queryable "book" |
| 3 Write | Blog template | the article: N secrets + CTA |
| 4 Build | this repo | `final_*.jpg` — the posted carousel |

One topic in, one finished deck out. Repeat per topic.
