# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
Not 5 of 5, because two parts of this path are outside my control. My search is
a plain keyword match over titles, tags and descriptions, so a phrasing the
listings don't use ("t-shirt" for "tee" is covered, "something warm" is not)
can come back empty, and my query parser is a handful of regexes that will
misread an oddly worded size or price. Both tools that call the model can also
fail on a rate limit. Not 3 of 5, because for a plain query like "vintage
graphic tee under $30" none of that should be in play.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
5 of 5 because nothing on this path is random. The stop is decided by whether
`search_listings` returned an empty list, and `search_listings` is plain code
with no model in it, so the same query gives the same answer every time.
"Names what to change" is checkable: the message has to mention at least one
specific thing the user can alter — the price limit, the size, or the keywords
— rather than saying "no results".

---

## 3. Something about state

For a query that matches, `session["selected_item"]["id"]` equals
`session["search_results"][0]["id"]`, and that same id is the one passed into
`suggest_outfit` and into `create_fit_card` — checked by wrapping both tools to
record the `id` of the item they receive — in 5 of 5 tries.

**Why this target:**
5 of 5 because this is dictionary assignment, not a judgment call: the loop
writes `selected_item` once and reads it back for each later tool. If the ids
differ even once, something is overwriting or re-searching, which is a bug and
not noise. I check the id the tools actually receive, not just what the session
holds, because a session that looks right can still be bypassed by a variable
passed around it.

---

## 4. Something about the fit card

Run five matching queries that find five different items, with the cache off.
A card passes when it is two to four sentences long, contains the item's price
(for example "$24") and its platform name (for example "depop"), and does not
begin with the same first four words as any of the other four cards. At least 4
of the 5 cards pass.

**Why this target:**
The words will differ run to run, so I'm not checking the words; I'm checking
the things I'd be unhappy to see missing — a price, a platform, a card that
runs on past a caption, or five cards that all open the same way. I allow one
miss because the prompt asks for these things and the model usually, not
always, follows it, and counting sentences by splitting on punctuation is
slightly unreliable ("Levi's 501s. Obsessed." counts as two). Not 3 of 5,
because the price and platform are given to the model in the prompt and
leaving one out is a real failure.

---

## 5. Your choice

For five queries that each include a size and a price ceiling, every listing in
`session["search_results"]` costs no more than the ceiling and has a size that
equals the requested size or one half of a combined size ("M" allows "M", "S/M"
and "M/L" but not "XL", "L/XL" or "US 9"). Zero violating listings across all
five queries — 5 of 5 tries.

**Why this target:**
5 of 5, zero tolerance, because filtering is plain code and a violation is a
bug I can point at, not variation. I picked the size rule on purpose: the
listings mix "M", "S/M", "XL (oversized)", "US 9" and "W30 L30", and a lazy
substring test ("l" in "xl") quietly returns the wrong sizes while still
looking like a working search. A price ceiling that is exceeded by even $1
would make the user trust the search less than an empty result would.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
