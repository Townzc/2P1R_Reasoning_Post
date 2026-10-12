# P007A: metered same-teacher supply pilot

Internal execution protocol, October12 2026; not presentation/report prose.
Status: prepared; GPU admission requires complete P007 main/base/audit verification.
The owner approved direct execution after that gate and prioritizes speed within
500USD total with at least50USD protected. The earlier350/100 split is superseded.
The original main campaign deadline is unchanged.

## Question and interpretation

How much failed, duplicate and length-censored generation is needed to obtain the
first, second and fourth distinct usable answer from one fixed teacher? This
supplies a cost/supply calibration for a later policy comparison. It is not a
student-performance experiment or a price estimate for OpenMathInstruct-2.

Teacher: Qwen/Qwen2.5-Math-1.5B-Instruct at
`aafeb0fc6f22cbf0eaeed126eff8be45b0360a35`, with every downloaded file pinned by
size and Git/LFS digest. Official CoT chat prompt, no tool/code execution, BF16
parameters and SDPA, Transformers4.56.2, torch2.8.0+cu128. One H10080GB, no
hardware upgrades or alternate teacher/backend selected from outputs. H100
nominal3.95USD/GPU-hour;4CPU and32GiB add0.4452USD/hour. These rates are estimates,
not invoices. Provider pricing and authenticated rates were checked October12.

## Frozen dose and checks

Use the first128 GSM8K audit_draw parents in the already-frozen C017 rank order,
without inspecting new teacher supply or backfilling difficult parents. Parent
metadata SHA df41e03d1f41a4dd72f55a34cecc1150f70b30961ed257a30dcf2992805778a0.
Raw GSM8K train SHA17f347dc51477c50d4efb83959dbb7c56297aba886e5544ee2aaed3024813465.
Every restored problem, reference and answer matches the frozen individual hash.
Reference answers are used only for checking and never placed in prompts.

Exactly eight attempted candidates per parent if the finite job completes;
maximum1024 outputs and zero student updates. Temperature0.8,top-p0.95,top-k0,
max1024 new tokens, native EOS[151645,151643],pad151643; no prompt truncation.
First16 parents are the startup block, followed by fixed32/32/32/16-parent blocks.
Eight attempt waves per block,40 batches total. Batch seed2026101201+batch index.
Startup work counts inside the1024 and the bill. No extra speed benchmark or retry.
The CPU preflight checks all prompt lengths and reference scalars before GPU use.

A usable answer must pass the existing gold-blind marked-answer extractor, agree
with the reference scalar, terminate at native EOS, not hit the token cap, and
not introduce a new-problem boundary. All explicit marked claims must agree.
This checks the final answer, not the reasoning chain. Duplicate detection is
within-parent NFC plus whitespace normalization of the entire answer; distinct
text does not certify distinct reasoning strategies. Duplicates and all other
rejections are retained and consume cost. EOS/pad processing is explicitly tested.

## Persistence, money and shutdown

Atomic run and batch claims precede work; persist request intent before generation
and the raw backend return before scoring. Preserve token IDs, source revisions,
input hashes, stops, duplicate links, checker decisions, GPU samples, generation
and checking time. Unknown returns after interruption remain unknown and are not
regenerated. No automatic restart or claim reset. One failed finite run is
reconciled before any distinct bounded repair is considered.

Campaign reserve15USD:1USD CPU asset fetch and14USD single GPU job including
startup/host/failure margin. Existing conservative reservations133.50USD remain;
combined148.50USD is below the450USD spending ceiling. Reservations are not actual
spend. GPU model window5400seconds, startup600seconds, hard job5500seconds,
absolute campaign cutoff October13 01:00UTC, with60seconds closeout guard. No
resident deployment;min0/single-use containers. Retain Volume, stop computing as
soon as work completes, verify provider containers exit and collect/hash evidence.

The actual total stage expense includes asset download/model load, generation,
checking, persistence, failures, duplicates and platform startup. Worker time ×
listed rate and delayed provider metering are reported separately. Equal shares
of measured batch time are accounting allocations, not independently measured
marginal attempt costs or counterfactual adaptive-policy runtimes. Logged prefixes
to the kth usable answer remain right-censored at eight attempts when unreached.
Do not discard censored parents or call conditional-on-success averages universal.

## Decision after the pilot

No student efficacy or teacher switching is selected from these outputs. First
verify all1024 raw returns locally and every ledger/manifest. Report supply and
censoring before choosing whether the planned cost-matched study is operationally
feasible. Freeze its exact timed spending caps, calibration rule, data draw,
student/evaluation recipe and absolute deadline before any new student outcome.
Do not reuse this pilot's parents as a fresh procurement validation draw. See
P007B for the concrete policy test and what it can and cannot establish.

Sources: [teacher model card](https://huggingface.co/Qwen/Qwen2.5-Math-1.5B-Instruct),
[Modal pricing](https://modal.com/pricing).
