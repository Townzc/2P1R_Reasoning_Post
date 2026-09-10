# C019: saved development answer-format and capability audit

2026-09-10 UTC. The owner requested the next experiment or offline planning,
with notification before server startup. This CPU-only audit reuses E013's
already observed 16 development parents and 32 saved base/final generations.
No new model call, split selection, server contact or budget reservation.

The original strict scores remain unchanged. A separate, explicitly post-hoc
`marked_answer_v1` extractor reads boxes, the same line after `####`, and
line-anchored `Answer:` / `The answer is` / `So the answer is` statements.
Prose claims must contain one unambiguous scalar; unmarked working is excluded.
All marked claims must resolve and agree. A line starting a new Problem,
Question or Q ends the scored segment; all original tokens remain recorded.
This extractor never receives the reference answer. Comparing with the gold
occurs afterward, using exact rational equality.

Report three separate diagnostic counts: marked answer correctness, correctness
with actual EOS and no truncation, and clean correctness additionally excluding
a generated new-problem continuation. Report parsing, EOS, truncation and all
paired gains/losses over the original denominator of 16. No proof verification
is implied. A correct number can coexist with faulty intermediate reasoning.

The raw token streams, original scores and input identities must first pass
the frozen E013 auditor. Source publication precedes producing immutable C019
outputs. The six adversarial fixture tests cover conflict, continuation,
truncation, malformed numbers, accidental working-number extraction and the
hash-marker tail issue. This is an audit developed on observed output, not an
unbiased new evaluation. Future use requires freezing it before new generation.

The operational comparison is E013 base versus its tuned endpoint, not E015.
E015 has no development predictions yet. The next proposed independent
calibration should distinguish baseline format/capability from tuning damage
before selecting a scientific training scale.
