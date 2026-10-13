#!/usr/bin/env python3
"""
Run the test and score every try against criteria.md. ← UNIT 4, Milestones 3 and 5

    python score_eval.py --label before
    python score_eval.py --label after

run_eval.py runs every scenario five times with the cache off and writes the
raw output into results/, but leaves PASS and FAIL blank. This runs
run_eval.main() exactly as it is — same arguments, same scenarios, same raw
results file — and adds two things on top:

  • It wraps suggest_outfit and create_fit_card where agent.py calls them, so
    each try records the id of the item each tool actually received. That is
    how criterion 3 says it is checked, and it also shows whether a model tool
    ran at all (criteria 1 and 2). The wrappers pass every call straight
    through; the agent does exactly what it does without them.

  • It applies the rule from criteria.md to every try and writes the run-log
    table, with the reason for every PASS and FAIL, next to the raw file as
    results/run_<stamp>_<label>_scored.md.

Criteria 4 and 5 are each written over five different queries, so one try of
either is a whole set: try k is the k-th run of each of its five scenarios.
"""

import re

import config
import agent
import run_eval
import scenarios as scenario_module

# What each criterion needs, as written in criteria.md.
CRITERIA = {
    1: ("A matching query completes all three tools", "4 of 5", 4),
    2: ("An impossible query stops before the second tool", "5 of 5", 5),
    3: ("Selected item is the item both model tools receive", "5 of 5", 5),
    4: ("Fit cards: 2-4 sentences, price, platform, distinct opening", "4 of 5 cards, every try", 5),
    5: ("Search results stay inside the size and price asked for", "0 violations, every try", 5),
}


# ── recording what the model tools receive ────────────────────────────────────

_received: list[tuple[str, str | None]] = []   # (tool, item id) for the try in progress


def _recording(name, tool, position):
    """Wrap a model tool so each call notes the id of the item it was handed."""
    def wrapper(*args, **kwargs):
        item = args[position] if len(args) > position else kwargs.get("new_item")
        _received.append((name, (item or {}).get("id")))
        return tool(*args, **kwargs)
    return wrapper


agent.suggest_outfit = _recording("suggest_outfit", agent.suggest_outfit, 0)
agent.create_fit_card = _recording("create_fit_card", agent.create_fit_card, 1)

_run_once = run_eval.run_once
_write_report = run_eval.write_report


def _run_once_recorded(scenario, use_trace=True):
    _received.clear()
    record = _run_once(scenario, use_trace)
    record["received"] = list(_received)
    return record


def _write_report_and_score(rows, args):
    _write_report(rows, args)
    write_scored(rows, args)


run_eval.run_once = _run_once_recorded
run_eval.write_report = _write_report_and_score


# ── the rules ─────────────────────────────────────────────────────────────────

def _no_card_reason(record):
    """Why a try ended without a fit card, or None if it has one."""
    if record["crashed"]:
        return f"crashed: {record['crashed'][:70]}"
    if record["session"]["error"]:
        return f"stopped: {record['session']['error'][:70]}"
    return None


def _tools_called(record):
    return [name for name, _ in record["received"]]


def score_1(record):
    """All three tools ran and a fit card came back."""
    reason = _no_card_reason(record)
    if reason:
        return False, reason
    session = record["session"]
    if not session["search_results"] or _tools_called(record) != ["suggest_outfit", "create_fit_card"]:
        return False, f"tools after search: {_tools_called(record)}"
    card = (session["fit_card"] or "").strip()
    if not card or card.startswith("No fit card written"):
        return False, f"no fit card: {card[:60]!r}"
    return True, f"{session['selected_item']['id']}, three tools, card {len(card)} chars"


def score_2(record):
    """Stopped before suggest_outfit, with a message naming price, size or keywords."""
    if record["crashed"]:
        return False, f"crashed: {record['crashed'][:70]}"
    called = _tools_called(record)
    if called:
        return False, f"called {', '.join(called)} after an empty search"
    message = (record["session"]["error"] or "").lower()
    named = [word for word in ("price", "size", "keyword") if word in message]
    if not named:
        return False, f"message names nothing to change: {message[:60]!r}"
    return True, f"no model tool called; message names {', '.join(named)}"


def score_3(record):
    """search_results[0], selected_item and what both model tools received are one id."""
    reason = _no_card_reason(record)
    if reason:
        return False, reason
    session = record["session"]
    first = session["search_results"][0]["id"]
    chosen = session["selected_item"]["id"]
    got = ", ".join(f"{name} got {item_id}" for name, item_id in record["received"])
    ok = chosen == first and record["received"] == [
        ("suggest_outfit", chosen), ("create_fit_card", chosen),
    ]
    return ok, f"results[0]={first}, selected={chosen}, {got}"


_WORD = re.compile(r"[a-z0-9]+(?:['’][a-z]+)?")


def sentences(text):
    """Split on . ! ? followed by a space. A trailing emoji is not a sentence."""
    return [part for part in re.split(r"(?<=[.!?])\s+", text.strip()) if re.search(r"[A-Za-z]", part)]


def opening(text):
    return " ".join(_WORD.findall(text.lower())[:4])


def has_price(card, price):
    price = float(price)
    if price.is_integer():
        pattern = rf"\$\s?{int(price)}(?:\.00)?(?!\.?\d)"
    else:
        pattern = rf"\$\s?{price:.2f}(?!\d)"
    return re.search(pattern, card) is not None


def card_problems(card, item):
    problems = []
    count = len(sentences(card))
    if not 2 <= count <= 4:
        problems.append(f"{count} sentences")
    if not has_price(card, item["price"]):
        problems.append(f"no ${item['price']:g}")
    if item["platform"].lower() not in card.lower():
        problems.append(f"no '{item['platform']}'")
    return problems


def score_card_set(records):
    """One try of criterion 4: five cards, at least four of them pass."""
    cards = []
    for record in records:
        reason = _no_card_reason(record)
        if reason:
            cards.append({"card": None, "item": None, "problems": [reason], "opening": None})
            continue
        session = record["session"]
        card = session["fit_card"].strip()
        cards.append({"card": card, "item": session["selected_item"],
                      "problems": card_problems(card, session["selected_item"]),
                      "opening": opening(card)})

    for i, entry in enumerate(cards):
        if entry["card"] is None:
            continue
        same = [str(j + 1) for j, other in enumerate(cards) if j != i and other["opening"] == entry["opening"]]
        if same:
            entry["problems"].append(f"opens like card {', '.join(same)}")
        entry["ok"] = not entry["problems"]
    for entry in cards:
        entry.setdefault("ok", False)

    passed = sum(entry["ok"] for entry in cards)
    return passed >= 4, passed, cards


def size_allowed(wanted, listing_size):
    """
    criteria.md #5, written out on its own rather than by calling the tool's
    _size_matches — a check that reuses the code it checks can't catch it.
    The wanted size has to equal the listing's size or one half of a combined
    size. "8" counts as "US 8", and "W30" as the waist of "W30 L30".
    """
    wanted = wanted.lower().strip()
    size = re.sub(r"\(.*?\)", "", listing_size.lower()).strip()
    if wanted == size:
        return True
    for half in (part.strip() for part in size.split("/")):
        if wanted == half:
            return True
        if re.fullmatch(r"us\s*" + re.escape(wanted), half):
            return True
        if re.fullmatch(re.escape(wanted) + r"\s+l\d+", half):
            return True
    return False


def score_filters(record, scenario):
    """One query of criterion 5: nothing over the ceiling, nothing in the wrong size."""
    if record["crashed"]:
        return False, f"crashed: {record['crashed'][:70]}", []
    want = scenario["expect"]
    results = record["session"]["search_results"] or []
    bad = [
        f"{r['id']} size {r['size']} ${r['price']:g}"
        for r in results
        if r["price"] > want["max_price"] or not size_allowed(want["size"], r["size"])
    ]
    parsed = record["session"]["parsed"] or {}
    misread = ""
    if (parsed.get("size") or "").lower() != want["size"].lower() or parsed.get("max_price") != want["max_price"]:
        misread = f" (parsed as size={parsed.get('size')!r}, max_price={parsed.get('max_price')!r})"
    seen = [f"{r['size']} ${r['price']:g}" for r in results]
    if bad:
        return False, f"{len(bad)} violating: {'; '.join(bad)}{misread}", seen
    return True, f"{len(results)} results, 0 violating{misread}", seen


# ── the report ────────────────────────────────────────────────────────────────

def write_scored(rows, args):
    tries = args.tries
    by_criterion = {}
    for row in rows:
        number = row["scenario"].get("criterion")
        if number:
            by_criterion.setdefault(number, []).append(row)

    table = [
        f"| Criterion | Target | {' | '.join(f'Try {i}' for i in range(1, tries + 1))} | Verdict |",
        f"|---|---|{'|'.join(['---'] * tries)}|---|",
    ]
    details = []

    for number, (name, target, needed) in CRITERIA.items():
        crit_rows = by_criterion.get(number, [])
        cells, notes = [], [f"### {number}. {name}", ""]
        if not crit_rows:
            table.append(f"| {number}. {name} | {target} | {' | '.join(['—'] * tries)} | NOT RUN |")
            continue

        for k in range(tries):
            if number in (1, 2, 3):
                row = crit_rows[0]
                ok, why = {1: score_1, 2: score_2, 3: score_3}[number](row["tries"][k])
                cells.append("PASS" if ok else "FAIL")
                notes.append(f"- Try {k + 1}: **{'PASS' if ok else 'FAIL'}** — {why}")

            elif number == 4:
                ok, passed, cards = score_card_set([row["tries"][k] for row in crit_rows])
                cells.append(f"{'PASS' if ok else 'FAIL'} ({passed}/5)")
                notes.append(f"- Try {k + 1}: **{'PASS' if ok else 'FAIL'}** — {passed} of 5 cards pass")
                for i, entry in enumerate(cards, 1):
                    item = entry["item"] or {}
                    verdict = "pass" if entry["ok"] else "fail: " + "; ".join(entry["problems"])
                    notes.append(
                        f"    - card {i} ({item.get('id', '—')}, {len(sentences(entry['card'] or ''))} sentences, "
                        f"opens \"{entry['opening'] or '—'}\"): {verdict}"
                    )
                    if entry["card"]:
                        notes.append(f"      > {entry['card']}")

            elif number == 5:
                results = [(row["scenario"], *score_filters(row["tries"][k], row["scenario"])) for row in crit_rows]
                ok = all(r[1] for r in results)
                violations = sum(not r[1] for r in results)
                cells.append("PASS" if ok else "FAIL")
                notes.append(f"- Try {k + 1}: **{'PASS' if ok else 'FAIL'}** — "
                             f"{violations} of {len(results)} queries had a violating listing")
                for scenario, q_ok, why, seen in results:
                    notes.append(f"    - `{scenario['query']}`: {why} — sizes/prices returned: {', '.join(seen) or 'none'}")

        passes = sum(cell.startswith("PASS") for cell in cells)
        verdict = f"{'MET' if passes >= needed else 'MISSED'} ({passes}/{tries})"
        table.append(f"| {number}. {name} | {target} | {' | '.join(cells)} | {verdict} |")
        details += notes + [""]

    raw = max(
        (p for p in config.RESULTS_DIR.glob(f"run_*{'_' + args.label if args.label else ''}.md")
         if not p.stem.endswith("_scored")),
        key=lambda p: p.stat().st_mtime,
    )
    path = raw.with_name(raw.stem + "_scored.md")
    lines = [
        f"# Scored run log{f' — {args.label}' if args.label else ''}",
        "",
        "- Produced by: `score_eval.py::write_scored`, wrapping `run_eval.py::main`",
        f"- Raw output for the same run: `{raw.name}`",
        f"- Tries per scenario: {tries}, caching off, temperature {config.TEMPERATURE}",
        "- Criteria 4 and 5 run five queries each; try k is the k-th run of all five.",
        "",
        *table,
        "",
        "## Why each try passed or failed",
        "",
        *details,
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {path.relative_to(config.ROOT)}\n")
    print("\n".join(table))


if __name__ == "__main__":
    run_eval.main()
