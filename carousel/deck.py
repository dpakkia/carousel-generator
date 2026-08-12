"""Deck I/O: reading content.json, naming deck folders, writing deck.txt.

A deck is cover + N secrets + CTA, so `total = len(secrets) + 2`, and
`image_prompts` maps 1:1 onto those slides (prompt i -> slide i+1 -> bg_i+1.png).
Keeping that mapping intact is the single easiest thing to get wrong when you
add or split a secret, so `validate()` checks it explicitly.
"""
import os
import re
import glob
import json


def load(path):
    """Read a content.json into a dict."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(content, path):
    """Write a content.json back, escaping inner quotes and keeping accents."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
        f.write("\n")


def total_slides(content):
    return 1 + len(content.get("secrets", [])) + 1


def validate(content):
    """Return a list of human-readable problems; empty means the deck is sound."""
    problems = []
    secrets = content.get("secrets", [])
    if not secrets:
        problems.append("no secrets — the deck would be just a cover and a CTA")
    for i, s in enumerate(secrets, start=1):
        if not isinstance(s, (list, tuple)) or len(s) != 2:
            problems.append(f"secret {i} is not a [headline, body] pair")
    if not content.get("title"):
        problems.append("missing title (the cover would be blank)")

    total = total_slides(content)
    prompts = content.get("image_prompts", [])
    if prompts and len(prompts) != total:
        problems.append(
            f"image_prompts has {len(prompts)} entries but the deck has {total} "
            f"slides — the slide/bg mapping is off by {len(prompts) - total}")

    badge = content.get("badge", "")
    m = re.match(r"\s*(\d+)\b", badge)
    if m and int(m.group(1)) != len(secrets):
        problems.append(
            f"badge says {m.group(1)} but there are {len(secrets)} secrets")
    return problems


def slugify(name, fallback="deck"):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower())
    return re.sub(r"-+", "-", s).strip("-") or fallback


def next_index(root):
    """Next free TODO-NN number in `root`."""
    idx = 0
    for d in glob.glob(os.path.join(root, "TODO-*")):
        if not os.path.isdir(d):
            continue
        m = re.match(r"TODO-(\d+)-", os.path.basename(d))
        if m:
            idx = max(idx, int(m.group(1)))
    return idx + 1


def folder_for(content, root, out_folder=None):
    """Resolve the deck folder: `out_folder` to re-skin in place, else a new
    auto-numbered TODO-NN-<name> under `root`."""
    folder = out_folder or os.path.join(
        root, f"TODO-{next_index(root):02d}-{slugify(content.get('name'))}")
    if not os.path.isabs(folder):
        folder = os.path.join(root, folder)
    return folder


def deck_number(folder):
    """The leading number of a deck folder name, or None.

    Accepts every naming state in use: TODO-07-x, 07-TO-POST-x, DONE-07-x.
    """
    base = os.path.basename(os.path.normpath(folder))
    m = re.match(r"(?:TODO-|DONE-)?(\d+)", base)
    return int(m.group(1)) if m else None


def write_deck_txt(folder, c, total):
    """The human-readable record of the deck: copy + the per-slide IMG prompts.

    Regenerated from `image_prompts` on every render, so edit content.json and
    never deck.txt — this file is a record, not a source.
    """
    prompts = c.get("image_prompts", [])
    img = lambda i: prompts[i] if i < len(prompts) else ""
    out = [c.get("title", "")]
    if c.get("subtitle"):
        out.append(c["subtitle"])
    if c.get("badge"):
        out.append(c["badge"])
    out += ["", "SLIDE 01 — COVER"]
    if img(0):
        out.append(f"  IMG: {img(0)}")
    out.append("")
    for n, (h, b) in enumerate(c.get("secrets", []), start=2):
        out += [f"SLIDE {n:02d} — {h}", f"  {b}"]
        if img(n - 1):
            out.append(f"  IMG: {img(n - 1)}")
        out.append("")
    out += [f"SLIDE {total:02d} — CTA", f"  {c.get('cta_q', '')}"]
    if img(total - 1):
        out.append(f"  IMG: {img(total - 1)}")
    out.append("")
    with open(os.path.join(folder, "deck.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def write_caption(folder, content):
    """Write caption.txt if the deck carries a caption. Returns the path or None."""
    cap = (content.get("caption") or "").strip()
    if not cap:
        return None
    p = os.path.join(folder, "caption.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(cap + "\n")
    return p
