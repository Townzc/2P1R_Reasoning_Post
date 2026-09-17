# E037 — frozen-endpoint paired-goal diagnostic

The owner requested execution of the September16 post-E036 handoff. This new
inference-only phase supersedes the previous pause; it does not authorize the
conditional G-single/G-paired training proposal. No optimizer or new checkpoint
is created. E018, E030, and E031–E036 outcomes, failures, doses and ledgers remain
unchanged. The source plan SHA256 is
`2fc679baaa890a7e5ce8973292677d44dccfcc44a7f63d4ca70319d1d441ff68`;
the supplied package SHA256 is
`589c22b6a9e76f2bf7185c3eaf91c12fba390f1d33d8da85d9926a7a6d7431bd`.

Use E033 C-S, E034 C-P, E035 B-S and E036 B-P final step256 adapters, bound by
endpoint_identities.json. Qwen2.5-1.5B Base, pinned original revision/tokenizer,
FP32 parameters, BF16 autocast, SDPA, TF32 off. No training, model substitution,
old-probe repetition, hyperparameter search, or outcome-dependent queue selection.

CPU selection fixes24 new distinct-number groups in the original1..40 number
and10..100 integer target domain. Each ordered one-hole skeleton has two distinct
goals uniquely solved by different candidates among +,-,*,/. Six unordered
operator pairs have4 groups each; each operator has12 correct labels and6 in
each target position. Root/internal holes and >=8 families are required.
Exclude selected-hole identity/absorption, division by zero and target invariance;
tag other degeneracy. Check number multiset and existing number-family hashes
against used/protected allocations without opening sealed question bodies.
Generation seed20260917; all selection is outcome-blind, finite and CPU-only.

F gives the original free-construction instructions. H additionally gives the
one-hole skeleton and requires the full completed expression with its ordered
AST unchanged. C evaluates each completed expression without stating its target.
F accepts every strict legal expression reaching the target. H separately reports
strict skeleton-following correctness and free target correctness. C uses exact
rational arithmetic. Prior stopping contract and answer/step style are unchanged.

Fixed queue: all four endpoints receive48 F,48 H,48 C greedy requests first;
each state also receives48 local operator contexts. Then all four receive48 F
and48 H prompts with n=4 sampling, temperature0.7, top_p0.95, top_k0. Batch8,
max_new_tokens512, independent evaluation seed2026091703 with durable RNG and
request identities. Total2112 autoregressive generations; fresh cap2304 includes
192 fault reserve. Historical4784/4864 and unused80 are immutable and separate.

Operator scores: retokenize full prompt + fixed valid answer prefix + candidate,
using the common token prefix; score every differential continuation token and
no EOS/future numeral/result. Prefix is identical across paired goals, ends
before the hole, and reveals no filled hole/result. Record full-vocabulary raw
log probabilities, candidate probability mass, candidate-normalized probabilities,
actual forward calls/tokens/seconds/memory. Four single-token scores can use one
forward. Unavailable token alignment remains explicitly missing and does not
remove the generation pair. Planned192 contexts/768 candidate scores, no
additional autoregressive sampling.

Report raw numerators/denominators, F/H strict and C accuracy, paired both-goal
success, strict H operator switch, separate Fwrong/Hright rescue and converse
loss, same ordered expression failures, and target/operator margins D_goal.
Sample pairs use the same sample_index, but the24 groups are the statistical
units. Fixed10000 group and skeleton-family bootstrap replicates, seed2026091704,
are exploratory problem variation and do not estimate training-seed uncertainty.
Do not claim a pure search/routing mechanism, structure OOD, or equivalence.

Independent resource limits: one existing A800, cumulative powered-on7200s or
CNY20, whichever first, at live verified price; includes setup/idle/backup.
Conservative power-on2026-09-17T02:06:00Z, verified7.98CNY/hour. Provider timer
04:05UTC, work deadline04:06UTC minus600s backup/shutdown reserve. Per-process
finite timeout with15s kill guard, immutable receipts, persistent separate
ledgers; no automatic regeneration of ambiguous charged batches. Minimum1GiB
before each generation batch (launcher basic preflight0.5GiB). Preserve all
historical checkpoints/E015. No paid storage/download/new instance needed.

Publish execution source/release before inference. Independently copy and verify
all new outputs and latest receipts, then confirm provider shutdown and clear
our timer. Analyze locally after shutdown. End with results and a conditional
next proposal; do not execute new training without the owner's next instruction.
