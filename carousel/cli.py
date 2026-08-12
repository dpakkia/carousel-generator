"""Command line entry point.

    carousel render content.json --style v3     copy  -> slide_*.png
    carousel render content.json --style auto   rotate the look by deck number
    carousel plates decks/TODO-01-x             prompts -> bg_*.png
    carousel compose decks/TODO-01-x            slides + plates -> final_*.jpg
    carousel build content.json --style v3      render, plates, compose
    carousel new                                answer questions -> content.json
    carousel import article.md                  blog post -> content.json
    carousel reindex decks/TODO-01-x            realign plates after a shape change
    carousel styles                             what looks are available
    carousel styles --check my-brand.json       validate a style you were handed
    carousel check content.json                 validate a deck before rendering
    carousel preview content.json               one contact sheet per style

The three stages are separate on purpose: plates cost money and are
art-directed, so re-rendering copy must never imply regenerating them.
"""
import os
import sys
import argparse

from . import deck as deck_io
from . import render as render_mod
from . import compose as compose_mod
from . import images as images_mod
from . import ops
from . import authoring
from . import reindex as reindex_mod
from .style import Style, available, rotate, rotation_table, StyleError


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="carousel", description="Generate Instagram carousel decks from JSON.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("render", help="render slide overlays from a content.json")
    p.add_argument("content")
    p.add_argument("--style", "-s", default="v1",
                   help="style name or path, or \"auto\" to rotate by deck number "
                        "(default: v1)")
    p.add_argument("--out", "-o", help="render into this existing deck folder (re-skin)")
    p.add_argument("--root", default="decks", help="where new deck folders are created")
    p.add_argument("--no-prune", action="store_true",
                   help="keep slide/final files left over above the slide count")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("plates", help="generate missing background plates")
    p.add_argument("folder")
    p.add_argument("--content", help="content.json (default: the folder's own)")
    p.add_argument("--only", help="slide numbers to generate, e.g. 3 or 3,5,7")
    p.add_argument("--force", action="store_true", help="replace plates that already exist")
    p.add_argument("--dry-run", action="store_true", help="show what would be generated")
    p.set_defaults(func=cmd_plates)

    p = sub.add_parser("compose", help="flatten slides over plates into final_*.jpg")
    p.add_argument("folder")
    p.add_argument("--quality", type=int, default=92)
    p.set_defaults(func=cmd_compose)

    p = sub.add_parser("build", help="render, generate missing plates, then compose")
    p.add_argument("content")
    p.add_argument("--style", "-s", default="v1",
                   help="style name or path, or \"auto\" to rotate by deck number")
    p.add_argument("--out", "-o")
    p.add_argument("--root", default="decks")
    p.add_argument("--no-plates", action="store_true", help="skip plate generation")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("new", help="build a content.json by answering questions")
    p.add_argument("--out", "-o", default="content.json")
    p.add_argument("--force", action="store_true", help="overwrite an existing file")
    p.add_argument("--locale", "-l", help="language for the slide chrome (default: en)")
    p.add_argument("--style", "-s", help="art-direct the image prompts for this style")
    p.set_defaults(func=cmd_new)

    p = sub.add_parser("import", help="turn a blog-post markdown file into a content.json")
    p.add_argument("article")
    p.add_argument("--out", "-o", default="content.json")
    p.add_argument("--force", action="store_true", help="overwrite an existing file")
    p.add_argument("--no-prompts", action="store_true",
                   help="leave image_prompts empty instead of scaffolding them")
    p.add_argument("--locale", "-l", help="language for the slide chrome (default: en)")
    p.add_argument("--style", "-s", help="art-direct the image prompts for this style")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("reindex",
                       help="realign background plates after a deck gains or loses a point")
    p.add_argument("folder")
    p.add_argument("--content", help="content.json (default: the folder's own)")
    p.add_argument("--from", dest="from_content", metavar="OLD",
                   help="an old content.json describing the shape the plates were made for "
                        "(default: read it from the folder's deck.txt)")
    p.add_argument("--dry-run", action="store_true", help="show the mapping, change nothing")
    p.add_argument("--force", action="store_true",
                   help="overwrite plates that are not part of the mapping")
    p.set_defaults(func=cmd_reindex)

    p = sub.add_parser("prompts", help="rewrite a deck's image prompts for a style")
    p.add_argument("content")
    p.add_argument("--style", "-s", help="take the art direction from this style")
    p.add_argument("--dry-run", action="store_true", help="show them without saving")
    p.set_defaults(func=cmd_prompts)

    p = sub.add_parser("styles", help="list the available styles")
    p.add_argument("--ops", action="store_true", help="also list the drawing ops")
    p.add_argument("--rotation", action="store_true",
                   help="show which style each deck number rotates to")
    p.add_argument("--check", metavar="PATH",
                   help="validate a style file (e.g. one an AI wrote) by rendering it")
    p.set_defaults(func=cmd_styles)

    p = sub.add_parser("check", help="validate a content.json")
    p.add_argument("content")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("preview", help="render a contact sheet for every style")
    p.add_argument("content")
    p.add_argument("--out", default="preview", help="output directory")
    p.add_argument("--styles", help="comma-separated subset, e.g. v1,v4")
    p.set_defaults(func=cmd_preview)

    args = parser.parse_args(argv)
    try:
        return args.func(args) or 0
    except (StyleError, images_mod.ImageError, reindex_mod.ReindexError,
            FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


# --------------------------------------------------------------------- commands
def cmd_render(args):
    content = deck_io.load(args.content)
    _warn(content)
    style = resolve_style(args.style, args.out, os.path.abspath(args.root))
    folder, paths, removed = render_mod.build(
        content, style, out_folder=args.out,
        root=os.path.abspath(args.root), prune=not args.no_prune)
    for p in removed:
        print(f"removed stale {os.path.basename(p)}")
    print(folder)
    for p in paths:
        print(f"  {os.path.basename(p)}")
    return 0


def cmd_plates(args):
    folder = args.folder
    content = deck_io.load(args.content or os.path.join(folder, "content.json"))
    images_mod.load_dotenv(os.path.join(os.getcwd(), ".env"))
    only = {int(n) for n in args.only.split(",")} if args.only else None
    written = images_mod.generate(folder, content, only=only, force=args.force,
                                  dry_run=args.dry_run)
    for p in written:
        print(p)
    return 0


def cmd_compose(args):
    outputs = compose_mod.compose_folder(args.folder, quality=args.quality)
    for p in outputs:
        print(p)
    return 0


def cmd_build(args):
    content = deck_io.load(args.content)
    _warn(content)
    style = resolve_style(args.style, args.out, os.path.abspath(args.root))
    folder, _, _ = render_mod.build(content, style, out_folder=args.out,
                                    root=os.path.abspath(args.root))
    print(folder)
    if not args.no_plates:
        images_mod.load_dotenv(os.path.join(os.getcwd(), ".env"))
        try:
            images_mod.generate(folder, content)
        except images_mod.ImageError as e:
            print(f"skipping plates: {e}")
    for p in compose_mod.compose_folder(folder):
        print(f"  {os.path.basename(p)}")
    return 0


def cmd_new(args):
    if os.path.exists(args.out) and not args.force:
        print(f"error: {args.out} already exists (pass --force to replace it)",
              file=sys.stderr)
        return 1
    try:
        content = authoring.wizard(locale=args.locale,
                                   style=_style_or_none(args.style))
    except (KeyboardInterrupt, EOFError):
        print("\naborted — nothing written")
        return 1
    return _write_content(content, args.out)


def cmd_import(args):
    if os.path.exists(args.out) and not args.force:
        print(f"error: {args.out} already exists (pass --force to replace it)",
              file=sys.stderr)
        return 1
    with open(args.article, encoding="utf-8") as f:
        content = authoring.from_markdown(f.read(), locale=args.locale)

    if not content.get("secrets"):
        print("error: no secrets found. The article needs a '### ' heading per "
              "secret — see docs/USER-GUIDE.md for the template.", file=sys.stderr)
        return 1
    if not args.no_prompts:
        content["image_prompts"] = authoring.scaffold_prompts(
            content, _style_or_none(args.style))
    return _write_content(content, args.out)


def cmd_reindex(args):
    """Renumber plates to match the deck's current shape.

    Run this *before* re-rendering: deck.txt is the record of the shape the
    plates were generated for, and rendering overwrites it.
    """
    folder = args.folder
    content = deck_io.load(args.content or os.path.join(folder, "content.json"))

    old_labels = None
    if args.from_content:
        old_labels = reindex_mod.labels_from_content(deck_io.load(args.from_content))
    plan = reindex_mod.build_plan(folder, content, old_labels)

    print(f"{folder}")
    plan.describe()

    if not plan.changed:
        print("\nplates already line up with the deck — nothing to do")
        if plan.missing:
            print("generate the missing ones with: "
                  f"carousel plates {folder} --only "
                  f"{','.join(str(n) for n in plan.missing)}")
        return 0

    if args.dry_run:
        print("\ndry run — nothing moved")
        return 0

    done = reindex_mod.apply_plan(plan, force=args.force)
    print(f"\n{len(done)} plates renamed")
    if plan.missing:
        print("now generate the new ones:")
        print(f"  carousel plates {folder} --only "
              f"{','.join(str(n) for n in plan.missing)}")
    print("then re-render and recompose:")
    print(f"  carousel render {os.path.join(folder, 'content.json')} --out {folder}")
    print(f"  carousel compose {folder}")
    return 0


def cmd_prompts(args):
    """Re-derive the image prompts, e.g. after re-skinning a deck.

    Prompts live in content.json, so switching a deck's look leaves the old art
    direction behind until they are rewritten. Plates already on disk are never
    touched — regenerate the ones you want with `plates --only`.
    """
    content = deck_io.load(args.content)
    style = _style_or_none(args.style)
    prompts = authoring.scaffold_prompts(content, style)
    clause = authoring.resolve_image_style(content, style)

    print(f"art direction: {clause}\n")
    for i, prompt in enumerate(prompts, start=1):
        print(f"  {i:02d}  {prompt[:100]}…")
    if args.dry_run:
        print("\ndry run — nothing written")
        return 0

    content["image_prompts"] = prompts
    deck_io.save(content, args.content)
    print(f"\n{len(prompts)} prompts written to {args.content}")
    print("existing plates are untouched; regenerate with: "
          "carousel plates <folder> --only N --force")
    return 0


def _style_or_none(name):
    return Style.load(name) if name else None


def resolve_style(name, out_folder=None, root=None, announce=True):
    """Turn a --style value into a style name, expanding "auto".

    "auto" rotates by deck number: the number in the target folder when
    re-rendering one, otherwise the number the next new folder will get.
    """
    if name != "auto":
        return name

    index = deck_io.deck_number(out_folder) if out_folder else None
    source = f"folder {os.path.basename(os.path.normpath(out_folder))}" if index \
        else None
    if index is None:
        index = deck_io.next_index(root or os.getcwd())
        source = f"next deck number {index:02d}"

    picked = rotate(index)
    if announce:
        print(f"style: {picked} (auto, from {source})")
    return picked


def _write_content(content, path):
    deck_io.save(content, path)
    authoring.summarise(content)

    problems = deck_io.validate(content)
    warnings = authoring.budget_warnings(content)
    if problems or warnings:
        print()
    for p in problems:
        print(f"problem: {p}")
    for w in warnings:
        print(f"warning: {w}")

    print(f"\nwritten to {path}")
    if not content.get("caption"):
        print("next: add a caption (see docs/CAPTION.md), then")
    else:
        print("next:")
    print(f"  carousel render {path} --style v1")
    return 1 if problems else 0


def cmd_styles(args):
    if args.check:
        return _check_style(args.check)
    for name in available():
        style = Style.load(name)
        note = style.data.get("meta", {}).get("description", "")
        print(f"{name:6} {style.label:22} {note[:70]}")
    if args.rotation:
        print("\nwith --style auto, deck number picks the look:")
        for number, name in rotation_table():
            print(f"  {number:02d}  {name}")
        print("  …then it wraps")
    if args.ops:
        print("\nops available to a style recipe:")
        print("  " + ", ".join(ops.available()))
    return 0


def _check_style(path):
    """Load a style and render every slide kind, reporting the first failure.

    Styles are usually written by an AI from a brand brief, so the useful output
    is a precise complaint — which slide, which step, which op.
    """
    from . import engine
    style = Style.load(path)
    print(f"{style.name} — {style.label}")
    print(f"  {style.width}x{style.height}, margin {style.margin}, "
          f"{len(style.palette)} colours, {len(style.type_styles)} type styles")

    sample = {
        "name": "style-check",
        "title": "Five ways to make light do the talking",
        "subtitle": "no studio, no flash",
        "badge": "2 POINTS",
        "secrets": [
            ["Find open shade", "Step **into the shade**: the light arrives soft "
             "and even, and nobody squints into the lens."],
            ["Expose for the highlights", "Drop **-0.7 EV**. Lifting a shadow "
             "costs a little noise; a blown highlight is simply gone."],
        ],
        "cta_q": "Which place do you keep going back to?",
        "handle": "@yourhandle",
        "wordmark": "YOUR BRAND",
    }
    images = engine.render_deck(style, sample)
    for i, im in enumerate(images, start=1):
        if not im.getbbox():
            print(f"  slide {i}: rendered completely empty")
            return 1
    print(f"  renders {len(images)} slides cleanly")
    return 0


def cmd_check(args):
    content = deck_io.load(args.content)
    problems = deck_io.validate(content)
    total = deck_io.total_slides(content)
    print(f"{content.get('name', '(unnamed)')}: "
          f"{len(content.get('secrets', []))} secrets -> {total} slides")
    if not problems:
        print("looks good")
        return 0
    for p in problems:
        print(f"  - {p}")
    return 1


def cmd_preview(args):
    from PIL import Image
    content = deck_io.load(args.content)
    names = args.styles.split(",") if args.styles else available()
    os.makedirs(args.out, exist_ok=True)

    for name in names:
        folder = os.path.join(args.out, f"_{name}")
        _, paths, _ = render_mod.build(content, name, out_folder=folder,
                                       root=os.path.abspath(args.out))
        thumbs = [compose_mod.compose_slide(p).resize((216, 270), Image.LANCZOS)
                  for p in paths]
        sheet = Image.new("RGB", (216 * len(thumbs), 270), (12, 12, 14))
        for i, t in enumerate(thumbs):
            sheet.paste(t, (i * 216, 0))
        out = os.path.join(args.out, f"{name}.jpg")
        sheet.save(out, "JPEG", quality=88)
        print(out)
    return 0


def _warn(content):
    for problem in deck_io.validate(content):
        print(f"warning: {problem}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
