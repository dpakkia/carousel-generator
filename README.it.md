# Carousel Generator

[English](README.md) · **Italiano**

Trasforma un testo in un carosello Instagram finito — 1080×1350, copertina più
una slide per punto più la call to action, pronto da pubblicare.

Un deck sono due file JSON: **cosa dice** e **come appare**. Nessun aspetto
grafico è scritto nel codice: palette, scala tipografica e la ricetta di disegno
di ogni slide vivono nei dati, quindi uno stile nuovo è un file JSON, non una
modifica al codice. Vale anche per lingua e brand: le parole che uno stile
disegna intorno al tuo testo stanno in un file di lingua, e handle e wordmark
arrivano dal deck.

```
content.json ──┐
               ├──► slide_NN.png ──┐
styles/v3.json ┘   (trasparenti)   ├──► final_NN.jpg   ← quello che pubblichi
                                   │
bg_NN.png ─────────────────────────┘
(sfondi generati)
```

Sono inclusi sette stili. Lo stesso testo, reso da ciascuno:

![I sette stili](docs/styles.jpg)

---

## Installazione

Per generare le slide bastano Python 3.9+ e Pillow.

```bash
pip install -r requirements.txt
python -m carousel.cli styles
```

Installando il pacchetto ottieni il comando `carousel` nel PATH — il resto di
questo documento lo usa:

```bash
pip install -e .
carousel styles
```

Per generare gli sfondi servono in più `pip install openai` e una
`OPENAI_API_KEY` (copia `.env.example` in `.env`).

---

## I due file

| File | Contiene | Lo cambi quando |
|------|----------|-----------------|
| `content.json` | titolo, sottotitolo, badge, `secrets[]`, `cta_q`, `image_prompts[]`, caption | scrivi un deck nuovo |
| `carousel/styles/*.json` | palette, font, scala tipografica, ricette delle slide | disegni un look nuovo |

Sono indipendenti: lo stesso contenuto si rende con qualsiasi stile, e qualsiasi
stile rende qualsiasi contenuto. Ricolorare un deck già fatto costa un comando e
riusa gli sfondi che hai già pagato.

---

## Scrivere il contenuto

Tre strade, dalla più comoda.

### Da un articolo che hai già scritto

Un post lungo si converte direttamente, se è strutturato come titolo, punti
numerati e domanda finale:

```bash
carousel import articolo.md
```

`# Titolo` diventa la copertina, la riga sotto il sottotitolo, ogni `### …` un
punto con il suo paragrafo come corpo, e la prima riga della sezione di chiusura
la call to action. L'introduzione e la riga `Fonti:` vengono ignorate: servono a
chi scrive, non finiscono in slide. Badge, nome della cartella e un prompt
immagine di partenza per ogni slide vengono ricavati da soli.

Un esempio completo di quel template e del flusso editoriale da cui nasce è in
[examples/scintilla-visiva/](examples/scintilla-visiva/).

### Rispondendo a delle domande

```bash
carousel new
```

Chiede titolo, sottotitolo, ogni segreto e la domanda finale, e ti avverte quando
una riga sfora il budget della sua slide *prima* che tu ci costruisca sopra.

### A mano

```json
{
  "name": "luce-naturale-ritratti",
  "locale": "it",
  "handle": "@iltuohandle",
  "wordmark": "IL TUO BRAND",

  "title": "4 segreti per ritratti in luce naturale",
  "subtitle": "senza flash, senza pannelli",
  "badge": "4 SEGRETI",
  "secrets": [
    ["Cerca l'ombra, non il sole", "Mettiti **all'ombra aperta**: la luce arriva morbida."]
  ],
  "cta_q": "Qual è il posto dove torni sempre a fotografare?",
  "image_prompts": ["<copertina>", "<punto 1>", "…", "<cta>"],
  "caption": "<caption Instagram completa>"
}
```

`secrets[]` comanda tutto il deck: **N segreti → N+2 slide** (copertina +
segreti + CTA), e `image_prompts[]` corrisponde 1:1 a quelle slide. Il corpo dei
segreti supporta il markup `**grassetto**`. Un esempio completo è in
[examples/starter/](examples/starter/content.json).

### Budget di lunghezza

Quello che sta davvero in una slide. `new` e `import` avvisano quando il testo
sfora; `carousel check content.json` ricontrolla qualsiasi deck e intercetta un
numero di prompt o un badge che non torna prima di renderizzare.

| Campo | Budget |
|-------|--------|
| `title` | 9 parole |
| `subtitle` | 8 parole |
| ogni headline | 6 parole |
| ogni corpo | 240 caratteri |
| `cta_q` | 14 parole |
| `secrets` | massimo 8 — Instagram si ferma a 10 slide |

---

## Lingua e brand

Ogni stile disegna qualche parola fissa intorno al tuo testo: l'invito a
scorrere, la riga del salva, l'etichetta sopra ogni punto. Stanno in
`carousel/locales/`, non dentro gli stili, così un solo file cambia lingua a
tutti e sette insieme.

```json
{ "locale": "it" }
```

Inglese e italiano sono già inclusi. Per aggiungere una lingua copia
`carousel/locales/en.json`, traduci i valori e tieni tutte le chiavi: ogni stile
la parla subito. Un deck può anche scavalcare una singola stringa senza creare un
file nuovo:

```json
{ "locale": "it", "strings": { "save": "Salvalo per dopo" } }
```

Il brand funziona allo stesso modo. `handle` e `wordmark` nel deck sono quello
che lo stile stampa come firma: impostali per deck quando la stessa
installazione serve più clienti, oppure una volta sola in `carousel/config.py` se
hai un brand solo. Se non imposti né l'uno né l'altro, quelle firme non vengono
disegnate e il deck resta pulito.

Vale anche per la direzione artistica degli sfondi. Ogni stile porta il proprio
`image_style`, perché la fotografia dietro un look brutalista non è quella dietro
un duotone, e un deck può scavalcarlo:

```bash
carousel import articolo.md --style v4     # prompt diretti per quel look
carousel prompts content.json --style v6   # rigenerali dopo un cambio di stile
```

Vince sempre il più vicino: **deck → stile → `carousel/config.py`**.

---

## Costruire il deck

Tre comandi separati, di proposito. Gli sfondi costano e sono scelti con cura,
quindi modificare il testo non deve mai ridisegnarli di nascosto.

| Fase | Comando | Produce |
|------|---------|---------|
| 1. Render | `carousel render content.json -s v3` | `slide_NN.png` (livelli trasparenti), `deck.txt`, `caption.txt` |
| 2. Sfondi | `carousel plates <cartella>` | `bg_NN.png` dai prompt immagine |
| 3. Compose | `carousel compose <cartella>` | `final_NN.jpg` — i file da pubblicare |

`carousel build content.json -s v3` esegue tutte e tre in un colpo solo.

Due comportamenti da tenere a mente:

- **`plates` non sovrascrive mai uno sfondo esistente.** Genera solo quello che
  manca. Con `--only 3,5` scegli le slide; `--force` sostituisce di proposito.
- **`render` pulisce gli orfani.** Se un deck perde un segreto, `slide_09.png` e
  `final_09.jpg` rimasti indietro vengono rimossi e segnalati, così una slide
  vecchia non finisce in un post.

`compose` scrive JPEG e non PNG di proposito: le Graph API di Instagram rifiutano
i PNG con l'errore `2207032`.

### Cambiare stile a un deck già fatto

Renderizza dentro la cartella del deck e ricomponi. Gli sfondi vengono riusati,
non rigenerati:

```bash
carousel render decks/TODO-04-x/content.json --style v6 --out decks/TODO-04-x
carousel compose decks/TODO-04-x
```

Per confrontare i look sul tuo testo prima di scegliere:

```bash
carousel preview content.json --out preview/
```

---

## Gli stili

| Nome | Etichetta | Carattere |
|------|-----------|-----------|
| `v1` | Forge Glow | Bagliore ambra su carbone, numeri giganti, scintilla del brand |
| `v2` | Editorial Panel | Card traslucida smerigliata, accento teal, testo più leggero |
| `v3` | Bold Poster | Testo enorme ancorato in basso, numeri vuoti, barra ember |
| `v4` | Editorial Brutalist | Blocchi crema in una cornice netta, testata mono, rosso segnale |
| `v5` | Editorial Serif | Fraunces da rivista, filetti sottili, margini ampi |
| `v6` | Luminous Duotone | Velatura duotone sfocata che fiorisce insieme alla foto |
| `v7` | Kinetic Teaching | Griglia da mirino, staffe di fuoco, HUD in Space Mono |

`v6` include tre varianti di palette. Un deck ne sceglie una con il proprio campo
`"palette"`, oppure la sceglie il suo nome in modo deterministico: così un deck
rende sempre con gli stessi colori, mentre una serie di deck ruota nella
famiglia.

---

## Scrivere uno stile

Uno stile è un JSON con cinque sezioni: `canvas`, `palette`, `fonts`, `type` e
`slides`. La ricetta dentro `slides` è una lista ordinata di operazioni di
disegno.

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

Tre idee reggono quasi tutta l'espressività:

- **Le espressioni.** Qualsiasi numero può essere un'operazione sulle variabili
  della slide: `"W - 2 * MX"`, `"H - 96"`. Vengono lette con `ast` su una lista
  chiusa di nodi, quindi un file di stile può fare i conti ma non eseguire
  codice.
- **Il cursore.** Le operazioni di testo fanno avanzare un cursore di layout,
  così il blocco successivo si posiziona con `{"after": 24}` invece che con una
  coordinata inventata. Un testo di qualsiasi lunghezza scorre da solo.
- **`measure`.** Misura il testo senza disegnarlo ed espone `<nome>_h`,
  `<nome>_w` e `<nome>_lines`. È così che un pannello si dimensiona sul testo
  disegnato *dopo* di lui, e che un blocco si ancora al piede della slide.

Schema completo e riferimento di tutte le operazioni:
**[docs/STYLES.md](docs/STYLES.md)**. Per l'elenco delle operazioni in qualsiasi
momento: `carousel styles --ops`.

### Progettarne uno conversando

Gli stili sono pensati per essere scritti descrivendo un brand, non digitando
coordinate. Dai a un'IA `docs/STYLES.md`, uno o due stili inclusi come esempio
concreto e la descrizione del brand — poi verifica quello che torna indietro:

```bash
carousel styles --check mio-brand.json
```

Carica il file, renderizza ogni tipo di slide con del testo di prova e indica il
passo esatto che non funziona:

```
error: midnight · cover slide · step 7 (op 'text'): unknown colour 'chartreuse'
       (palette has: hot, ink, line, muted, scrim)
```

Quel messaggio è pensato per essere incollato di nuovo nella conversazione. Metti
il file finito in `carousel/styles/` e compare subito in `carousel styles`.

[AGENTS.md](AGENTS.md) è il briefing per quella conversazione, e per gli altri
lavori che questo strumento lascia di proposito al giudizio: scrivere il testo,
scrivere i soggetti dei prompt immagine, modificare un deck e guardare il
risultato.

---

## Farlo tuo

| Cosa | Dove |
|------|------|
| Handle e wordmark | `handle` / `wordmark` nel deck, oppure `carousel/config.py` se hai un brand solo |
| Look degli sfondi generati | `image_style` nel deck, altrimenti nello stile, altrimenti `IMAGE_STYLE` in `carousel/config.py` |
| Le parole sulle slide | `carousel/locales/<lingua>.json` |
| I caratteri | metti un TTF in `fonts/`; il nome del file in minuscolo diventa la famiglia che uno stile richiama |
| Il look vero e proprio | un file nuovo in `carousel/styles/` |

Niente di tutto questo richiede di toccare Python.

---

## Struttura

```
carousel/
  config.py       dimensioni tela, percorsi font, costanti del brand
  style.py        carica il JSON di stile, risolve palette/tipografia/font
  values.py       il valutatore di espressioni
  fonts.py        registro dei font e gestione degli assi variabili
  typography.py   a capo, markup **grassetto**, spaziatura, disegno del testo
  engine.py       esegue le ricette di uno stile su un deck
  ops/            le primitive di disegno che gli stili richiamano
  deck.py         lettura/scrittura content.json, validazione, nomi cartelle
  authoring.py    markdown -> deck, procedura guidata, budget di lunghezza
  locales.py      i testi fissi delle slide, per lingua
  render.py       orchestrazione
  compose.py      slide + sfondi -> JPEG finali
  images.py       generazione degli sfondi
  cli.py          riga di comando
  styles/*.json   i look
fonts/            i TTF inclusi
docs/             riferimento stili, flusso editoriale, guida alle caption
example/          un content.json completo
tests/
```

## Test

```bash
python -m unittest discover tests
```

Coprono ogni stile incluso mentre rende un deck completo in ogni lingua inclusa,
la sandbox delle espressioni, la validazione dei deck e i budget di lunghezza,
l'import da markdown, la risoluzione dei font, il testo vuoto (outline), i deck
senza brand e la pulizia delle slide orfane che impedisce a uno `slide_09.png`
rimasto indietro di finire in un post dopo che il deck ha perso un punto. Un test
fa fallire la build se uno stile scrive a mano una parola che doveva arrivare da
un file di lingua.

## Licenza

MIT — vedi [LICENSE](LICENSE).

I caratteri inclusi **non** rientrano in questa licenza. Inter, Fraunces e Space
Mono sono sotto SIL Open Font License 1.1: il testo della licenza è in
[fonts/OFL.txt](fonts/OFL.txt) e il copyright di ogni famiglia in
[fonts/README.md](fonts/README.md).

I contributi sono benvenuti — [CONTRIBUTING.md](CONTRIBUTING.md).
