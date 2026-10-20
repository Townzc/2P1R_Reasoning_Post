# Prepared A/D training and endpoint leaf modules

No actual training, model loading, generation, symbolic scoring or scientific
bootstrap has been run. Full runtime CR/A2-lite, actual input A1, cost/window,
asset/source binding, permanent dispatch/unit guards, child exit before vLLM,
raw-output verification and bounded collection are still required. This draft
adds no independent code-only admission gate. Original live data sources stay
unchanged. A7 from the selected smoke arm will be reused, never retrained.

Training retains the three original arms, FP32 parameters/AdamW state and BF16
autocast, unpadded one-answer microbatches, exact token-normalized gradients,
whole-answer q/q+1 exposure, U=ceil(B/64000), r64/alpha128/dropout0/seven projections
or full parameters. Ceil(5%U) warmup, step1-based cosine endpoint10%, gradient
clip1, AdamW betas(.9,.999)/eps1e-8/weight_decay0 and4threads are explicit proposed
operational details for the full-path CR. They are not an already accepted
runtime or an independent owner amendment. Native EOS151645/final ignored
newline differ from the old base training recipe. No old trainer is invoked.

An admitted journal must fence every update before work and retain failures.
The final state saves every trainable tensor (full model in full arm), optimizer,
RNG, complete schedule/LR vector and dose before FP32 merge/BF16 model export.
The old snapshot/save helper is reused for serialization/readback only; its
LoRA-only load/restore path is not used for the new schema. Synthetic tests mock
CUDA synchronization and the actual long model. They do not establish H100
memory feasibility, model speed, full-size state memory/storage or future cost.

Endpoint leaf code enumerates all3300 requests per model: MATH500 four samples
and greedy, AIME24/25 and AMC23 eight samples each. Seeds0–3/0–7, T.6/p.95,
16384newtokens, native user-only chat template. Required context equals actual
prompt length+16384; full runtime must validate native model context and original
EOS IDs. No prompt/output truncation, boundary regex or invented teacher system.

The sole P1 text adaptation is after the last </think>; without that boundary
it uses the ENTIRE output, not the data-completeness last2000 fallback. The
unchanged P1 scalar/pool/journal still extracts the last box; capped outputs
remain incorrect, technical unknowns block scoring. Actual gold support and
adjudication limits will be retained. New paired question statistic code uses
500 means-of-four, default_rng20261021,10000resamples, linear quantiles. No
training-seed population claim. Claude makes the actual smoke selection.

Six new synthetic training checks passed0.822s; five new endpoint/statistic
fixtures passed0.059s. The bootstrap fixture has an algebraically constant25pp
difference; no old scientific statistic, model, label or successful test rerun.
One draft-only sorted-extras validation idea was removed before testing because
the original subset reconstruction order is not sorted; full runtime must bind
the exact original plan SHA, including extras and update boundaries. Original
source-built plans were not changed. Read-only environment probe lacked torch
in the first venv; the existing data_pipeline torch2.8.0 environment was used.
