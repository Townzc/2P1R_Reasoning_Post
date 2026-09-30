# Q2 feasibility: two-update GPU profile passed; provider OFF

## September 30 UTC: engineering profile completed

The original published source `bba38900778bfb373f2659fde115073c91b2ee24` ran
unchanged on the owner-started single A800 80GB, after the separately authorized
[storage cleanup](../storage_cleanup_20260930/RESULTS.md). The original >=40 GiB
admission floor passed; the proposed reduced disk floor was not adopted. All
246 frozen inputs were rehashed, and the installed locked environment was reused.

| Verified item | Observed result |
| --- | --- |
| Training dose | Exactly 2 full-model union-reward updates and 32 completions |
| Sampled data | 4 TRAIN tasks, 8 completions each; 8 TRAIN reference tasks prepared |
| Batch accounting | 2 sealed batches; all 34 signed intent/sample records verified; no ambiguous work |
| Finite gradients | Both pre-update checks passed, 338 gradient tensors each |
| Train + fresh reload launchers | 95.52 + 8.40 = 103.92 seconds, both exit 0 |
| PyTorch training allocator peak | 33.90 GiB allocated / 35.56 GiB reserved |
| Fresh-process model/tokenizer reload | Passed; maximum last-token logit difference 0.0 on one TRAIN prompt |
| Held-out evaluation | None |

Allocator measurements are scoped to the training worker and exclude other
allocators; they are not the full-card peak. The two batch generation/scoring
intervals were 10.38 and 7.88 seconds. Four groups had union-pass counts of 6/8,
7/8, 4/8 and 4/8. All 32 had matching base/extra verdicts: 21 pass/pass and
11 fail/fail. **These are training observations, not benchmark accuracy or a
scientific comparison.** In particular, no base-pass/extra-fail completion occurred
in this tiny profile. No conclusion about history harm, recovery, novelty or
expected W/C/R effect follows from it.

The complete model/tokenizer export contains 11 files. Every file, including the
3,087,467,144-byte weight file, was independently rehashed against its manifest.
Probe and reference-cache hashes also matched. All 85 compact evidence files
were copied locally and independently verified; large weights remain on the
server. This verifies a fresh-optimizer weight fork, not optimizer/RNG/sampler
resume. The reload check covers one TRAIN prompt, not a general equivalence proof.
The saved generation lengths are 19–520 tokens, below the 640 cap; the TRL reward
hook did not expose individual finish reasons. The known EvalPlus inner-FAIL
exception ambiguity remains a limitation. Full logs, verdicts and prior failures
are retained in the private evidence bundle.

No owned workers remained and the GPU reported 0 MiB before shutdown. Normal
**provider OFF was verified by 05:02:38 UTC**, and the temporary timer was cleared.
The conservative 04:46:00–05:02:38 powered window is 998 seconds (0.2772 A800
hours), including cleanup and collection. At the verified CNY7.98/hour it is a
**CNY2.2123 compute upper-bound proxy**, excluding storage, not an invoice or an
A100-equivalent measure. The final provider data-disk display was 40.59%, with
about 89.11 GiB free before the small evidence archive. Earlier setup failures
and their costs remain recorded below; no allowance is reset.

The engineering gate now passes. The next scientific step remains a separately
specified, costed W/C/R screen with identical future union supervision and fresh
optimizers. This profile does not establish a sufficient history dose or a
reliable full-study duration. No scientific grid, new seed, automatic restart or
extra evaluation is queued. See the [compact result and checkpoint audit](ENGINEERING_PROFILE_20260930.json).

All earlier sections below are dated history; current readiness and server state
are given above.

## September 30: server inputs and offline installation are ready

The owner started no-card mode to avoid GPU time spent waiting for resources.
The actual limits were 0.5 CPU core and 2 GiB RAM. All **246 frozen files,
7,513,836,508 bytes**, passed an independent server-side SHA256 check, including
the seven model files, data/split, locks and original published source archive.
The model directory contains exactly the seven expected files.

One serialized offline installation took **282.7 seconds**. Python 3.11.16 and
uv 0.12.17 passed identity checks. The unchanged 227-package runtime plus the
additional build helper matched all 228 expected installed versions. Lightweight
packaging/numpy/safetensors imports passed; no OOM or OOM-kill event was observed.
After installation, 22.44 GiB remained on the data filesystem and 14.46 GiB on
the system filesystem. **GPU imports, model loading, kernels, training and the
fresh-process reload remain untested.** This is preparation, not a scientific result.

Transfer problems are retained in the [preparation receipt](NOCARD_PREPARATION_20260930.json):
slow direct PyPI transport, a stopped deadline-bound mirror transfer, an undersized
mirror-index cap and a missing manifest in an operator deployment. Each was
reconciled before an explicit correction; completed artifacts were rehashed and
reused, with original versions and full-file hashes unchanged. A proposed NAS-chunk
recovery never ran because its plan transfer timed out. The final verified inputs
came from the staged files and exact-file downloads. The old browser archive
upload was stopped at about 55% only after full server verification; its incomplete
cache and all historical evidence were preserved.

All 1,547 compact evidence files were copied and independently checked before
normal provider shutdown. **Provider OFF was verified by 04:24:42 UTC**, and the
temporary shutdown timer was cleared. The conservative 03:39:00–04:24:42 window
is 2,742 seconds, about CNY0.0762 at the documented no-card rate, excluding storage;
this is a cost proxy, not an invoice. Large inputs and the installed runtime remain
on the stopped instance. No automatic GPU startup or new scientific arm follows.

The next finite step remains two updates / 32 training completions plus the
fresh-process reload. Its disk admission must be reconciled with the now-resident
inputs/runtime before requesting startup; a proposed reserve and owned-worker
monitor are documented privately, not yet implemented or measured. The original
60-minute GPU powered-window and 1,800-second worker limits stand.

## Second setup: transfer admission failed; no model work

The second owner-started attempt verified the same idle one-A800 hardware and
set a normal provider timer. The frozen7,513,836,508-byte bundle was transferred
once, with an admission watchdog reserving installation and at least35minutes
for the profile. After60.14s, observed accepted throughput was0.314MB/s; estimated
remaining transfer was23,880s (about6.6h). The watchdog stopped the transfer.
The preserved BrokenPipe is a consequence of this intentional stop. Remote
inventory found23 fully matching files and one partial; no automatic replay or
deletion followed. No environment installation, model generation, optimizer
update, reference/candidate execution or checkpoint occurred.

Normal provider OFF was verified by02:01:30UTC and the temporary timer cleared.
Conservative power-on01:55:30UTC gives360s / CNY0.798 at7.98/hour. Across both
failed attempts the powered upper-bound proxies total1,034s (0.2872A800 hours)
and CNY2.292, excluding storage; neither figure is a bill or A100 equivalence.
See [the second setup receipt](TRANSFER_ATTEMPT_20260930.json).

The preparation error was treating locally downloaded assets as practical server
readiness before measuring the upstream path. Future setup must avoid paid GPU
waiting: stage inputs in [provider file storage](https://www.autodl.com/docs/fs/)
while OFF, then use owner-started [no-card mode](https://www.autodl.com/docs/save_money/)
for bounded hash verification and installation. Provider documentation describes
20GB free file storage and no-card mode at CNY0.1/hour with0.5CPU/2GBRAM; live
conditions must still be checked. These small CPU/RAM resources may constrain
installation; offline install and GPU execution remain unverified.

A7,514,327,040-byte archive of the original manifest-selected inputs was created
and locally hashed. Its browser upload has started while the GPU is OFF, but
completion and server-side hashes are **not yet verified**. Keep this readiness
state distinct from the local bundle's completed hashes. There is still no
scientific Q2 result or measured cost for the proposed W/C/R study.

## September 30 UTC: setup stopped before model work

The owner started one A800 80GB instance for the prepared finite engineering
profile. Hardware admission passed (driver 580.126.09, glibc 2.35, 120 GiB host
RAM, idle GPU). A normal provider shutdown timer bounded the powered window.
The execution source was published at
`bba38900778bfb373f2659fde115073c91b2ee24` before transfer.

Asset staging verified the official dataset and split, then failed fetching the
first pinned Hugging Face model configuration with `Network is unreachable`.
The parallel uv bootstrap was terminated immediately. This is one asset/network
failure and one cancelled bootstrap, not two independent package failures.
Python 3.11, the locked GPU environment and the profile worker were never
started. There were **zero model generations, zero optimizer updates, zero
reference/candidate program executions and no new checkpoint**. No automatic
retry or alternative stack ran. This failure does not test the scientific idea.

All 24 inventoried source/setup/data/evidence files were independently copied
and SHA256-verified. The final process inspection found no owned setup/model
workers and no GPU compute applications. Normal provider OFF was observed by
01:38:14 UTC; the temporary timer was subsequently cleared. With conservative
power-on at 01:27:00 UTC, the powered-window bound is 674 seconds (0.1873 A800
device-hours), or CNY1.494 at the verified CNY7.98/hour. This is a wall-clock cost
proxy, not an invoice; storage is excluded. Historical volumes remain intact.

Next preparation is local: assemble and hash-check the pinned model and Linux
dependency artifacts before another owner-started attempt. Network reachability,
Python-package resolution and a successful model runtime are distinct checks.
No new scientific result or throughput/cost estimate for W/C/R is available.
The [compact setup receipt](SETUP_ATTEMPT_20260930.json) and
[path-redacted original asset error](SETUP_ASSET_FAILURE_20260930.log) preserve
this failed attempt separately from the earlier exploratory replay.

Local preparation after shutdown completed: all seven model files and232
dependency/interpreter/bootstrap artifacts were downloaded and independently
hash-verified, together with the frozen data, split, locks and source archive.
The transfer manifest covers246 files totaling7,513,836,508bytes. All227 runtime
artifacts match the original public lock; the three source-only packages retain
their original sdist hashes. The separately pinned build tools do not change the
training recipe. See [the compact preparation receipt](OFFLINE_BUNDLE_20260930.json).
No package was installed locally and no model/program was executed. This removes
the need to fetch those inputs from the server; Linux installation and GPU runtime
remain unverified. The one-hour powered limit and original profile are unchanged.

## September 29 offline milestone (historical)

September 29, 2026. **There is a measurable supervision change to investigate;
there is not yet a new training result or evidence that weak history harms future
learning.** New GPU/model work, new optimizer updates, new candidate executions,
and paid-server actions in this milestone are all zero.

## Actual exploratory replay

We independently joined the five public Qwen2.5-Coder-1.5B-Instruct base-reward
training runs from [the author's pinned repository](https://github.com/toffee-desuwa/rlvr-leaky-suite/tree/9b6c86abeb4b837418b009d5354f81b43a28f84b/runs/grid).
Each contains 400 batches of 16 completions, grouped eight per task. Every
base-passing completion has exactly one boolean extra-test verdict; there are
no duplicate/orphan joins, unresolved base verdicts or logged outer scorer errors
in these files. This does not prove absence of hidden evaluator error.

All 32,000 rollouts use the frozen 250 TRAIN tasks; no held-out samples were
accessed or generated. File sizes and Git blob hashes match the pinned tree.
The new analysis computes reward changes on fixed previously generated programs;
it does not simulate the different programs a union-trained model would emit.

| Descriptive quantity | All five 400-step runs | First 64 steps of each run |
| --- | ---: | ---: |
| Previously generated completions | 32,000 | 5,120 |
| Base pass but extra fail (reward changes 1 to 0) | 2,821 / 32,000 (8.82%) | 424 / 5,120 (8.28%) |
| Groups whose centered reward signs change | 1,065 / 4,000 (26.63%) | 172 / 640 (26.88%) |

Across the five full runs, the reward-flip rate ranges from 8.56% to 9.06%.
15.00% of base-accepted completions are rejected by the union rule. Flips occur
on 158 of the 250 tasks; ten tasks account for 32.93% of flips. These are repeated
training observations, not independent task or training replication for our Q2.
We do not attach an iid rollout confidence interval to these descriptive counts.

The group transitions are also informative:

| Base-group status → union-group status | Groups |
| --- | ---: |
| Mixed success → all fail | 391 |
| All pass → mixed success | 146 |
| Mixed success → mixed success | 2,310 |
| All pass → all fail | 18 |
| All pass → all pass | 582 |
| All fail → all fail | 553 |

Thus mixed groups fall from 2,701/4,000 (67.53%) to 2,456/4,000 (61.40%) on these
fixed samples. Stricter supervision can both create and remove a nonconstant
binary reward signal. Centered-reward signs are not actual parameter gradients:
normalization, clipping, importance ratios, and model Jacobians also matter.
The all-pass-to-all-fail case changes every reward but leaves all centered rewards
zero; the analysis explicitly handles this case.

An independent direct-count implementation (without importing the analysis code)
matched all 88 checked source/count/window/transition values. The deterministic
analysis and its edge-case tests are in
[`reanalyze_public_rollouts.py`](../../experiments/q2_supervision_migration/reanalyze_public_rollouts.py).
[Full descriptive output](PUBLIC_REPLAY.json), [source receipts](PUBLIC_SOURCE_RECEIPTS.json),
and [independent check](INDEPENDENT_REPLAY_CHECK.json) retain the evidence.

## Implication for the small experiment

The reward intervention is not vanishingly rare even in the first 64 updates of
these existing runs. This supports an engineering profile and a possible short
screen. It does not identify a sufficient dose for history formation, bound the
future-effect variance, or establish that a 64-step null rules out the direction.

Keep the initial scientific comparison W/C/R with common fresh continuation:
weak-test prefix W, equal-dose union-test prefix C, and no-prefix reference R.
The known alternative explanation from reward-group starvation is now directly
relevant to the candidate assets. Record mixed/all-fail/all-pass groups and task
coverage; do not claim irreversible damage from low future learning alone.

A candidate T=K=64 screen would contain 320 update opportunities and 5,120 new
training generations before evaluation. This remains a proposal to cost using
actual measurements, not an automatic continuation after the profile. Independent
training replication is needed for stronger causal and noninferiority claims.

## Local engineering results

- Implemented explicit base/extra/union reward semantics and separate scorer
  error, timeout and missing statuses. No unknown outcome becomes zero reward.
  Full completion text/token IDs and dual verdicts have exclusive-create records;
  repeated or ambiguous batches/forks are refused. Authored CPU fixtures exercise
  collision, incomplete output, mutation and concurrent-reservation cases.
- Staged and hash-verified official MBPP+ v0.2.0 without executing its programs;
  all 378 IDs match the 250/128 split. Initial validation incorrectly assumed all
  extra suites were nonempty: official Mbpp/793 is empty. This failed assumption
  is preserved in [the data preparation check](DATA_PREP_CHECK.json); data were
  not removed or modified. It is outside the first eight profile tasks.
- The Qwen model revision and all seven needed file hashes are frozen. Small
  tokenizer/config assets were inspected; the 3.09GB weight file was not fetched.
- Resolved the Linux/Python3.11 package graph with 227 packages and distribution
  hashes after removing unused conflicting xformers. Small source-distribution
  metadata was built locally; no GPU packages were installed. Metadata resolution
  is not a runtime/import/hardware test. This PyPI stack needs compatible R580+
  CUDA13 drivers, glibc>=2.35, and an actual GPU profile.
- Prepared a finite two-update/32-completion profile, complete weight/tokenizer
  export and fresh-process reload check. No held-out metric, full science grid,
  restart or alternate implementation is queued.

The [profile protocol](../../experiments/q2_supervision_migration/PROFILE_PROTOCOL.md)
specifies a proposed 60-minute whole-powered-window cap and a 30-minute combined
training/reload-worker cap. At the *previously supplied*, unverified-current price
of CNY7.98/hour, the compute ceiling would be CNY7.98 excluding storage. It is
not a throughput forecast or permission to start a stopped server automatically.
The user retains server startup; actual host compatibility and current price must
be checked. Stop promptly on incompatible setup rather than spend the whole cap.

## Backup status

A separate agent checked one nearby fallback about test-selection transfer across
changing policies. Existing test-selection, cross-policy evaluation, reward-density
and noise-correction work substantially covers the naive version. It is not
admitted as an independent GPU project. Main effort remains Q2. Complete Q2 output
retention would permit a later bounded reuse-only diagnostic if justified; no
extra generation or branch is assigned to the fallback.
