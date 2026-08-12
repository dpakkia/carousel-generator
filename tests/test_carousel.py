"""Tests for the carousel generator.

Run with:  python -m unittest discover tests     (or: pytest)
"""
import os
import sys
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from carousel import deck, engine, render, fonts, authoring, locales  # noqa: E402
from carousel import typography as ty                               # noqa: E402
from carousel import values                                         # noqa: E402
from carousel.style import Style, StyleError, available             # noqa: E402
from carousel.render import prune_stale                             # noqa: E402

DECK = {
    "name": "test-deck",
    "title": "4 segreti per **ritratti** in luce naturale",
    "subtitle": "senza flash",
    "badge": "3 SEGRETI",
    "secrets": [
        ["Cerca l'ombra", "Mettiti **all'ombra aperta**: la luce arriva morbida."],
        ["Esponi per le alte luci", "Scendi di **-0,7 EV** e salva le zone chiare."],
        ["Usa il muro", "Piazza il soggetto a **un metro** da una parete chiara."],
    ],
    "cta_q": "Qual è il posto dove torni sempre?",
    "image_prompts": ["a", "b", "c", "d", "e"],
    "caption": "una caption",
}


class TestStyles(unittest.TestCase):
    def test_every_style_loads(self):
        self.assertTrue(available(), "no styles found")
        for name in available():
            with self.subTest(style=name):
                style = Style.load(name)
                self.assertGreater(style.width, 0)
                for kind in ("cover", "secret", "cta"):
                    self.assertTrue(style.recipe(kind), f"{name} has no {kind} recipe")

    def test_every_style_renders_a_full_deck(self):
        for name in available():
            with self.subTest(style=name):
                images = engine.render_deck(Style.load(name), DECK)
                self.assertEqual(len(images), 5, "cover + 3 secrets + cta")
                for im in images:
                    self.assertEqual(im.size, (1080, 1350))
                    self.assertEqual(im.mode, "RGBA")

    def test_slides_are_not_blank(self):
        for name in available():
            with self.subTest(style=name):
                for im in engine.render_deck(Style.load(name), DECK):
                    self.assertTrue(im.getbbox(), "slide rendered completely empty")

    def test_unknown_style_is_reported(self):
        with self.assertRaises(StyleError):
            Style.load("does-not-exist")

    def test_unknown_colour_names_the_palette(self):
        style = Style.load("v1")
        with self.assertRaises(StyleError) as ctx:
            style.color("chartreuse")
        self.assertIn("chartreuse", str(ctx.exception))

    def test_variant_palette_is_deterministic(self):
        style = Style.load("v6")
        a = engine.apply_variant(style, {"name": "deck-one"}).palette["a"]
        b = engine.apply_variant(style, {"name": "deck-one"}).palette["a"]
        self.assertEqual(a, b, "same deck must always pick the same variant")

    def test_variant_can_be_pinned_by_the_deck(self):
        style = Style.load("v6")
        picked = engine.apply_variant(style, {"name": "x", "palette": "teal-indigo"})
        self.assertEqual(tuple(picked.palette["a"]), (48, 170, 164))


class TestExpressions(unittest.TestCase):
    def test_arithmetic_and_variables(self):
        env = {"W": 1080, "MX": 96}
        self.assertEqual(values.number("W - 2 * MX", env), 888.0)
        self.assertEqual(values.number(560, env), 560.0)

    def test_cursor_relative(self):
        env = {"cursor": 400.0}
        self.assertEqual(values.number({"after": 24}, env), 424.0)

    def test_unknown_variable_is_an_error(self):
        with self.assertRaises(values.ExpressionError):
            values.number("NOPE + 1", {})

    def test_expressions_cannot_execute_code(self):
        for hostile in ("__import__('os').system('true')", "open('/etc/passwd')"):
            with self.assertRaises(values.ExpressionError):
                values.number(hostile, {})


class TestDeck(unittest.TestCase):
    def test_total_slides(self):
        self.assertEqual(deck.total_slides(DECK), 5)

    def test_valid_deck_has_no_problems(self):
        self.assertEqual(deck.validate(DECK), [])

    def test_prompt_count_mismatch_is_caught(self):
        bad = dict(DECK, image_prompts=["only", "two"])
        self.assertTrue(any("image_prompts" in p for p in deck.validate(bad)))

    def test_badge_count_mismatch_is_caught(self):
        bad = dict(DECK, badge="9 SEGRETI")
        self.assertTrue(any("badge" in p for p in deck.validate(bad)))

    def test_slugify(self):
        self.assertEqual(deck.slugify("Foto d'auto PRO!"), "foto-d-auto-pro")
        self.assertEqual(deck.slugify(""), "deck")
        self.assertEqual(deck.slugify("", "carosello"), "carosello")

    def test_deck_number_reads_every_naming_state(self):
        self.assertEqual(deck.deck_number("TODO-07-x"), 7)
        self.assertEqual(deck.deck_number("07-TO-POST-x"), 7)
        self.assertEqual(deck.deck_number("DONE-07-x"), 7)


class TestTypography(unittest.TestCase):
    def test_bold_markup_is_stripped_and_flagged(self):
        toks = ty.tokenize("plain **bold word** plain")
        self.assertEqual([w for w, _ in toks], ["plain", "bold", "word", "plain"])
        self.assertEqual([b for _, b in toks], [False, True, True, False])

    def test_markers_never_reach_the_canvas(self):
        self.assertNotIn("*", ty.strip_markup("a **b** c"))


class TestFonts(unittest.TestCase):
    def test_bundled_families_are_discovered(self):
        found = fonts.families()
        for family in ("inter", "fraunces", "spacemono"):
            self.assertIn(family, found, f"{family} not found in fonts/")

    def test_spacemono_bold_is_a_separate_file(self):
        self.assertNotEqual(fonts.path_for("spacemono", "bold"),
                            fonts.path_for("spacemono"))

    def test_missing_family_falls_back_without_crashing(self):
        self.assertIsNotNone(fonts.load({"family": "nope"}, 40))


class TestRender(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_writes_slides_deck_and_caption(self):
        folder, paths, _ = render.build(DECK, "v1", root=self.tmp)
        self.assertEqual(len(paths), 5)
        self.assertTrue(os.path.isfile(os.path.join(folder, "deck.txt")))
        self.assertTrue(os.path.isfile(os.path.join(folder, "caption.txt")))
        self.assertTrue(os.path.basename(folder).startswith("TODO-01-test-deck"))

    def test_deck_txt_carries_every_prompt(self):
        folder, _, _ = render.build(DECK, "v1", root=self.tmp)
        with open(os.path.join(folder, "deck.txt"), encoding="utf-8") as f:
            text = f.read()
        self.assertEqual(text.count("IMG:"), len(DECK["image_prompts"]))

    def test_reskin_reuses_the_same_folder(self):
        folder, _, _ = render.build(DECK, "v1", root=self.tmp)
        again, _, _ = render.build(DECK, "v4", out_folder=folder, root=self.tmp)
        self.assertEqual(folder, again)

    def test_prune_removes_only_slides_above_the_count(self):
        for n in (1, 2, 3, 4, 5, 6, 7):
            open(os.path.join(self.tmp, f"slide_{n:02d}.png"), "w").close()
        removed = prune_stale(self.tmp, 5)
        self.assertEqual(len(removed), 2)
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "slide_05.png")))
        self.assertFalse(os.path.isfile(os.path.join(self.tmp, "slide_06.png")))

    def test_shrinking_a_deck_clears_the_orphans(self):
        folder, _, _ = render.build(DECK, "v1", root=self.tmp)
        smaller = dict(DECK, secrets=DECK["secrets"][:1], image_prompts=["a", "b", "c"])
        _, paths, removed = render.build(smaller, "v1", out_folder=folder, root=self.tmp)
        self.assertEqual(len(paths), 3)
        self.assertEqual(len(removed), 2)


ARTICLE = """# 4 segreti per ritratti in luce naturale
senza flash, senza pannelli

Intro che non finisce in nessuna slide.

## I segreti

### 1. Cerca l'ombra, non il sole
Mettiti **all'ombra aperta**: la luce arriva morbida e uniforme.

### 2. Esponi per le alte luci
Scendi di **-0,7 EV** e salva le zone chiare.

## Chiudi
Qual è il posto dove torni sempre a fotografare?

---
Fonti: Canale — Titolo — https://example.com
"""


class TestAuthoring(unittest.TestCase):
    def test_markdown_becomes_a_deck(self):
        content = authoring.from_markdown(ARTICLE)
        self.assertEqual(content["title"], "4 segreti per ritratti in luce naturale")
        self.assertEqual(content["subtitle"], "senza flash, senza pannelli")
        self.assertEqual(len(content["secrets"]), 2)
        self.assertEqual(content["secrets"][0][0], "Cerca l'ombra, non il sole")
        self.assertIn("**all'ombra aperta**", content["secrets"][0][1])
        self.assertEqual(content["cta_q"], "Qual è il posto dove torni sempre a fotografare?")

    def test_badge_and_name_are_derived(self):
        content = authoring.from_markdown(ARTICLE)
        self.assertEqual(content["badge"], "2 POINTS")
        self.assertEqual(content["name"], "4-segreti-per-ritratti-in-luce-naturale")

    def test_intro_and_sources_are_not_slides(self):
        content = authoring.from_markdown(ARTICLE)
        joined = json_dumps(content)
        self.assertNotIn("Intro che non finisce", joined)
        self.assertNotIn("example.com", joined)

    def test_imported_deck_is_valid_and_renders(self):
        content = authoring.from_markdown(ARTICLE)
        content["image_prompts"] = authoring.scaffold_prompts(content)
        self.assertEqual(deck.validate(content), [])
        self.assertEqual(len(engine.render_deck(Style.load("v1"), content)), 4)

    def test_one_scaffolded_prompt_per_slide(self):
        content = authoring.from_markdown(ARTICLE)
        prompts = authoring.scaffold_prompts(content)
        self.assertEqual(len(prompts), deck.total_slides(content))
        for p in prompts:
            self.assertTrue(p.endswith("No text, no letters, no watermark."))
            self.assertNotIn("**", p, "markup must not reach an image prompt")

    def test_budget_warnings_flag_long_copy(self):
        content = authoring.from_markdown(ARTICLE)
        self.assertEqual(authoring.budget_warnings(content), [])
        content["secrets"][0][1] = "x" * 400
        self.assertTrue(any("body" in w for w in authoring.budget_warnings(content)))

    def test_budget_ignores_bold_markers(self):
        over, _, _ = authoring.over_budget("headline", "**una due tre**")
        self.assertEqual(over, 0)

    def test_article_without_secrets_yields_none(self):
        self.assertEqual(authoring.from_markdown("# Solo un titolo\n")["secrets"], [])


class TestLocales(unittest.TestCase):
    """Slide chrome is data, so one file re-languages every style."""

    def test_shipped_languages_have_the_same_keys(self):
        self.assertIn("en", locales.available())
        base = set(locales.load("en"))
        for name in locales.available():
            with self.subTest(locale=name):
                self.assertEqual(set(locales.load(name)), base,
                                 f"{name}.json is missing or adding keys")

    def test_no_style_hardcodes_chrome(self):
        """A literal cue in a recipe would be invisible to translation."""
        import glob, json as _json
        leaked = []
        for path in glob.glob(os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "carousel", "styles", "*.json")):
            with open(path, encoding="utf-8") as fh:
                raw = _json.dumps(_json.load(fh))
            for word in ("Scorri", "Salva", "Segui", "SEGRETO", "SCORRI",
                         "Continua", "SEGUI", "SALVA"):
                if word in raw:
                    leaked.append(f"{os.path.basename(path)}: {word}")
        self.assertEqual(leaked, [], "chrome must come from carousel/locales/")

    def test_chrome_reaches_the_slide_in_the_deck_language(self):
        en = engine.slide_data(dict(DECK, locale="en"), "cta", 5, total=5)
        it = engine.slide_data(dict(DECK, locale="it"), "cta", 5, total=5)
        self.assertEqual(en["scroll"], "Swipe →")
        self.assertEqual(it["scroll"], "Scorri →")

    def test_follow_interpolates_the_brand_handle(self):
        data = engine.slide_data(dict(DECK, locale="en", handle="@someone"),
                                 "cta", 5, total=5)
        self.assertEqual(data["follow"], "Follow @someone")

    def test_a_deck_can_override_one_string(self):
        data = engine.slide_data(
            dict(DECK, locale="en", strings={"save": "Pin this"}), "cta", 5, total=5)
        self.assertEqual(data["save"], "Pin this")
        self.assertEqual(data["scroll"], "Swipe →", "other strings untouched")

    def test_unknown_language_is_reported(self):
        with self.assertRaises(locales.LocaleError):
            locales.load("klingon")

    def test_every_style_renders_in_every_language(self):
        for name in available():
            for lang in locales.available():
                with self.subTest(style=name, locale=lang):
                    imgs = engine.render_deck(Style.load(name), dict(DECK, locale=lang))
                    self.assertTrue(all(im.getbbox() for im in imgs))


class TestUnbrandedDeck(unittest.TestCase):
    """A deck with no brand set must still render, just without the marks."""

    def test_renders_without_handle_or_wordmark(self):
        bare = {k: v for k, v in DECK.items()}
        for name in available():
            with self.subTest(style=name):
                imgs = engine.render_deck(Style.load(name), bare)
                self.assertTrue(all(im.getbbox() for im in imgs))

    def test_brand_defaults_are_not_personal(self):
        from carousel import config
        self.assertEqual(config.HANDLE, "")
        self.assertEqual(config.WORDMARK, "")


class TestHollowType(unittest.TestCase):
    """v3 draws its numerals as an outline: a stroke with no fill."""

    def test_type_style_stroke_is_not_lost(self):
        style = Style.load("v3")
        self.assertEqual(style.text_style("number")["stroke_width"], 3)
        self.assertIsNone(style.text_style("number")["color"])

    def test_outline_numeral_leaves_its_counter_open(self):
        style = Style.load("v3")
        img = engine.render_slide(
            style, "secret", engine.slide_data(DECK, "secret", 2, 1, 3, 5))
        # The bowl of the "0" sits inside the numeral; an outline leaves it clear
        # while a filled numeral would paint it. Sample well inside the glyph.
        px = img.getpixel((120, 210))
        self.assertLess(px[3], 200, "numeral counter should not be filled in")

    def test_stroke_colour_is_actually_drawn(self):
        style = Style.load("v3")
        img = engine.render_slide(
            style, "secret", engine.slide_data(DECK, "secret", 2, 1, 3, 5))
        amber = tuple(style.palette["amber"])
        px = img.load()
        found = any(px[x, y][:3] == amber and px[x, y][3] > 200
                    for x in range(80, 400, 2) for y in range(110, 380, 2))
        self.assertTrue(found, "no amber stroke pixels found in the numeral area")


def json_dumps(obj):
    import json
    return json.dumps(obj, ensure_ascii=False)


class TestExampleDeck(unittest.TestCase):
    def test_shipped_example_is_valid(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        content = deck.load(os.path.join(root, "examples", "starter", "content.json"))
        self.assertEqual(deck.validate(content), [])


if __name__ == "__main__":
    unittest.main()
