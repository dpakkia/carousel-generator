"""Tests for the carousel generator.

Run with:  python -m unittest discover tests     (or: pytest)
"""
import os
import sys
import shutil
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from carousel import deck, engine, render, fonts, typography as ty  # noqa: E402
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
        self.assertEqual(deck.slugify(""), "carosello")

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


class TestExampleDeck(unittest.TestCase):
    def test_shipped_example_is_valid(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        content = deck.load(os.path.join(root, "example", "content.json"))
        self.assertEqual(deck.validate(content), [])


if __name__ == "__main__":
    unittest.main()
