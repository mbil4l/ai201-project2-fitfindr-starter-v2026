"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # A query the data can match. Criterion 1.
        "name": "matching query completes all three tools",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # A query nothing can match. Criterion 2 — the branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # A user with nothing saved. One of unit 4's three failure modes.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
    {
        # Criterion 3 — the id in the session is the id both model tools
        # receive. A query with a size, so the item comes through a filter.
        "name": "selected item is the item passed on",
        "query": "90s track jacket in size M",
        "wardrobe": "example",
        "criterion": 3,
    },

    # Criterion 4 — five matching queries, five different items, across all
    # three platforms. One card per query; try k of each of these five is one
    # complete set of five cards, scored together (the opening-words check
    # compares each card with the other four in its set).
    {
        "name": "fit card: slip dress (lst_013, depop)",
        "query": "silk slip dress in midi length under $40",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "fit card: platform sneakers (lst_019, poshmark)",
        "query": "platform sneakers size 8",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "fit card: corduroy pants (lst_005, depop)",
        "query": "corduroy wide-leg pants under $40",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "fit card: windbreaker (lst_010, thredUp)",
        "query": "vintage windbreaker",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "fit card: chelsea boots (lst_028, poshmark)",
        "query": "suede chelsea boots",
        "wardrobe": "example",
        "criterion": 4,
    },

    # Criterion 5 — five queries with a size and a price ceiling, each picked
    # so a lazy size match would let something wrong through. "expect" is the
    # size and ceiling the query asks for; the check uses these, not what
    # parse_query pulled out, so a misread query counts against the agent too.
    {
        # M has to admit "M" and "S/M"; the $30 ceiling has to drop the $38 blazer.
        "name": "filters: vintage top, M, $30",
        "query": "vintage top size M under $30",
        "wardrobe": "example",
        "criterion": 5,
        "expect": {"size": "M", "max_price": 30},
    },
    {
        # L has to admit "L/XL" but not "XL" or "XL (fits oversized)".
        "name": "filters: oversized sweatshirt, L, $25",
        "query": "oversized sweatshirt size L under $25",
        "wardrobe": "example",
        "criterion": 5,
        "expect": {"size": "L", "max_price": 25},
    },
    {
        # 8 has to admit "US 8" but not "US 8.5" or "US 9".
        "name": "filters: sneakers, 8, $50",
        "query": "sneakers size 8 under $50",
        "wardrobe": "example",
        "criterion": 5,
        "expect": {"size": "8", "max_price": 50},
    },
    {
        # W30 has to admit "W30 L30" but not "W32" or "W28".
        "name": "filters: jeans, W30, $40",
        "query": "jeans size W30 under $40",
        "wardrobe": "example",
        "criterion": 5,
        "expect": {"size": "W30", "max_price": 40},
    },
    {
        # M has to admit "M/L"; the $50 ceiling has to drop the $75 bomber.
        "name": "filters: jacket, M, $50",
        "query": "jacket size M under $50",
        "wardrobe": "example",
        "criterion": 5,
        "expect": {"size": "M", "max_price": 50},
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems
