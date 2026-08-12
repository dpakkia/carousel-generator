"""Realign background plates after a deck changes shape.

Slides are numbered by position, and a plate is a file named after a position —
`bg_03.png`. So inserting a point in the middle renumbers the copy (which is
regenerated from content.json) but *not* the plates on disk, and every plate
after the insertion ends up behind the wrong slide.

The count check in `deck.validate()` catches the careless version of this, where
`image_prompts` no longer matches the slide count. It cannot catch the careful
version: keep the prompts in sync and validation goes quiet while the plates are
silently misaligned.

`deck.txt` is the record that makes the repair possible. It is rewritten on every
render, so before you re-render it still describes the shape the plates were
generated for. Matching its slide headlines against the current content.json
gives the mapping from old plate number to new slide number.

**Run this before re-rendering**, or deck.txt is overwritten and the old shape
is gone.
"""
import os
import re
import glob

from . import deck as deck_io

PLATE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
_SLIDE_LINE = re.compile(r"^SLIDE\s+(\d+)\s+[—–-]\s+(.*)$")

COVER = "\x00cover"      # sentinels: a cover only ever matches a cover
CTA = "\x00cta"

# Plates whose slide was deleted are renamed, never removed — a plate costs
# money to make and may well be wanted again.
ORPHAN_PREFIX = "orphan_"


class ReindexError(RuntimeError):
    pass


# ------------------------------------------------------------------- labelling
def normalise(label):
    """Compare headlines by their words, not their punctuation or markup."""
    if label in (COVER, CTA):
        return label
    s = re.sub(r"\*\*", "", label or "").lower()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()


def labels_from_deck_txt(folder):
    """The slide labels the plates in this folder were generated for."""
    path = os.path.join(folder, "deck.txt")
    if not os.path.isfile(path):
        raise ReindexError(
            f"no deck.txt in {folder} — without it there is no record of the "
            f"shape the plates were made for. Pass --from <old content.json> "
            f"instead.")
    labels = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = _SLIDE_LINE.match(line.strip())
            if not m:
                continue
            text = m.group(2).strip()
            upper = text.upper()
            labels.append(COVER if upper == "COVER" else CTA if upper == "CTA" else text)
    if not labels:
        raise ReindexError(f"{path} lists no slides")
    return labels


def labels_from_content(content):
    """The slide labels this deck has now."""
    return [COVER] + [h for h, _ in content.get("secrets", [])] + [CTA]


# ----------------------------------------------------------------------- plan
class Plan:
    """What reindexing this folder would do."""

    def __init__(self, folder, moves, unchanged, missing, orphans, collisions):
        self.folder = folder
        self.moves = moves            # [(old_slide, new_slide, path)]
        self.unchanged = unchanged    # [slide]
        self.missing = missing        # [new_slide] — no plate exists yet
        self.orphans = orphans        # [(old_slide, path)] — slide is gone
        self.collisions = collisions  # [(new_slide, path)] — target occupied

    @property
    def changed(self):
        return bool(self.moves or self.orphans)

    def describe(self, log=print):
        if self.moves:
            log("  renames:")
            for old, new, _ in self.moves:
                log(f"    bg_{old:02d} -> bg_{new:02d}")
        if self.unchanged:
            log(f"  already correct: {', '.join(f'bg_{n:02d}' for n in self.unchanged)}")
        if self.missing:
            log(f"  no plate yet:    {', '.join(f'bg_{n:02d}' for n in self.missing)}")
        if self.orphans:
            log("  orphaned (their slide is gone; set aside, not deleted):")
            for old, path in self.orphans:
                ext = os.path.splitext(path)[1]
                log(f"    bg_{old:02d} -> {ORPHAN_PREFIX}{old:02d}{ext}")
        if self.collisions:
            log("  BLOCKED — these targets are occupied by files not in the mapping:")
            for new, path in self.collisions:
                log(f"    bg_{new:02d}  {os.path.basename(path)}")


def existing_plates(folder):
    """{slide number: path} for every bg_NN plate on disk."""
    found = {}
    for path in sorted(glob.glob(os.path.join(folder, "bg_*"))):
        m = re.match(r"bg_(\d+)\.", os.path.basename(path))
        if m and os.path.splitext(path)[1].lower() in PLATE_EXTENSIONS:
            found[int(m.group(1))] = path
    return found


def find_plate(folder, slide):
    """The plate file for a slide number, whatever its extension."""
    for ext in PLATE_EXTENSIONS:
        p = os.path.join(folder, f"bg_{slide:02d}{ext}")
        if os.path.isfile(p):
            return p
    return None


def build_plan(folder, content, old_labels=None):
    """Work out how plates should be renumbered for the deck's current shape."""
    old_labels = old_labels or labels_from_deck_txt(folder)
    new_labels = labels_from_content(content)

    # Match old slides to new ones by headline. Cover matches cover, CTA matches
    # CTA, and a repeated headline matches the next unclaimed copy of itself.
    pool = {}
    for i, label in enumerate(new_labels, start=1):
        pool.setdefault(normalise(label), []).append(i)

    mapping = {}                       # old slide -> new slide
    for old_slide, label in enumerate(old_labels, start=1):
        candidates = pool.get(normalise(label))
        if candidates:
            mapping[old_slide] = candidates.pop(0)

    # Every plate actually on disk, including any left over from a shape older
    # than deck.txt records — those are orphans too, not obstacles.
    moves, unchanged, orphans = [], [], []
    for slide, path in sorted(existing_plates(folder).items()):
        new_slide = mapping.get(slide)
        if new_slide is None:
            orphans.append((slide, path))
        elif new_slide == slide:
            unchanged.append(slide)
        else:
            moves.append((slide, new_slide, path))

    claimed = {new for _, new, _ in moves} | set(unchanged)
    missing = [n for n in range(1, len(new_labels) + 1) if n not in claimed]

    # Orphans are moved aside before the renames, so they can never block one.
    # Anything still occupying a target after that is genuinely unexpected.
    freed = {slide for slide, _ in orphans}
    moving_from = {old for old, _, _ in moves} | freed
    collisions = [(new, find_plate(folder, new)) for _, new, _ in moves
                  if find_plate(folder, new)
                  and new not in moving_from and new not in unchanged]

    return Plan(folder, moves, sorted(unchanged), missing, orphans, collisions)


# ---------------------------------------------------------------------- apply
def apply_plan(plan, force=False):
    """Perform the renames. Two phases via temporary names, so any permutation
    is safe — a straight shift, a reorder, or a swap."""
    if plan.collisions and not force:
        raise ReindexError(
            "refusing to overwrite plates that are not part of the mapping "
            f"({', '.join(f'bg_{n:02d}' for n, _ in plan.collisions)}). "
            "Move or delete them, or pass --force.")
    if not (plan.moves or plan.orphans):
        return []

    # Phase 0 — set orphans aside. Their slide no longer exists, so they must
    # not sit on a number a live plate is moving into, and must not be lost.
    for slide, path in plan.orphans:
        ext = os.path.splitext(path)[1]
        os.replace(path, os.path.join(
            plan.folder, f"{ORPHAN_PREFIX}{slide:02d}{ext}"))

    staged = []
    for old, new, path in plan.moves:
        ext = os.path.splitext(path)[1]
        tmp = os.path.join(plan.folder, f".reindex_{new:02d}{ext}")
        os.replace(path, tmp)
        staged.append((tmp, os.path.join(plan.folder, f"bg_{new:02d}{ext}"), old, new))

    done = []
    for tmp, target, old, new in staged:
        os.replace(tmp, target)
        done.append((old, new, target))
    return done
