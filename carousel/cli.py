"""Command line entry point.

    carousel render content.json --style v3     copy  -> slide_*.png
    carousel plates decks/TODO-01-x             prompts -> bg_*.png
    carousel compose decks/TODO-01-x            slides + plates -> final_*.jpg
    carousel build content.json --style v3      render, plates, compose
    carousel styles                             what looks are available
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
from .style import Style, available, StyleError


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="carousel", description="Generate Instagram carousel decks from JSON.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("render", help="render slide overlays from a content.json")
    p.add_argument("content")
    p.add_argument("--style", "-s", default="v1", help="style name or path (default: v1)")
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
    p.add_argument("--style", "-s", default="v1")
    p.add_argument("--out", "-o")
    p.add_argument("--root", default="decks")
    p.add_argument("--no-plates", action="store_true", help="skip plate generation")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("styles", help="list the available styles")
    p.add_argument("--ops", action="store_true", help="also list the drawing ops")
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
    except (StyleError, images_mod.ImageError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


# --------------------------------------------------------------------- commands
def cmd_render(args):
    content = deck_io.load(args.content)
    _warn(content)
    folder, paths, removed = render_mod.build(
        content, args.style, out_folder=args.out,
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
    folder, _, _ = render_mod.build(content, args.style, out_folder=args.out,
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


def cmd_styles(args):
    for name in available():
        style = Style.load(name)
        note = style.data.get("meta", {}).get("description", "")
        print(f"{name:6} {style.label:22} {note[:70]}")
    if args.ops:
        print("\nops available to a style recipe:")
        print("  " + ", ".join(ops.available()))
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
