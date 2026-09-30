# Q2 offline feasibility results and first GPU setup attempt

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
