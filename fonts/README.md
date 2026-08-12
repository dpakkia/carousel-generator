# Bundled fonts

Three typefaces ship with this repository so that a fresh clone renders every
style without hunting for files. All three are licensed under the **SIL Open
Font License, Version 1.1**, whose full text is in [OFL.txt](OFL.txt).

| File | Family | Copyright | Upstream |
|------|--------|-----------|----------|
| `Inter.ttf` | Inter | Copyright 2016 The Inter Project Authors | https://github.com/rsms/inter |
| `Fraunces.ttf` | Fraunces | Copyright 2020 The Fraunces Project Authors | https://github.com/undercasetype/Fraunces |
| `SpaceMono-Regular.ttf`, `SpaceMono-Bold.ttf` | Space Mono | Copyright 2016 The Space Mono Project Authors | https://github.com/googlefonts/spacemono |

The OFL permits bundling and redistribution, including in commercial work. Two
conditions matter in practice:

- the license and copyright notices travel with the fonts — that is what this
  file and `OFL.txt` are for;
- the fonts must not be sold on their own, and a **Reserved Font Name** may not
  be reused on a modified version. None of these three declare a reserved name,
  so a modified copy may keep its family name — but if you swap in a font that
  does, rename it before redistributing.

The OFL applies to the font files only. The rest of this repository is under its
own licence — see [../LICENSE](../LICENSE).

## Adding your own

Drop a TTF or OTF into this directory. The lowercased filename stem becomes the
family name a style can reference:

```
Inter.ttf            -> family "inter"
SpaceMono-Bold.ttf   -> family "spacemono", variant "bold"
```

```json
"fonts": { "display": { "family": "yourfont", "weight": "Bold" } }
```

If you redistribute this repository with fonts you added, add their licences
here too. Many commercial licences forbid redistribution entirely — in that case
keep the font out of the repository and load it from elsewhere.
