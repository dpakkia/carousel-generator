"""Getting to a content.json without hand-writing JSON.

Two routes in:

  from_markdown()  the blog post from Stage 3 of the workflow — a title, N
                   numbered secrets, a closing question — parsed straight into
                   a deck. The template was already shaped like the deck, so
                   this is mostly bookkeeping.
  wizard()         a guided set of questions for starting from scratch.

Both run the same length budgets, because copy that overflows a slide is the
one failure the renderer cannot fix for you.
"""
import re
import textwrap

from .config import IMAGE_STYLE
from . import deck as deck_io

# Budgets from the editorial workflow — what actually fits a 1080x1350 slide.
BUDGETS = {
    "title": (9, "words"),
    "subtitle": (8, "words"),
    "headline": (6, "words"),
    "body": (240, "characters"),
    "cta_q": (14, "words"),
}
MAX_SECRETS = 8          # Instagram caps a carousel at 10 slides: cover + 8 + CTA


def _count(text, unit):
    text = re.sub(r"\*\*", "", text or "")
    return len(text.split()) if unit == "words" else len(text)


def over_budget(field, text):
    """How far past its budget a field is, or 0. Returns (over, limit, unit)."""
    limit, unit = BUDGETS[field]
    n = _count(text, unit)
    return (max(0, n - limit), limit, unit)


def budget_warnings(content):
    """Soft warnings about copy that will crowd or overflow its slide."""
    out = []
    for field in ("title", "subtitle", "cta_q"):
        over, limit, unit = over_budget(field, content.get(field, ""))
        if over:
            out.append(f"{field} is {over} {unit} over the {limit}-{unit[:-1]} budget")

    for i, pair in enumerate(content.get("secrets", []), start=1):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        headline, body = pair
        over, limit, unit = over_budget("headline", headline)
        if over:
            out.append(f"secret {i} headline is {over} {unit} over the {limit}-word budget")
        over, limit, unit = over_budget("body", body)
        if over:
            out.append(f"secret {i} body is {over} characters over the {limit}-character budget")

    n = len(content.get("secrets", []))
    if n > MAX_SECRETS:
        out.append(f"{n} secrets — Instagram allows {MAX_SECRETS} "
                   f"(cover + {MAX_SECRETS} + CTA = 10 slides). Keep the strongest.")
    return out


# ------------------------------------------------------------------- markdown
_H1 = re.compile(r"^#\s+(.*)$")
_H2 = re.compile(r"^##\s+(.*)$")
_H3 = re.compile(r"^###\s+(?:\d+[.)]\s*)?(.*)$")
_CLOSING = re.compile(r"^(chiudi|close|closing|cta|conclusione)\b", re.I)
_SOURCES = re.compile(r"^(fonti|sources|credits)\s*:", re.I)


def from_markdown(text):
    """Parse the workflow's blog-post template into a deck.

    Recognises: `# Title`, the line under it as the subtitle, every `### …` as a
    secret (its following paragraph is the body), and the closing section's
    first line as the CTA question. Intro copy and the `Fonti:` line are
    ignored — they are context for the writer, not slides.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    content = {"title": "", "subtitle": "", "secrets": [], "cta_q": ""}

    secrets = []
    current = None          # [headline, [body lines]]
    in_closing = False
    seen_title = False
    subtitle_pending = False

    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("---") and set(stripped) <= {"-"}:
            continue
        if _SOURCES.match(stripped):
            break

        m = _H1.match(stripped)
        if m:
            content["title"] = m.group(1).strip()
            seen_title, subtitle_pending = True, True
            continue

        m = _H3.match(stripped)
        if m:
            if current:
                secrets.append(current)
            current = [m.group(1).strip(), []]
            in_closing = False
            continue

        m = _H2.match(stripped)
        if m:
            if current:
                secrets.append(current)
                current = None
            in_closing = bool(_CLOSING.match(m.group(1).strip()))
            continue

        if not stripped:
            if subtitle_pending and content["subtitle"]:
                subtitle_pending = False
            continue

        if subtitle_pending and seen_title and not content["subtitle"]:
            content["subtitle"] = stripped
            continue

        if current is not None:
            current[1].append(stripped)
        elif in_closing and not content["cta_q"]:
            content["cta_q"] = stripped

    if current:
        secrets.append(current)

    content["secrets"] = [[h, " ".join(b).strip()] for h, b in secrets if h]
    content["badge"] = f"{len(content['secrets'])} SEGRETI"
    content["name"] = deck_io.slugify(content["title"])
    return content


# --------------------------------------------------------------- image prompts
# Where the text sits on each slide kind, so the plate leaves room for it.
_NEGATIVE_SPACE = {
    "cover": "large near-black negative space across the lower half",
    "secret": "large near-black negative space down the left column",
    "cta": "a calm, empty centre",
}


def scaffold_prompts(content, style=IMAGE_STYLE):
    """One starting-point image prompt per slide, in slide order.

    These are a scaffold, not finished art direction — the subject clause is
    lifted from each slide's own copy. Rewrite the subject, keep the style and
    the negative-space clause, and the deck stays visually coherent.
    """
    def build(subject, kind):
        subject = re.sub(r"\*\*", "", subject or "").strip().rstrip(".")
        return (f"{subject}. {style} 1080x1350 portrait (4:5), "
                f"{_NEGATIVE_SPACE[kind]}, low contrast, nothing busy. "
                f"No text, no letters, no watermark.")

    prompts = [build(content.get("title", ""), "cover")]
    for headline, body in content.get("secrets", []):
        prompts.append(build(f"{headline} — {body}"[:180], "secret"))
    prompts.append(build(content.get("cta_q", ""), "cta"))
    return prompts


# --------------------------------------------------------------------- wizard
def wizard(ask=input, out=print):
    """Guided questions -> a deck. `ask`/`out` are injectable for testing."""
    def field(label, key, hint="", required=True):
        limit, unit = BUDGETS.get(key, (None, None))
        budget = f" (max {limit} {unit})" if limit else ""
        while True:
            out(f"\n{label}{budget}")
            if hint:
                out(f"  {hint}")
            value = ask("> ").strip()
            if not value and required:
                out("  needed — try again")
                continue
            if not value:
                return value
            if limit:
                over, limit_, unit_ = over_budget(key, value)
                if over:
                    out(f"  that is {over} {unit_} over the budget and will crowd "
                        f"the slide. Enter to keep it, or type a shorter version.")
                    again = ask("> ").strip()
                    if again:
                        value = again
            return value

    out("New carousel deck. Ctrl-C to abort.\n"
        "Copy is Italian, 'tu', imperative, concrete, no emoji.")

    content = {}
    content["title"] = field("Cover title — the promise", "title",
                             "e.g. 5 segreti per foto d'auto da pro")
    content["subtitle"] = field("Subtitle — the constraint or tension", "subtitle",
                                "e.g. senza studio, senza flash")

    out("\nNow the secrets. Blank headline when you're done "
        f"(max {MAX_SECRETS}). Wrap key terms in **double asterisks** to bold them.")
    secrets = []
    while len(secrets) < MAX_SECRETS:
        n = len(secrets) + 1
        headline = field(f"Secret {n} — headline", "headline",
                         "the takeaway in a few words", required=False)
        if not headline:
            break
        body = field(f"Secret {n} — body", "body",
                     "the concrete action + why, 1-2 sentences")
        secrets.append([headline, body])
    content["secrets"] = secrets

    content["cta_q"] = field("Closing question — invites a comment", "cta_q",
                             "e.g. Qual è il posto dove torni sempre a fotografare?")

    content["badge"] = f"{len(secrets)} SEGRETI"
    content["name"] = deck_io.slugify(
        field("Short folder name", "name",
              f"kebab-case; Enter to use '{deck_io.slugify(content['title'])}'",
              required=False) or content["title"])

    out("\nCaption (the post copy). Paste it, then a blank line. "
        "Enter to skip and add it later.")
    caption = []
    while True:
        line = ask("")
        if not line.strip():
            break
        caption.append(line)
    if caption:
        content["caption"] = "\n".join(caption)

    content["image_prompts"] = scaffold_prompts(content)
    return content


def summarise(content, out=print):
    """Print a deck the way the user reviews it: everything, in slide order."""
    total = deck_io.total_slides(content)
    out(f"\n{content.get('name', '(unnamed)')} — {len(content.get('secrets', []))} "
        f"secrets, {total} slides")
    out(f"  cover     {content.get('title', '')}")
    out(f"            {content.get('subtitle', '')}")
    out(f"            [{content.get('badge', '')}]")
    for i, (headline, body) in enumerate(content.get("secrets", []), start=1):
        out(f"  slide {i + 1:<3} {headline}")
        for line in textwrap.wrap(body, 68):
            out(f"            {line}")
    out(f"  cta       {content.get('cta_q', '')}")
