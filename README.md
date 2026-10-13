# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

FitFindr is a thrifting agent. You tell it what you want in one sentence — "a
vintage graphic tee under $30, size M" — and it searches a file of 40 secondhand
listings, picks the best match, and works out what you could wear it with from
the wardrobe you give it. What you get back is the listing (title, price,
platform), one or two outfit ideas that name pieces you already own, and a short
caption you could post. If nothing in the listings fits, it stops there and says
which part of your request to change.

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Searches `data/listings.json` for listings that match the
  description keywords, the size, and the price ceiling, and ranks them.
- **Inputs:** `description` (str) — keywords, e.g. "vintage graphic tee";
  `size` (str or None) — a size such as "M", "S/M", "US 8.5" or "W30", where
  None skips the size filter; `max_price` (float or None) — inclusive ceiling in
  dollars, where None skips the price filter. A size matches when it equals one
  of the sizes the listing offers, so "M" matches "M", "S/M" and "M/L" but not
  "XL" or "US 9".
- **Returns:** A list of listing dicts, best match first, at most
  `config.SEARCH_RESULT_LIMIT` (10) of them. Each dict has `id` (str), `title`
  (str), `description` (str), `category` (str), `style_tags` (list[str]),
  `size` (str), `condition` (str), `price` (float), `colors` (list[str]),
  `brand` (str or None) and `platform` (str). Ranked by keyword score: 3 points
  per keyword found in the title, 2 in tags/colors/category, 1 in the
  description or brand; ties go to the cheaper listing.
- **When it has nothing:** An empty list `[]` — never None, never an exception.
  That includes a description with no usable keywords.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits built around the new
  item, using the pieces in the user's wardrobe.
- **Inputs:** `new_item` (dict) — one listing dict as returned by
  `search_listings`; `wardrobe` (dict) — `{"items": [...]}` where each item has
  `name` (str), `category` (str), `colors` (list[str]), `style_tags`
  (list[str]) and `notes` (str or None).
- **Returns:** A non-empty string of outfit suggestions, under about 120 words,
  naming wardrobe pieces by the names they have in the wardrobe.
- **When it has nothing:** If `wardrobe["items"]` is empty (or the wardrobe is
  missing), it still returns a non-empty string — general styling advice for
  the item, with no claims about what the user owns. If the model returns
  nothing, it returns a one-line fallback suggestion built from the item title.

### `create_fit_card`

- **What it does:** Asks the model to write a short social-media-style caption
  about the find.
- **Inputs:** `outfit` (str) — the string from `suggest_outfit`; `new_item`
  (dict) — the listing dict for the item.
- **Returns:** A string of two to four sentences that mentions the item, its
  price and its platform, with no hashtags.
- **When it has nothing:** If `outfit` is empty or whitespace it does not call
  the model and returns a string beginning "No fit card written — there was no
  outfit to build it from." (a message, not an exception, and not an empty
  string).

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in
`session["error"]` that names what to change (the price limit, the size, or the
keywords) and return the session — `suggest_outfit` and `create_fit_card` are
not called, and `session["fit_card"]` stays `None`. Otherwise take the first
result as `session["selected_item"]` and go on to `suggest_outfit`, then
`create_fit_card`.

**Where it lives:** `agent.py::run_agent`. The loop asks `agent.py::_next_step`
what to do next by looking at the session; the empty-search stop is the
`if not session["search_results"]: return None` line in `_next_step`, and the
error message is built by `agent.py::_nothing_found_message`.

**How the query is parsed:** Regular expressions, in `agent.py::parse_query` —
no model call. A price comes from phrases like "under $30" or "$30", a size
from "size M", "size W28", "size 8.5", or a word like "medium", and whatever is
left (minus filler like "looking for") is the description. A missing price or
size becomes `None`, which tells `search_listings` to skip that filter.

**What moves through the session:** In order: `query` → `parsed`
(description, size, max_price) → `search_results` (and `searched = True`) →
`selected_item` (the first result) → `outfit_suggestion` → `fit_card`. Each
tool call reads its inputs from the session and writes its result back, so
`selected_item` is the same dict that `suggest_outfit` and `create_fit_card`
receive. `error` is set only when the run ends early.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

```
$ python app.py ask 'vintage graphic tee under $30, size M'
  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   Hey bestie! Here are two cute ways to style your new butterfly baby tee:

**Outfit 1:** Pair it with your **Baggy straight-leg jeans, dark wash** and **Chunky white sneakers**. Add the **Brown leather belt**.
*Why it works:* The fitted tee balances the baggy dark denim, and the sneakers keep the Y2K vibe fresh and effortless. 

**Outfit 2:** Layer it under your **Vintage black denim jacket**, paired with your **Wide-leg khaki trousers** and **Black combat boots**.
*Why it works:* The cropped jacket highlights the waist of the trousers, while the boots add a cool edge to the sweet butterfly print.

  Fit card: Just scored this dreamy butterfly baby tee on Depop for $18 and I am obsessed with the Y2K energy. I put together two easy ways to style it, from baggy denim to a cool jacket layered look. Let me know which fit is your favorite!🦋

1 model calls this session, 1 served from cache, 313 prompt + 55 output tokens
```

The empty-search path, which doesn't touch the model:

```
$ python app.py ask 'designer ballgown size XXS under $5'
  Nothing matched 'designer ballgown', size XXS, under $5. You could try different or fewer keywords, like a style (vintage, y2k) or a type of item (jacket, jeans).

0 model calls this session
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; print([(r['title'], r['size'], r['price']) for r in search_listings('graphic tee', max_price=30)])"
[('Graphic Tee — 2003 Tour Bootleg Style', 'L', 24.0), ('Y2K Baby Tee — Butterfly Print', 'S/M', 18.0), ('Vintage Band Tee — Faded Grey', 'L', 19.0), ('Vintage Graphic Hoodie — Faded Black', 'L', 26.0), ('Mesh Long-Sleeve Top — Black', 'S/M', 15.0), ('Oversized Crewneck Sweatshirt — Vintage Navy', 'XL (fits oversized)', 20.0), ('Low-Rise Cargo Pants — Khaki', 'W29', 27.0)]
```

```
$ python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
[]
```

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
Here are two ways to style your new Vintage Levi's 501 Jeans:

**Outfit 1**
*   **Top:** White ribbed tank top
*   **Outerwear:** Vintage black denim jacket
*   **Shoes:** Chunky white sneakers
*   **Accessories:** Black crossbody bag
*   *Why it works:* The crisp white tank and sneakers balance the rugged indigo denim for an effortless, classic look.

**Outfit 2**
*   **Top:** Oversized grey crewneck sweatshirt
*   **Shoes:** Black combat boots
*   **Accessories:** Brown leather belt
*   *Why it works:* Tucking the chunky sweatshirt in with the belt plays with proportions while the boots toughen up the medium wash.
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
Scored these vintage Levi's 501 jeans on Depop for just $38 and I am obsessed. Paired them with crisp white sneakers for the ultimate effortless streetwear look.
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:* A query parser for `agent.py` that pulls a price, a size
  and a description out of a sentence like "looking for a vintage graphic tee
  under $30, size M".
- *What came back:* Code that looked right but never found a size. I ran nine
  made-up queries through `parse_query` and printed the result, and `size` was
  `None` every time, with "size M" still sitting in the description. Two
  things were wrong. The `\b` word boundaries in the regex had been turned
  into backspace characters when the code was written out, so the pattern
  could never match. And the size alternatives were in the wrong order, with
  `s` before `s/m`, so "S/M" would have come out as just "S" once the first bug
  was gone.
- *What I changed:* Put the backslashes back, and listed the longer sizes first
  (`s/m`, `l/xl`, `xxl`) before the single letters. I also added "dollars" to
  the filler words after one query left it in the description. Then I re-ran
  the same nine queries until each gave the size and price I expected.

**Moment 2**

- *What I asked for:* A `create_fit_card` that writes a short caption from the
  item and the outfit, mentioning the price and platform once.
- *What came back:* Once I ran it on the real model, the first caption said
  "this precious Y2K butterfly baby tee I just listed on Depop". It read like the seller
  posting an ad, when the person using FitFindr is the one who bought it. The
  price and platform were there, so nothing in my criteria would have caught it.
- *What I changed:* Added a line to the prompt saying the writer is the buyer
  who just found the piece, not the seller. I re-ran the same query and got
  "Just scored this dreamy butterfly baby tee on Depop for $18", which is what
  I wanted.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

Each step is one `trace.step()` call in `agent.py::run_agent` (and two in
`agent.py::_nothing_found_message`). The `search_listings (via MCP)` lines are
the MCP call: the agent sends the arguments to `mcp_server.py` through
`mcp_client.call_tool` and gets the listing dicts back.

**Happy path** — cache off, so both model calls are real

```
$ python app.py ask 'vintage graphic tee under $30, size M' --trace
[1] parse_query
      in:  vintage graphic tee under $30, size M
      out: description='vintage graphic tee', size='M', max_price=30.0
[2] search_listings (via MCP)
      in:  description='vintage graphic tee', size='M', max_price=30.0
      out: 8 items: Y2K Baby Tee — Butterfly Print, Vintage Polo Shirt — Forest Green, Vintage Knit Vest — Argyle Brown/Cream … +5 more
      →    branch: results — take the first
[3] select
      in:  search_results[0] of 8
      out: lst_002 · Y2K Baby Tee — Butterfly Print ($18, depop)
[4] suggest_outfit
      in:  new_item=lst_002 · Y2K Baby Tee — Butterfly Print ($18, depop), wardrobe=10 items
      out: **Outfit 1** *   **Pieces:** Y2K Baby Tee — Butterfly Print, Baggy straight-leg jeans, dark wash, Chunky white…
[5] create_fit_card
      in:  outfit=(481 chars), new_item=lst_002 · Y2K Baby Tee — Butterfly Print ($18, depop)
      out: I still can't believe I scored this Y2K butterfly baby tee on Depop for just $18. The pink and purple graphic …
[6] stop
      →    nothing left to run — all three tools called

  Found:    Y2K Baby Tee — Butterfly Print — $18.0 on depop

  Outfit:   **Outfit 1**
*   **Pieces:** Y2K Baby Tee — Butterfly Print, Baggy straight-leg jeans, dark wash, Chunky white sneakers
*   **Why it works:** The fitted tee balances the voluminous jeans for a classic Y2K silhouette.

**Outfit 2**
*   **Pieces:** Y2K Baby Tee — Butterfly Print, Wide-leg khaki trousers, Vintage black denim jacket, Black combat boots
*   **Why it works:** The cropped jacket and pink-and-purple print add a sweet pop of color against neutral, utilitarian trousers.

  Fit card: I still can't believe I scored this Y2K butterfly baby tee on Depop for just $18. The pink and purple graphic print is so sweet, and it looks amazing paired with baggy dark-wash jeans for that classic silhouette.

2 model calls this session, 594 prompt + 172 output tokens
```

Why each step: [1] the query has to be split into the three search inputs
before anything else can run. [2] `_next_step` sees `searched` is False, so it
searches. The list came back non-empty, so the branch goes on rather than
stopping. [3] Only one item goes forward, and it's the top-ranked one. [4] and
[5] each read their inputs back out of the session — the same `lst_002` goes
into both. [6] `_next_step` returns None because `fit_card` is filled in.

**Empty search** — visibly shorter after the branch: no `suggest_outfit`, no
`create_fit_card`, and no model calls

```
$ python app.py ask 'designer ballgown size XXS under $5' --trace
[1] parse_query
      in:  designer ballgown size XXS under $5
      out: description='designer ballgown', size='XXS', max_price=5.0
[2] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=5.0
      out: [] (empty)
      →    branch: empty — stop before suggest_outfit
[3] search_listings (via MCP)
      in:  description='designer ballgown', size='XXS', max_price=None
      out: [] (empty)
      →    looser search for the message: price limit dropped
[4] search_listings (via MCP)
      in:  description='designer ballgown', size=None, max_price=5.0
      out: [] (empty)
      →    looser search for the message: size dropped
[5] stop
      out: Nothing matched 'designer ballgown', size XXS, under $5. You could try different or fewer keywords, like a sty…
      →    suggest_outfit and create_fit_card not called

  Nothing matched 'designer ballgown', size XXS, under $5. You could try different or fewer keywords, like a style (vintage, y2k) or a type of item (jacket, jeans).

0 model calls this session
```

Steps [3] and [4] are the message working out what to suggest: it re-runs the
search with the price dropped, then with the size dropped. Both still came back
empty, so the keywords are what's in the way, and that's what the message names.

### Failure modes, triggered on purpose

**1. Empty search.** Already handled by the branch from unit 3 — no change
needed. The message names whichever filter is in the way:

```
$ python app.py ask 'designer ballgown size XXS under $5'
  Nothing matched 'designer ballgown', size XXS, under $5. You could try different or fewer keywords, like a style (vintage, y2k) or a type of item (jacket, jeans).

$ python app.py ask 'silk slip dress under $10'
  Nothing matched 'silk slip dress', under $10. You could raise your price limit — the cheapest match is $28.

$ python app.py ask 'platform sneakers size 12'
  Nothing matched 'platform sneakers', size 12. You could try a different size — matches come in US 7, US 8, US 8.5, US 9.
```

**2. Empty wardrobe.** Already handled in `tools.py::suggest_outfit` — it
switches to a general-advice prompt when `wardrobe["items"]` is empty. No crash,
no empty string, and it doesn't claim the user owns anything:

```
$ python app.py ask 'denim jacket under $50' --empty-wardrobe --trace
(running with an empty wardrobe)
...
[4] suggest_outfit
      in:  new_item=lst_007 · Denim Jacket — Light Wash, Cropped ($42, poshmark), wardrobe=0 items
      out: This Wrangler denim jacket is a vintage classic! Since it’s a cropped size S in excellent condition for $42, h…
...
  Outfit:   This Wrangler denim jacket is a vintage classic! Since it’s a cropped size S in excellent condition for $42, here is how to style it:

*   **Outfit 1:** Throw it over a flowy midi dress with white canvas sneakers for an effortless high-low mix. 
*   **Outfit 2:** Pair it with high-waisted black leggings and a plain white t-shirt for easy streetwear vibes. 

**Shoes:** Go with classic low-top sneakers or chunky black boots. 

**Layers:** On colder days, layer a grey cotton hoodie underneath, letting the hood pop out over the collar.
```

**3. Model unavailable.** One character of the key changed, a query I hadn't
asked before, cache off. This one **needed a handler.** Before:

```
$ python app.py ask 'corduroy wide-leg pants under $40'

ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com.

1 model calls this session
```

No stack trace, but only because `app.py::main` has a last-resort
`except Exception`. `run_agent` itself raised, so the session was thrown away:
the user never saw the corduroy pants the search *had* found, the exit code was
1, and `run_eval.py` would have logged the try as CRASHED. I added
`agent.py::_model_unavailable`, which `run_agent` calls when `suggest_outfit` or
`create_fit_card` raises `ModelUnavailable`. It puts a message in
`session["error"]` and returns the session. After:

```
$ python app.py ask 'corduroy wide-leg pants under $40' --trace
[1] parse_query
      in:  corduroy wide-leg pants under $40
      out: description='corduroy wide-leg pants', size=None, max_price=40.0
[2] search_listings (via MCP)
      in:  description='corduroy wide-leg pants', size=None, max_price=40.0
      out: 4 items: Corduroy Wide-Leg Pants — Rust, Low-Rise Cargo Pants — Khaki, Straight Leg Khaki Trousers — Olive … +1 more
      →    branch: results — take the first
[3] select
      in:  search_results[0] of 4
      out: lst_005 · Corduroy Wide-Leg Pants — Rust ($32, depop)
[4] suggest_outfit
      in:  new_item=lst_005 · Corduroy Wide-Leg Pants — Rust ($32, depop), wardrobe=10 items
      out: ModelUnavailable: The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh k…
      →    model unreachable — stopping, error in session

  Found Corduroy Wide-Leg Pants — Rust ($32 on depop), but the model couldn't be reached to write the outfit ideas. The model rejected your API key. Check GEMINI_API_KEY in your .env file, or create a fresh key at aistudio.google.com. The search doesn't need the model, so once that's fixed, ask again.

1 model calls this session
```

It says what broke (the model, at the outfit step), why (the key was
rejected), what to do (check the key or make a new one), and keeps the result
of the search that did work. Key put back afterwards.

**4. MCP server unreachable** (not one of the three, but the MCP move added
it). I pointed `mcp_client.SERVER` at a file that doesn't exist:

```
error: The listing search couldn't be reached — the MCP server in mcp_server.py didn't answer. Check that `python mcp_server.py` starts without an error, then ask again.
fit_card: None
```

**On the MCP move:** `search_listings` is registered in
`mcp_server.py` with FastMCP, under the same name and the same typed inputs as
the Tool Inventory (`description: str`, `size: str | None`,
`max_price: float | None`). The description is written for a caller who can't
see my code: units on the price (inclusive, US dollars), what "size matches"
means, every field in a returned listing, and that nothing found is `[]`, not
null or an error. In `agent.py` the direct call became `_search()`, which calls
`mcp_client.call_tool("search_listings", {...})`. All three searches go through
it — the main one in `run_agent` and the two looser re-searches in
`_nothing_found_message` — so the agent never calls `search_listings`
directly now. `suggest_outfit` and `create_fit_card` are unchanged.

Nothing behaved differently. I called both paths on the same input and
compared: `call_tool(...) == search_listings(...)` was `True` (10 listing
dicts, `price` still a float, not a string), and the impossible query came
back as `[]`, a real empty list, so the branch's `if not
session["search_results"]` still works. The sample query from unit 3 printed
the same item, outfit and fit card. The one visible difference is speed: every
`call_tool` starts the server as a new process, so a search went from about
1 ms to about 1 s (five timed calls: 1.78, 1.01, 0.90, 0.96, 1.10 s), and the
empty-search path (three searches) is the
slowest path now even though it makes no model calls.



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
