"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

The README's Tool Inventory section is the spec for all three.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── helpers for search_listings ───────────────────────────────────────────────

# Words that carry no search meaning. Dropped from the description before scoring.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "of", "in", "on", "with", "to", "me",
    "i", "im", "want", "need", "looking", "find", "something", "some", "any",
    "that", "is", "my", "under", "below", "size", "sz",
}

# What a shopper types vs. what the listings say. Kept short on purpose — this
# is a keyword match, not a thesaurus.
_SYNONYMS = {
    "tee": {"tee", "tshirt"},
    "tshirt": {"tee", "tshirt"},
    "jean": {"jean", "denim"},
    "pant": {"pant", "trouser"},
    "trouser": {"pant", "trouser"},
    "sneaker": {"sneaker", "shoe"},
    "jacket": {"jacket", "windbreaker", "bomber", "coat"},
}


def _stem(word: str) -> str:
    """Lowercase and drop a plural 's' so 'tees' meets 'tee' and 'jeans' meets 'jean'."""
    word = re.sub(r"[^a-z0-9]", "", word.lower())
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        word = word[:-1]
    return word


def _words(text: str) -> set[str]:
    return {w for w in (_stem(t) for t in re.split(r"[\s/,\-—]+", text or "")) if w}


def _size_options(size: str) -> list[str]:
    """
    Break a listing's size string into the sizes it offers.

    "S/M" offers s and m. "XL (oversized)" offers xl — the parenthesis is a
    note, not a size. "W30 L30" and "US 8.5" stay whole; their single parts
    ("w30", "8.5") are matched separately in _size_matches.
    """
    size = re.sub(r"\(.*?\)", "", size.lower())
    return [part.strip() for part in size.split("/") if part.strip()]


def _size_matches(wanted: str, listing_size: str) -> bool:
    """
    Whole-size match, not a substring test: "m" fits "M" and "S/M", never "XL"
    or "US 9". A multi-part size like "W30 L30" also answers to "w30".
    """
    wanted = wanted.lower().strip()
    for option in _size_options(listing_size):
        if wanted == option or wanted in option.split():
            return True
    return False


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Rule: the wanted size has to equal one of the sizes the
                     listing offers, case-insensitively. "M" matches "M", "S/M"
                     and "M/L"; it does not match "XL", "L/XL" or "US 9".
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand.

    Scoring: each description keyword earns 3 points if it is in the title, 2 in
    the style tags, colors or category, 1 in the description text or brand
    (best place only, once per keyword). Listings that score zero are dropped;
    ties go to the cheaper listing.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    keywords = {_stem(w) for w in re.split(r"\s+", description or "")} - _STOPWORDS - {""}
    if not keywords:
        return []

    scored = []
    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size and not _size_matches(size, listing["size"]):
            continue

        title = _words(listing["title"])
        tags = _words(" ".join(listing["style_tags"] + listing["colors"] + [listing["category"]]))
        body = _words(listing["description"] + " " + (listing["brand"] or ""))

        score = 0
        for keyword in keywords:
            variants = _SYNONYMS.get(keyword, {keyword})
            if variants & title:
                score += 3
            elif variants & tags:
                score += 2
            elif variants & body:
                score += 1
        if score:
            scored.append((score, listing))

    scored.sort(key=lambda pair: (-pair[0], pair[1]["price"]))
    return [listing for _, listing in scored[: config.SEARCH_RESULT_LIMIT]]


# ── helpers for the two model tools ───────────────────────────────────────────

_STYLIST_SYSTEM = (
    "You are a friendly thrift-shopping stylist. Be concrete and brief. "
    "Only talk about the pieces you are given; never invent a brand or a price."
)


def _price(item: dict) -> str:
    price = item.get("price")
    if price is None:
        return "price unknown"
    return f"${price:g}" if float(price).is_integer() else f"${price:.2f}"


def _describe_item(item: dict) -> str:
    """One line for a listing. `brand` is often None, so it is only added when present."""
    parts = [
        item.get("title", "untitled"),
        _price(item),
        f"size {item.get('size', '?')}",
        f"{item.get('condition', '?')} condition",
        f"on {item.get('platform', '?')}",
    ]
    if item.get("brand"):
        parts.append(f"brand {item['brand']}")
    if item.get("colors"):
        parts.append("colors: " + ", ".join(item["colors"]))
    if item.get("style_tags"):
        parts.append("style: " + ", ".join(item["style_tags"]))
    return " | ".join(parts)


def _describe_wardrobe_piece(piece: dict) -> str:
    line = f"- {piece.get('name', 'unnamed piece')} ({piece.get('category', '?')}"
    if piece.get("colors"):
        line += ", " + ", ".join(piece["colors"])
    line += ")"
    if piece.get("notes"):
        line += f" — {piece['notes']}"
    return line


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, returns general styling advice rather than
        raising or returning "".

    With a wardrobe, the prompt lists every piece and asks for combinations that
    name pieces the user already owns. Without one, it asks for general advice.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    items = (wardrobe or {}).get("items") or []
    item_line = _describe_item(new_item)

    if items:
        owned = "\n".join(_describe_wardrobe_piece(piece) for piece in items)
        prompt = (
            f"Someone is thinking about buying this secondhand piece:\n{item_line}\n\n"
            f"Here is everything in their wardrobe:\n{owned}\n\n"
            "Suggest one or two outfits built around the new piece. Name the "
            "specific wardrobe pieces to wear with it, exactly as listed. Say in "
            "a few words why each combination works. Keep it under 120 words."
        )
    else:
        prompt = (
            f"Someone is thinking about buying this secondhand piece:\n{item_line}\n\n"
            "They have not saved a wardrobe, so you don't know what they own. "
            "Give general styling advice: one or two outfit ideas using common "
            "pieces, and what kind of shoes and layers suit it. Keep it under "
            "120 words."
        )

    outfit = generate(prompt, system=_STYLIST_SYSTEM).strip()
    return outfit or (
        f"Pair the {new_item.get('title', 'piece')} with simple basics in a "
        "neutral colour and let it be the focus of the outfit."
    )


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, returns a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    if not outfit or not outfit.strip():
        return (
            "No fit card written — there was no outfit to build it from. "
            "Run suggest_outfit first and pass its result in."
        )

    prompt = (
        f"Write a caption for a post about a secondhand find.\n\n"
        f"The find: {_describe_item(new_item)}\n"
        f"The outfit: {outfit.strip()}\n\n"
        "The writer is the buyer who just found it, not the seller. "
        "Rules: two to four sentences, written like a real person posting, not "
        "a product description. Mention the item, its price "
        f"({_price(new_item)}) and the platform ({new_item.get('platform', 'unknown')}) "
        "once each. Be specific about the vibe. At most one emoji and no "
        "hashtags. Return only the caption."
    )
    card = generate(prompt, system=_STYLIST_SYSTEM).strip()
    return card or "No fit card written — the model returned nothing. Try again."
