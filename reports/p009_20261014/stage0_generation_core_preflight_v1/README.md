# Stage0 P2/P3 generation core, prepared only

This independent code preparation overlaps the owner-amendment review. The br
scope PASS is now recorded. There is **no new model call or remote upload** and
no executable admission in this packet. The next exact runtime release must add
the complete Modal entry, admission/dispatch fences, original model/input file
manifests and readback, fresh budget/provider facts, collector and independent
raw oracle. Neither code PASS nor this candidate alone can start a paid worker.

The unchanged input inventory has8993 teacher procurement requests and5457
outputs in six new endpoint files. Existing P0 Qwen/GSM0-shot650 is reused only
for that endpoint; there is no P0 regeneration. Teacher sampling retains each
original request's seed, temperature0.8/top-p0.95/1024 cap. All six endpoints
are greedy17, GSM512 or MATH1024, context2048. The original common high-throughput
V1/bf16/graphs/256seq/8192tokens/.8 memory configuration remains exact. The
Qwen/teacher and OLMo vocabularies/EOS are checked separately. Native EOS at the
exact cap may retain backend length/null metadata; no token/stop rewrite or
logical-scoring relaxation occurs. Backend malformed/extra responses are saved
before validation; a missing response keeps its attempted unit without replay.

One proposed model lifetime each: teacher procurement then teacher GSM/MATH
endpoints (44 batches); Qwen MATH0/4 (4); OLMo GSM0/4 (12). The three first256
batches are **proposed paid measurement exceptions**, part of their original
rosters, never repeated. There is no matching observed throughput for these
pipelines. The P0 timing is not substituted. Every subsequent batch including
the first batch of later endpoints uses the slowest complete observed interval
in that worker and actual elapsed,20% remaining margin and300 uncalibrated
seconds. This is an engineering scenario, not a future-host upper bound or
completion guarantee. A failed forecast ends that once-only worker.

Candidate worker caps2400/900/1200; platform+60, startup600, full windows3100/
1600/1900, oneH100/4CPU/32GiB each, min0/single-use/retries0 intended. Full-window
reserves399/216/252c total867c; retain all1004c old reservations, leaving129c
within Stage0's2000c. $110 experiment/$450 project/$50 protection are unchanged.
No settlement release, stage borrowing, changed dose or new science is assumed.
The frozen dispatch order gives remaining-stage bases996/597/381c; future cost
forecasts also fit80% of those amounts. Rate/allowances are conservative planning
inputs, not invoices or a rigorously calibrated guarantee.

Sixteen new offline fixtures passed once: full mocked1000-row pair, one bootstrap
per model lifetime rather than per endpoint, lost-response fencing, prior-unit
rejection, invalid raw preservation, exact EOS boundary, separate sampling and
vocabularies, context/identity rejection, all-batch timing and reserve arithmetic.
They are not CUDA, actual model-loading, real-output scoring or throughput tests.
No old tests or raw oracle were rerun. The original14,450-row inventory was copied,
not regenerated or rescored. Stage1 remains unadmitted pending actual stages.

Pinned primary-source reads confirm Olmo2ForCausalLM registration and the native
implementation in [vLLM0.11 registry](https://github.com/vllm-project/vllm/blob/v0.11.0/vllm/model_executor/models/registry.py)
and [OLMo2 implementation](https://github.com/vllm-project/vllm/blob/v0.11.0/vllm/model_executor/models/olmo2.py).
They do not demonstrate this model's graph startup/throughput on the planned host.
