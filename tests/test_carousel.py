"""Tests for the carousel generator.

Run with:  python -m unittest discover tests     (or: pytest)
"""
import os
import sys
import glob
import json
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from carousel import deck, engine, render, fonts, authoring, locales  # noqa: E402
from carousel import typography as ty                               # noqa: E402
from carousel import values                                         # noqa: E402
from carousel.style import (Style, StyleError, available, rotate,    # noqa: E402
                            rotation_table)                          # noqa: E402
from carousel.render import prune_stale                             # noqa: E402
from carousel import reindex as reindex_mod                         # noqa: E402

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


class TestImageStyle(unittest.TestCase):
    """Plate art direction: deck beats style beats install default."""

    def test_every_shipped_style_art_directs_its_plates(self):
        for name in available():
            with self.subTest(style=name):
                self.assertTrue(Style.load(name).image_style,
                                f"{name} has no image_style")

    def test_styles_do_not_all_share_one_look(self):
        clauses = {Style.load(n).image_style for n in available()}
        self.assertGreater(len(clauses), 1, "art direction must vary by style")

    def test_style_beats_the_install_default(self):
        from carousel import config
        clause = authoring.resolve_image_style({}, Style.load("v6"))
        self.assertNotEqual(clause, config.IMAGE_STYLE)
        self.assertEqual(clause, Style.load("v6").image_style)

    def test_deck_beats_the_style(self):
        clause = authoring.resolve_image_style(
            {"image_style": "my own look"}, Style.load("v6"))
        self.assertEqual(clause, "my own look")

    def test_falls_back_to_config_with_neither(self):
        from carousel import config
        self.assertEqual(authoring.resolve_image_style({}, None), config.IMAGE_STYLE)

    def test_a_literal_clause_is_accepted(self):
        self.assertEqual(authoring.resolve_image_style({}, "just this"), "just this")

    def test_scaffolded_prompts_carry_the_style_look(self):
        prompts = authoring.scaffold_prompts(
            {"title": "T", "secrets": [["h", "b"]], "cta_q": "q"}, Style.load("v4"))
        marker = Style.load("v4").image_style[:30]
        self.assertTrue(all(marker in p for p in prompts))


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

    def test_locales_stay_brand_neutral(self):
        """A locale is inherited by every brand, so it must not carry one
        brand's vocabulary. This shipped wrong once: the Italian file used the
        author's own photography framing (SEGRETO, "per la prossima sessione"),
        which read as nonsense for, say, a car-care account."""
        leaked = []
        for name in locales.available():
            blob = " ".join(locales.load(name).values()).lower()
            for word in ("segreto", "segreti", "sessione", "fuoco", "scatto",
                         "obiettivo", "photo", "shoot", "camera"):
                if word in blob:
                    leaked.append(f"{name}.json: {word}")
        self.assertEqual(leaked, [],
                         "locale files must not carry one brand's vocabulary")

    def test_a_style_supplies_defaults_for_words_it_invented(self):
        """v7's viewfinder HUD is a prop of the look, not anyone's language."""
        self.assertIn("focus_lock", Style.load("v7").strings)
        for name in locales.available():
            self.assertNotIn("focus_lock", locales.load(name),
                             "style furniture should not sit in a locale")

    def test_the_three_layers_resolve_nearest_wins(self):
        style = Style.load("v7")
        base = engine.slide_data(dict(DECK, locale="it"), "cta", 5,
                                 total=5, style=style)
        self.assertEqual(base["section"], "PUNTO", "locale supplies the word")
        self.assertEqual(base["focus_lock"], "FOCUS · LOCK", "style default")

        pinned = engine.slide_data(
            dict(DECK, locale="it", strings={"section": "SEGRETO",
                                             "focus_lock": "FUOCO · BLOCCO"}),
            "cta", 5, total=5, style=style)
        self.assertEqual(pinned["section"], "SEGRETO", "deck beats locale")
        self.assertEqual(pinned["focus_lock"], "FUOCO · BLOCCO", "deck beats style")

    def test_a_locale_beats_a_style_default(self):
        """Anything translatable belongs in a locale, so adding it there wins."""
        style = Style.load("v7")
        style.strings = {"scroll": "STYLE-DEFAULT"}
        data = engine.slide_data(dict(DECK, locale="it"), "cta", 5,
                                 total=5, style=style)
        self.assertEqual(data["scroll"], "Scorri →")

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


class TestSharedStrings(unittest.TestCase):
    """A brand with several decks keeps its vocabulary in one file, and that
    file lives with the brand's work rather than inside this repository."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.brand = os.path.join(self.tmp, "brand.json")
        with open(self.brand, "w", encoding="utf-8") as f:
            json.dump({"_note": "ignored", "section": "DETTAGLIO",
                       "save": "Salvalo per dopo"}, f)
        self.deck_dir = os.path.join(self.tmp, "decks", "01-x")
        os.makedirs(self.deck_dir)
        self.path = os.path.join(self.deck_dir, "content.json")
        self.write({"strings": "../../brand.json"})

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, extra):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(dict(DECK, locale="it", **extra), f, ensure_ascii=False)

    def test_a_path_is_resolved_relative_to_the_deck(self):
        content = deck.load(self.path)
        self.assertEqual(deck.strings_for(content)["section"], "DETTAGLIO")

    def test_underscore_keys_in_the_brand_file_are_ignored(self):
        self.assertNotIn("_note", deck.strings_for(deck.load(self.path)))

    def test_the_words_reach_the_slide(self):
        content = deck.load(self.path)
        data = engine.slide_data(content, "cta", 5, total=5, style=Style.load("v7"))
        self.assertEqual(data["section"], "DETTAGLIO", "brand file wins")
        self.assertEqual(data["scroll"], "Scorri →", "locale still supplies the rest")

    def test_saving_keeps_the_reference_rather_than_inlining_it(self):
        content = deck.load(self.path)
        deck.save(content, self.path)
        with open(self.path, encoding="utf-8") as f:
            raw = json.load(f)
        self.assertEqual(raw["strings"], "../../brand.json")
        self.assertNotIn("_strings", raw, "working state must not be written back")

    def test_an_inline_object_still_works(self):
        self.write({"strings": {"section": "INLINE"}})
        content = deck.load(self.path)
        self.assertEqual(deck.strings_for(content)["section"], "INLINE")

    def test_a_missing_file_says_where_it_looked(self):
        self.write({"strings": "../../nope.json"})
        with self.assertRaises(deck.DeckError) as ctx:
            deck.load(self.path)
        self.assertIn("nope.json", str(ctx.exception))
        self.assertIn("relative to", str(ctx.exception))

    def test_an_absolute_path_works_too(self):
        self.write({"strings": self.brand})
        self.assertEqual(deck.strings_for(deck.load(self.path))["section"], "DETTAGLIO")

    def test_a_brand_file_that_is_not_an_object_is_rejected(self):
        bad = os.path.join(self.tmp, "bad.json")
        with open(bad, "w", encoding="utf-8") as f:
            json.dump(["not", "an", "object"], f)
        self.write({"strings": bad})
        with self.assertRaises(deck.DeckError):
            deck.load(self.path)


class TestRotation(unittest.TestCase):
    """Consecutive decks must not repeat a look."""

    def test_the_documented_sequence(self):
        # 01 -> v1 … 07 -> v7, then back to the start
        for number, expected in [(1, "v1"), (2, "v2"), (7, "v7"),
                                 (8, "v1"), (9, "v2"), (15, "v1")]:
            with self.subTest(deck=number):
                self.assertEqual(rotate(number), expected)

    def test_rotates_over_however_many_styles_exist(self):
        three = ["a", "b", "c"]
        self.assertEqual([rotate(n, three) for n in range(1, 8)],
                         ["a", "b", "c", "a", "b", "c", "a"])

    def test_never_repeats_within_one_cycle(self):
        picks = [rotate(n) for n in range(1, len(available()) + 1)]
        self.assertEqual(len(set(picks)), len(picks))

    def test_a_missing_deck_number_is_an_error(self):
        for bad in (None, 0, -1):
            with self.subTest(index=bad):
                with self.assertRaises(StyleError):
                    rotate(bad)

    def test_no_styles_is_an_error_not_a_crash(self):
        with self.assertRaises(StyleError):
            rotate(1, [])

    def test_every_rotated_name_actually_loads(self):
        for _, name in rotation_table():
            with self.subTest(style=name):
                self.assertTrue(Style.load(name).slides)

    def test_rotation_table_covers_the_wrap(self):
        table = rotation_table()
        self.assertGreater(len(table), len(available()),
                           "table should show at least one wrapped deck")
        self.assertEqual(table[0][1], table[len(available())][1])


class TestReindex(unittest.TestCase):
    """Plates are named by slide position, so changing a deck's shape
    misaligns them. validate() cannot see it once the prompt count is kept in
    sync, which is exactly when it is most dangerous."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.folder, _, _ = render.build(DECK, "v1", root=self.tmp)
        # a stand-in plate per slide, tagged with the slide it was made for
        from PIL import Image
        for n in range(1, deck.total_slides(DECK) + 1):
            Image.new("RGB", (4, 4), (n * 10, 0, 0)).save(
                os.path.join(self.folder, f"bg_{n:02d}.png"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def made_for(self, slide):
        """Which slide the plate now at `slide` was originally generated for."""
        from PIL import Image
        path = os.path.join(self.folder, f"bg_{slide:02d}.png")
        return Image.open(path).getpixel((0, 0))[0] // 10

    def insert_point(self, at=1):
        """Add a point with the bookkeeping done correctly throughout."""
        c = json.loads(json.dumps(DECK))
        c["secrets"].insert(at, ["Brand new point", "with a brand new body"])
        c["image_prompts"].insert(at + 1, "a new prompt")
        c["badge"] = f"{len(c['secrets'])} SEGRETI"
        return c

    def test_the_silent_case_passes_validation(self):
        """The trap: every check satisfied, every later plate still wrong.

        validate() catches a stale prompt count or badge. It cannot see plate
        alignment, so doing the bookkeeping properly is what makes this
        dangerous rather than what makes it safe.
        """
        shifted = self.insert_point()
        self.assertEqual(deck.validate(shifted), [])
        plan = reindex_mod.build_plan(self.folder, shifted)
        self.assertTrue(plan.moves, "validation was clean but plates are misaligned")

    def test_insertion_shifts_every_later_plate(self):
        plan = reindex_mod.build_plan(self.folder, self.insert_point())
        self.assertEqual([(o, n) for o, n, _ in plan.moves],
                         [(3, 4), (4, 5), (5, 6)])
        self.assertEqual(plan.unchanged, [1, 2])
        self.assertEqual(plan.missing, [3])

    def test_applying_puts_every_plate_behind_its_own_copy(self):
        plan = reindex_mod.build_plan(self.folder, self.insert_point())
        reindex_mod.apply_plan(plan)
        for new_slide, original in ((1, 1), (2, 2), (4, 3), (5, 4), (6, 5)):
            self.assertEqual(self.made_for(new_slide), original,
                             f"bg_{new_slide:02d} holds the wrong plate")

    def test_a_reorder_is_handled_not_just_a_shift(self):
        """Renaming in one pass would clobber; staging through temps does not."""
        c = json.loads(json.dumps(DECK))
        c["secrets"] = [c["secrets"][2], c["secrets"][1], c["secrets"][0]]
        plan = reindex_mod.build_plan(self.folder, c)
        reindex_mod.apply_plan(plan)
        self.assertEqual([self.made_for(n) for n in (2, 3, 4)], [4, 3, 2])

    def test_deleting_a_point_sets_its_plate_aside_rather_than_losing_it(self):
        c = json.loads(json.dumps(DECK))
        removed = c["secrets"].pop(0)
        plan = reindex_mod.build_plan(self.folder, c)
        self.assertEqual([o for o, _ in plan.orphans], [2])
        reindex_mod.apply_plan(plan)
        self.assertTrue(os.path.isfile(
            os.path.join(self.folder, "orphan_02.png")), "orphan was deleted")
        self.assertEqual(self.made_for(2), 3, "later plates should shift down")

    def test_no_temp_files_survive(self):
        plan = reindex_mod.build_plan(self.folder, self.insert_point())
        reindex_mod.apply_plan(plan)
        self.assertEqual(glob.glob(os.path.join(self.folder, ".reindex_*")), [])

    def test_unchanged_deck_is_a_no_op(self):
        plan = reindex_mod.build_plan(self.folder, DECK)
        self.assertFalse(plan.changed)
        self.assertEqual(reindex_mod.apply_plan(plan), [])

    def test_matching_ignores_markup_and_punctuation(self):
        c = json.loads(json.dumps(DECK))
        c["secrets"][0][0] = "**Cerca** l'ombra!"       # was "Cerca l'ombra"
        plan = reindex_mod.build_plan(self.folder, c)
        self.assertFalse(plan.orphans, "reworded headline should still match")
        self.assertFalse(plan.changed)

    def test_missing_deck_txt_is_explained(self):
        os.remove(os.path.join(self.folder, "deck.txt"))
        with self.assertRaises(reindex_mod.ReindexError) as ctx:
            reindex_mod.build_plan(self.folder, DECK)
        self.assertIn("--from", str(ctx.exception))


class TestExampleDeck(unittest.TestCase):
    def test_shipped_example_is_valid(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        content = deck.load(os.path.join(root, "examples", "starter", "content.json"))
        self.assertEqual(deck.validate(content), [])


if __name__ == "__main__":
    unittest.main()
