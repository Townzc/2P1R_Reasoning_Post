# Post-E030 registered continuation — September16,2026

The owner explicitly requested execution of the supplied post-E030 resume plan,
and started the existing server. This amendment supersedes the previous pause;
it does not revise any completed observation, data release, optimizer recipe or
scientific endpoint. Source plan SHA256:
`02ca48815b22c0cff62caa7870f17b9653874a4e5d88b1504cfdb8300f11ba90`.
The plan and its handoff manifest were independently checked before execution.

## Fixed scientific scope

Continue E031–E036: two32-update prep parents from the original C0 LoRA and
four256-update main children from their respective prep parents. Original base,
rank16 adapter, FP32 parameters/BF16 compute, SDPA, token-weighted AdamW,
seed17, batch16/microbatch1, peak5e-5, original absolute LR vectors, datasets,
schedules, checkpoint steps and stopping/scoring rules remain unchanged.
E030 is neither rerun nor used as a parent. No alternative model, LR, seed,
RL, n8, forced prefix or reserved holdout is admitted.

Immediately after each prep parent, measure the first fixed batch of its
registered probe evaluation and discovery sampled evaluation. Commit these
requests to the same eventual evaluation, with the same RNG chain. Then finish
all four children in registered order, with128-update midpoint snapshots.
Complete registered evaluations and four fixed train diagnostics thereafter.
Scores, significance and NLL changes do not decide which cells run.

## Durable units and request identity

Admit the next saveable unit, not a forecast for the entire unfinished grid.
Main segments end at absolute64/128/192/256; recovery commits every16 updates
and at the segment boundary. Recovery includes adapter, AdamW, all Python,
NumPy, torch and CUDA RNG states, the absolute schedule position and identity
hashes. Resume does not create a new warmup, seed, parent or logical run.
Immutable attempt histories preserve uncommitted physical work; scientific dose
is counted only from the committed recovery trajectory.

Evaluation uses the original eight-output batch and original greedy/sampled
recipe (seed2026091603, sampled temperature0.7/top-p0.95/top-k0, max512).
A stable request binds adapter, split, question, sample and decoding protocol.
Each batch durably stores raw outputs and pre/post RNG before CPU scoring.
Completed outputs are not sampled again. An interrupted charged batch without
raw output stops for reconciliation; it is not automatically regenerated.
Caller training RNG and mode are restored around evaluation.

Profiles record nonpadding input tokens, retained and padded generated tokens,
combined model generation time, raw-save and CPU-score time separately by
checkpoint and task/view. Prefill/decode-only time is null when not measured;
combined model time is explicitly labeled as including prefill. No shortened
output cap, hidden token pruning or changed verifier is used for speed.

## Fixed diagnostic release

`release_resume_r1` selects16 original training questions before any new main
training, four per anchor-family × existing B-reference target-degeneracy
stratum, using the unchanged assignment seed and SHA ordering. ManifestSHA256
`1435cf011cb0f3224f97f08d7713707bd8c745cc4e80ba3daf1d1b184fd9221b`.
The same16 questions receive one greedy output at each of four endpoints:
64 additional generations. Small A/B-reference teacher-forced NLL checks are
allowed only as bounded forward passes. These are descriptive training
observations, not held-out generalization evidence. Supplementary construction
analysis separates target value, exact input multiset and operation legality
from local arithmetic consistency; unavailable intermediate evidence is NA.
The original correctness score and denominator remain unchanged.

## Finite cumulative resource package

The new package allows at most8 powered-on hours or CNY65 of compute-rental
proxy, whichever is reached first, within the owner's existing monetary
authority. Setup, idle time, transfer and multiple worker segments count.
The launch ledger persists across process restarts and any verified separate
power windows. Individual worker slices are bounded by GNU timeout to at most
7200 seconds plus15-second kill grace, inside the global deadline. Reserve
1500 seconds for independent export and provider-confirmed shutdown.
An authenticated provider timer is an additional shutdown backstop.
No recharge, new machine, storage purchase or paid API is authorized.

Generation accounting begins at592 actual historical attempts. Original
remaining4128 plus diagnostic64 gives4192 new and4784 cumulative, within the
unchanged4864 cap;80 remain as fault reserve, not additional experiments.
The historical24 receipts/8915 process seconds are immutable and separately
reported. Each new worker receives a unique receipt; power-window cost is a
proxy at the currently verified rate, not an invoice.

Initial available data disk is about5.6GiB. Planned new adapters and rolling
recovery states fit without historical cleanup. Checkpoints and raw outputs
are exported incrementally and SHA-verified independently. Only this code's
obsolete rolling recovery states are pruned after replacement readback.
E015 unique weights, original releases, failed runs and prior receipts stay
protected. Full local analysis and publication follow verified shutdown.
