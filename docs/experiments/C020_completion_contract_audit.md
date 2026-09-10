# C020: saved-stream completion diagnosis and prospective dose inventory

2026-09-10 UTC. CPU-only preparation authorized by the owner's request to improve
evaluation and capability preservation. No GPU launch, paid API, server contact,
fresh development generation or new training is part of this phase.

The boundary idea and preliminary count inspection occurred after E016. This is
explicitly post-hoc diagnosis, not a new unbiased evaluation or a revision of
E016's frozen scores/gates. Publish code before writing immutable audit outputs.

Reverify all 160 saved streams: E013 base/tuned on the old16 parents, and E016
base/E015 on64 parents. Preserve strict and marked scores. Find the earliest
native EOS, complete line-anchored new-question header, invalid special token or
length cap, using generated tokens only. The CPU reference checks successive
decoded prefixes so a delimiter split across tokens is handled without assuming
one delimiter token. Retain trigger tokens, distinguish boundary from native
EOS, and require a correct unambiguous marked answer before a valid stop.
Never use the gold answer to decide when to stop. Conflicting claims, missing
answers, invalid specials and incomplete streams must not become successes.

Report original truncation/boundary intersections, saved-prefix candidate counts,
exact retained-token counts and sums of batch maximum lengths. These are saved
trace calculations, not observed speedups or guaranteed runtime outputs. Changing
finished-row handling can affect GPU batch numerics. The CPU reference is not a
production GPU stopping implementation. No official-test or unused dev text is
opened; the remaining432 development parents stay reserved.

Separately inventory a review-only two-epoch schedule over the existing253
accepted single-response parents from the nominal256 C017 pool. Keep all three
unavailable parents visible. Use epochs shuffled by seeds17/18, batch8,
microbatch1,64 updates,506 whole-response presentations and no length filtering.
Report exact existing metadata token totals and all batch indices. Raw response
reconstruction, chain-quality review and fresh exact-token checks remain required
before any training release. This inventory neither validates new supervision
nor selects a successful training policy.

Estimate one rank16/alpha32 LoRA candidate over q/k/v/o/gate/up/down projections
from the pinned Qwen configuration, freezing embeddings, norms, head and biases.
Report trainable tensor bytes, excluding metadata and optimizer state. This is
an alternative proposal; it does not change the incumbent base or the SFT method
of any existing or future scientific arm without review.

Meaningful fixtures cover stop/score independence, false EOS attribution,
multi-token delimiters, missing/contradictory answers, partial/inline headers,
special tokens, length caps, and native EOS before later padding. No classifier,
LLM judge, unrestricted last-number extraction or proof-validity claim is added.
