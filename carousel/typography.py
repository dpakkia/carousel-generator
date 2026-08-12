"""Text measurement and layout: `**bold**` markup, wrapping, drawing.

The engine is font-agnostic. Callers pass in the regular font and the bold font
to pair with it — the style decides what "bold" means for a given text style,
which is what lets a serif display face bold into a heavier serif instead of
silently switching family.
"""


def tokenize(text):
    """Strip ** markers; return [(word, is_bold)] with punctuation kept attached."""
    clean, mask, bold, i = [], [], False, 0
    while i < len(text):
        if text[i:i + 2] == "**":
            bold = not bold
            i += 2
            continue
        clean.append(text[i])
        mask.append(bold)
        i += 1
    s = "".join(clean)
    toks, j, n = [], 0, len(s)
    while j < n:
        if s[j].isspace():
            j += 1
            continue
        k = j
        while k < n and not s[k].isspace():
            k += 1
        toks.append((s[j:k], any(mask[j:k])))
        j = k
    return toks


def strip_markup(text):
    """The text as it will render, with the ** markers removed."""
    return " ".join(w for w, _ in tokenize(text or ""))


def wrap(draw, text, font, bold_font, maxw, tracking=0):
    """Wrap `text` to `maxw`, returning lines of [(word, is_bold)].

    Plain text is measured as whole strings so the font's kerning across word
    boundaries is respected; only mixed-weight text falls back to summing
    per-word advances, since those runs are drawn separately anyway.
    """
    text = text or ""
    if "**" not in text and not tracking:
        lines, cur = [], ""
        for word in text.split():
            candidate = (cur + " " + word).strip()
            if draw.textlength(candidate, font=font) <= maxw:
                cur = candidate
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return [[(w, False) for w in ln.split()] for ln in lines]

    space = _advance(draw, " ", font, tracking)
    lines, cur, curw = [], [], 0.0
    for word, is_bold in tokenize(text):
        f = bold_font if is_bold else font
        ww = _advance(draw, word, f, tracking)
        add = ww + (space if cur else 0)
        if cur and curw + add > maxw:
            lines.append(cur)
            cur, curw = [(word, is_bold)], ww
        else:
            cur.append((word, is_bold))
            curw += add
    if cur:
        lines.append(cur)
    return lines


def text_width(draw, s, font, tracking=0):
    """Visual width of a single run of text, without the trailing letter gap."""
    if not s:
        return 0.0
    return _advance(draw, s, font, tracking) - (tracking if tracking else 0)


def line_width(draw, line, font, bold_font, tracking=0):
    """Rendered width of one wrapped line.

    Letter-spacing is an advance *after* each glyph, so a measured width drops
    the trailing gap — otherwise centred and right-aligned tracked text sits
    half a space too far left.
    """
    if not tracking and not any(b for _, b in line):
        return draw.textlength(" ".join(w for w, _ in line), font=font)
    space = _advance(draw, " ", font, tracking)
    total = sum(_advance(draw, w, bold_font if b else font, tracking) for w, b in line)
    return total + space * (len(line) - 1) - (tracking if line else 0)


def draw_lines(draw, x, y, lines, font, bold_font, fill, leading,
               align="left", width=None, tracking=0,
               stroke_width=0, stroke_fill=None):
    """Draw wrapped lines and return the y just past the last one.

    `width` is the column the text aligns within — required for centre/right.
    `stroke_width` with a null `fill` gives hollow, outlined type.
    """
    for line in lines:
        if align == "left":
            start = x
        else:
            lw = line_width(draw, line, font, bold_font, tracking)
            start = x + (width - lw) if align == "right" else x + (width - lw) / 2
        _draw_line(draw, start, y, line, font, bold_font, fill, tracking,
                   stroke_width, stroke_fill)
        y += leading
    return y


def _draw_line(draw, x, y, line, font, bold_font, fill, tracking,
               stroke_width=0, stroke_fill=None):
    # Uniform runs go out in a single call so the font kerns across spaces.
    if not tracking and not any(b for _, b in line):
        _draw_word(draw, x, y, " ".join(w for w, _ in line), font, fill, 0,
                   stroke_width, stroke_fill)
        return
    space = _advance(draw, " ", font, tracking)
    for i, (word, is_bold) in enumerate(line):
        f = bold_font if is_bold else font
        if i:
            x += space
        x = _draw_word(draw, x, y, word, f, fill, tracking,
                       stroke_width, stroke_fill)


def _draw_word(draw, x, y, word, font, fill, tracking,
               stroke_width=0, stroke_fill=None):
    extra = {}
    if stroke_width:
        extra = {"stroke_width": int(stroke_width), "stroke_fill": stroke_fill}
    if not tracking:
        draw.text((x, y), word, font=font, fill=fill, **extra)
        return x + draw.textlength(word, font=font)
    for ch in word:                      # letter-spaced: one glyph at a time
        draw.text((x, y), ch, font=font, fill=fill, **extra)
        x += draw.textlength(ch, font=font) + tracking
    return x


def _advance(draw, s, font, tracking=0):
    """How far the pen moves after drawing `s` — including the trailing gap.

    Use this to position what comes next; use `line_width` to measure what a
    run of text actually occupies.
    """
    if not tracking:
        return draw.textlength(s, font=font)
    return sum(draw.textlength(ch, font=font) + tracking for ch in s)
