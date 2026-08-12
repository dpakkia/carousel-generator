# CAPTION.md — the Instagram/Telegram caption for each deck

Every deck ships a `caption.txt` in its `TODO-XX-<name>/` folder: the post copy
that goes under the carousel. Claude writes it as the `"caption"` field in
`content.json`; the renderer saves it to `caption.txt` at render time.

## Voice (same as the deck)

Italian, dare del "tu", imperative, mentor voice — concrete, a little
provocative, zero fluff. **No emoji anywhere.** Plain text only (no markdown,
no bullet characters) — it gets pasted straight into Instagram.

## Structure (in this order)

1. **Hook** — one line, ≤ ~12 words. A provocative restatement of the cover
   promise that stops the scroll. Often a sharp claim or a question.
2. **Body** — 2–3 short paragraphs (≈ 4–7 lines total). Name the mistake most
   people make, say why it matters, and tell them what the carousel gives them.
   Tease one or two secrets — do **not** list them all (the slides do that).
3. **Action** — one line: tell them to **save** the carousel and to **swipe**
   for all N secrets. e.g. `Salva il carosello e scorri per tutti i N segreti.`
4. **CTA question** — invite a comment. Reuse `cta_q` or sharpen it.
5. **Follow** — `Segui @scintillavisiva per fotografia e video senza fronzoli.`
   (adapt the tail to the deck's domain: "per il color grading", "per l'audio…").
6. **Hashtags** — one block on the last line(s): **10–15** tags, lowercase, no
   emoji. Mix Italian + English, broad + niche + gear/topic specific. Always end
   with `#scintillavisiva`. No banned/spammy or unrelated tags.

## Length

Aim **600–1100 characters** before the hashtags (Instagram hard-caps at 2200).
Short paragraphs separated by a blank line. Keep it skimmable.

## How it's wired

- Add `"caption"` to `content.json` as a single string (use `\n` for line breaks,
  `\n\n` between paragraphs).
- The renderer writes it verbatim to `decks/TODO-XX-<name>/caption.txt`.
- If `"caption"` is missing/empty, no `caption.txt` is written.

---

## Example 1 — `foto-auto-pro`

```
La tua auto è uno specchio. E nessuno te lo ha mai detto.

Per foto d'auto da professionista non servono obiettivi da 3.000 euro. Serve
sapere dove guarda la luce, come gira una ruota e perché un filtro da pochi euro
cambia tutto.

La maggior parte degli scatti amatoriali muore per tre errori che puoi correggere
oggi. In questo carosello trovi i 5 segreti che separano una foto piatta da una da
copertina: dal polarizzatore alla regola 1:1 per i rolling shot.

Salva il carosello prima del prossimo shooting e scorri per tutti i 5 segreti.

Quale di questi smetti di sbagliare dal prossimo shooting?

Segui @scintillavisiva per fotografia e video senza fronzoli.

#fotografiaauto #carphotography #automotivephotography #fotografiaitalia #fotografodiauto #cpl #rollingshot #fototecnica #fotografiacreativa #cargram #automotive #photographytips #scintillavisiva
```

## Example 2 — `sony-a7iv-setup`

```
Un milione di combinazioni di menu. E tu ne usi cinque.

La Sony A7IV non è il problema. Il problema è il labirinto di impostazioni tra te
e lo scatto. Smetti di inseguire la nitidezza perfetta e configura la macchina
come un professionista: otturatore giusto, sensore protetto, ISO sotto controllo,
selezione già in camera.

Quando non pensi più a quale tasto premere, la A7IV diventa un'estensione del tuo
occhio. In questo carosello trovi i 7 segreti per arrivarci, dal trucco
dell'Aperture Priority al Teal and Orange che fa saltare fuori il soggetto.

Salva questo setup e scorri per tutti i 7 segreti.

Pixel perfetti o battito della tua storia: cosa scegli al prossimo scatto?

Segui @scintillavisiva per fotografia e video senza fronzoli.

#sonya7iv #sonyalpha #sonyalphaitalia #mirrorless #fotografiaitalia #setupfotografico #fototecnica #tealandorange #streetphotography #sonyphotography #fotografiadigitale #photographytips #scintillavisiva
```
