# A9 LogiQA2.0 pilot — frozen inputs and source

Authority ecda09143c135a64512fec346fe13d38002c7951, section 4 explicitly exempts this new data/scorer path from prereview and requires full post-audit. Evaluation and sampling only; no training or future task admission.

Three endpoints: 4B and9B full test1572greedy each; unfinetuned9B sampled300trainrows x8 independent calls. Frozen literal template, disable-thinking renderer, max2048, seeds9000+row*8+draw. Exact input tokenization and context checks pass. Ten scoring cases plus literal substitution and20-word boundary checks pass. Upper forecast $15.323168088/20 includes2048tokens for EVERY output and1.5buffer. The prior A9 ledger already reserves20; do not double count.

Source repo csitfun/LogiQA2.0@955e1d3df6c59d9bfb44d9913da1e1a27ec14e18; input texts and reversible prompt tokens stay private. Public input lists contain row identifiers, original IDs, gold labels, counts and cryptographic hashes. Original numeric IDs are not unique:338duplicate trainIDs and4duplicate testIDs beyond the first occurrence. Preserve every source row, use split+original line for identity, and sort by numeric ID stably before Random(20261120).sample(300).

Primary passage-only overlap:228testrows exact,311testrows13gram. Supplemental passage+question:217exact,54413gram. No rows filtered. Unicode word tokenization and casefold apply only to13gram; exact matching uses original text. Exact matching and13gram hitlists contain IDs only. This overlap is material for any later training interpretation.

Scoring takes the last balanced box; unwraps text{}; removes parentheses/brackets/braces, periods and whitespace; requires exactly uppercaseA/B/C/D. Missing, invalid or unfinished outputs are wrong. Answer-only is fewer than20whitespace-separated words before the last box. All attempts and errors remain available. Source prices are frozen from official models.json via the web tool; urllib retrieval403 occurred during CPU preparation before any model call.

Pending: generate, publish timestamped ecda0914 prescore bindings, score, then deliver all5544outputs for independent review. Owner decides any subsequent training after Claude audit.
