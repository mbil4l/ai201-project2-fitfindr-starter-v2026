"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import config
import trace
from tools import search_listings, suggest_outfit, create_fit_card
from generate import ModelUnavailable


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "searched": False,           # True once search_listings has run, even if it found nothing
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
    }


# ── parsing the query ─────────────────────────────────────────────────────────
# Plain regex — no model call. A model call here would cost a request on every
# run and could change the parse between two identical queries.

_PRICE_PATTERNS = [
    r"(?:under|below|less than|max(?:imum)?|up to|no more than|at most|within|<=?)\s*\$?\s*(\d+(?:\.\d+)?)",
    r"\$\s*(\d+(?:\.\d+)?)",
]

_SIZE_WORDS = {"extra small": "XS", "small": "S", "medium": "M", "large": "L", "extra large": "XL"}
_SIZE_TOKEN = r"(?:[sml]/[sml]|l/xl|xxl|xxs|xl|xs|s|m|l|w\d{2}(?:\s*l\d{2})?|us\s*\d+(?:\.\d)?|\d+(?:\.\d)?|one size)"

_FILLER = re.compile(
    r"\b(?:i(?:'m| am)? (?:want|need|looking for|am looking for)|looking for|"
    r"find me|show me|i want|i need|can you find|please|dollars?|bucks|usd)\b",
    re.IGNORECASE,
)


def parse_query(query: str) -> dict:
    """
    Pull a description, a size and a max price out of a plain-language query.

    Returns {"description": str, "size": str | None, "max_price": float | None}.
    A price or size that isn't in the query comes back as None, which tells
    search_listings to skip that filter.
    """
    text = query.strip()
    max_price = None
    size = None

    for pattern in _PRICE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            max_price = float(match.group(1))
            text = text.replace(match.group(0), " ", 1)
            break

    match = re.search(rf"\b(?:size|sz)\s*:?\s*({_SIZE_TOKEN})\b", text, re.IGNORECASE)
    if match:
        size = re.sub(r"\s+", " ", match.group(1)).upper()
        text = text.replace(match.group(0), " ", 1)
    else:
        for word, value in _SIZE_WORDS.items():
            match = re.search(rf"\b{word}\b(?: size)?", text, re.IGNORECASE)
            if match:
                size = value
                text = text.replace(match.group(0), " ", 1)
                break

    text = _FILLER.sub(" ", text)
    description = re.sub(r"[^\w\s'/-]", " ", text)
    description = re.sub(r"\s+", " ", description).strip()
    return {"description": description, "size": size, "max_price": max_price}


def _nothing_found_message(parsed: dict) -> str:
    """
    Say what the user could change. Re-runs the search with one filter dropped
    at a time, so the message can name the filter that is actually in the way.
    """
    desc, size, price = parsed["description"], parsed["size"], parsed["max_price"]
    asked = f"'{desc}'" + (f", size {size}" if size else "") + (f", under ${price:g}" if price is not None else "")
    suggestions = []

    if price is not None:
        looser = search_listings(desc, size=size, max_price=None)
        if looser:
            cheapest = min(item["price"] for item in looser)
            suggestions.append(f"raise your price limit — the cheapest match is ${cheapest:g}")
    if size:
        looser = search_listings(desc, size=None, max_price=price)
        if looser:
            sizes = sorted({item["size"] for item in looser})
            suggestions.append(f"try a different size — matches come in {', '.join(sizes)}")
    if not suggestions:
        suggestions.append("try different or fewer keywords, like a style (vintage, y2k) or a type of item (jacket, jeans)")

    return f"Nothing matched {asked}. You could " + "; or ".join(suggestions) + "."


# ── planning loop ─────────────────────────────────────────────────────────────

def _next_step(session: dict) -> str | None:
    """
    Look at the session and say what runs next, or None when the run is done.
    This is where the loop reads the last result before picking the next step.
    """
    if not session["parsed"]:
        return "parse"
    if not session["searched"]:
        return "search"
    if not session["search_results"]:
        return None                      # branch: searched, found nothing — stop
    if session["selected_item"] is None:
        return "select"
    if session["outfit_suggestion"] is None:
        return "outfit"
    if session["fit_card"] is None:
        return "fit_card"
    return None


def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    The branch: if search_listings returns an empty list, put a message naming
    what to change in session["error"] and stop — suggest_outfit and
    create_fit_card are never called. Otherwise take the first result and go on.
    Every tool reads its inputs back out of the session, not from a local variable.
    """
    session = new_session(query, wardrobe)

    count = 0
    while (step := _next_step(session)) is not None:
        count += 1
        trace.check_iterations(count)

        if step == "parse":
            session["parsed"] = parse_query(session["query"])
            if not session["parsed"]["description"]:
                session["error"] = (
                    "I couldn't find anything to search for in that. Say what you "
                    "want — for example 'vintage graphic tee under $30, size M'."
                )
                return session

        elif step == "search":
            parsed = session["parsed"]
            session["search_results"] = search_listings(
                parsed["description"], size=parsed["size"], max_price=parsed["max_price"]
            )
            session["searched"] = True

        elif step == "select":
            session["selected_item"] = session["search_results"][0]

        elif step == "outfit":
            session["outfit_suggestion"] = suggest_outfit(
                session["selected_item"], session["wardrobe"]
            )

        elif step == "fit_card":
            session["fit_card"] = create_fit_card(
                session["outfit_suggestion"], session["selected_item"]
            )

    if session["searched"] and not session["search_results"]:
        session["error"] = _nothing_found_message(session["parsed"])

    return session


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )
