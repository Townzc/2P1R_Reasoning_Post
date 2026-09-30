# Q2 first engineering profile (not the three-branch scientific screen)

2026-09-29. The owner requested prompt small-experiment feasibility work and
allowed an agent to audit a fallback. The main idea remains supervision history
under a base-to-union code-test migration. No new GPU work is claimed here.

## Completed local diagnostic

`reanalyze_public_rollouts.py` joins the published five Qwen2.5-Coder-1.5B-Instruct
base-reward runs at upstream commit `9b6c86abeb4b837418b009d5354f81b43a28f84b`.
It computes base versus union rewards on the *same saved author-generated codes*.
No model, candidate program, or benchmark reference executes during this replay.
This is an exploratory intervention-strength diagnostic, not training under the
counterfactual reward and not a new benchmark result. See
[the result report](../../reports/q2_feasibility_20260929/RESULTS.md).

## Finite next queue

- One Linux x86_64 GPU with at least 75 GiB VRAM (A100/A800 80GB class), bf16;
  at least 32 GiB host RAM and 40 GiB free staging/environment/output disk.
  These are admission floors, not measured peak requirements.
- Python 3.11 and the hash-locked package file. This resolved PyPI stack uses
  CUDA 13 and needs a compatible driver (R580 or newer); check before installing.
  No driver upgrade, alternate backend, or dependency sweep is queued.
- Frozen Qwen model revision, official MBPP+ v0.2.0, upstream 250/128 split;
  pinned hashes are in `assets/`. First eight lexicographically sorted TRAIN
  tasks only. Reference execution is restricted to those eight tasks.
- Exactly two union-reward full-model GRPO updates, fresh Adafactor, constant
  learning rate 1e-6, bf16, beta=0, microbatch4, accumulation4, K8,
  max completion640, temperature1. On one worker this is 32 completions
  (four sampled prompt groups); eight candidate tasks need not all be drawn.
- One complete model/tokenizer export and a new model load with a fixed training
  prompt's next-token logit/rendering comparison. It verifies a weight fork,
  not retained optimizer/RNG/sampler resume. No extra training after reload.
- No held-out generations, public-test scoring, branches W/C/R, automatic retry,
  new seed, alternative model, or optional sweep.

## Bounds and costs

Proposed *whole powered-window* ceiling: 60 minutes, including installation,
asset staging, CPU preparation, idle time, collection, and normal provider
shutdown. This is a maximum allowance for the first engineering attempt, not a
measured duration or a promise that fresh installation fits.

Before owner startup, verify the displayed current hourly price and provider
shutdown mechanism. At the previously supplied CNY7.98/hour, the 60-minute compute
ceiling would be CNY7.98 excluding storage; this conditional arithmetic is not a
new quote or invoice. One GPU for at most one hour is at most one device-hour;
A800 device-hours are not automatically A100-equivalent hours. All actual work
counts toward the owner's shared project ceiling; failed work is not reset.

Set a normal provider shutdown timer no later than power-on+60min. The model
worker parent permits at most 1,800 seconds, including hash checks, reference
preparation, generation, updates, and export/reload; reserve collection and
shutdown time separately. **Start the worker only with >=35min remaining in the
powered window; otherwise retain setup receipts, shut down and report.** Stop
installation/staging as soon as completion within this bound is implausible.
`stage_profile_assets.py --seconds 600` independently limits asset fetching;
keep dependency setup within the shared window as well. Do not extend the
window to fix an environment or memory failure.

The user retains server startup. Never treat an old SSH route, stopped LT002
instance, or old heartbeat as a new live execution queue. At startup, inspect
actual provider instance identity, driver, GPU/CPU workers, free disk and memory.
No unrelated worker may be interrupted. Provider OFF, not process exit, ends the
powered window. Shut down promptly after evidence collection, not at the timer
if finished early. Never use a shutdown helper that also clears Trash.

## Prepare and launch after owner startup

September30 UTC cleanup amendment: the owner requested deletion of unused server
data and started the single-A800 host. Completed math-run optimizer/RNG states
were pruned with independent identity checks; final weights/scientific records
remain. Data free space is92.04GiB, so the original >=40GiB floor now passes.
The previously proposed lower post-install gate is unnecessary and not adopted.
All246 frozen Q2 files were rehashed after cleanup; no model work was done by
cleanup. Continue only the originally authorized finite engineering profile after
fresh hardware/worker/price/timer admission, with no source or dose change.

September 30 UTC no-card closeout amendment: the owner-started resource preparation
completed with all 246 frozen inputs independently verified and the unchanged
runtime installed offline. All 228 runtime/build versions and three lightweight
imports passed. The announced no-card cap was amended from the earlier proposed
30 minutes to 60 minutes under the owner's save-time direction; a verified normal
provider timer bounded it. Actual conservative duration was 2,742 seconds, followed
by verified provider OFF. The original GPU 60-minute/1,800-second bounds are unchanged.
See `reports/q2_feasibility_20260929/NOCARD_PREPARATION_20260930.json`.
The browser archive upload is no longer a prerequisite: it was stopped after direct
server input verification, and its partial cache was preserved. Reuse the verified
resident inputs and runtime on the next owner startup; do not repeat downloads or
installation. GPU imports/model execution remain unverified. Reconcile the original
broad disk reserve against actual post-install free space before GPU admission;
any revised incremental reserve/owned-worker monitor must be explicit and ready
before launch. No new model dose, alternative stack or automatic startup is authorized.
Earlier preparation amendments below are dated history where superseded.

September30 UTC second-setup amendment: the owner-started offline-transfer
attempt also closed before installation/model execution. Measured upload was
0.314MB/s, so the admission watchdog stopped it and normal provider OFF was
verified. Preserve both failed attempts. Download completeness did not establish
server-readiness; do not request a further GPU startup based on it alone.

Next staging uses provider file storage while the GPU is OFF. The prepared tar
contains exactly the frozen manifest and selected inputs; its SHA256 is
`1a078d763becc9a4653c2e1916692468ce877fd2e4417ff7508e2b1211c0d3eb`.
Browser upload is pending at this amendment. Require completed remote visibility
and subsequent server SHA verification, not just a selected/uploading file.

Proposed owner-started no-card preparation is capped at30minutes (CNY0.05 at the
documented0.1/hour, conditional on the live quote). Only resource staging/hash
checks, the same locked installation and lightweight version/import checks are
allowed; no model load, candidate/reference execution or training. Record actual
0.5CPU/2GBRAM limits, disk availability and mount before setup. Stop on failure
or insufficient resources; retain partials and shut down normally. Its low-memory
installation remains untested. Only a verified environment can justify a new
GPU profile request, still bounded by the original60min powered/1800s worker
limits. There is no automatic startup or scientific continuation.

September30 UTC setup amendment: the first owner-started setup failed on the
initial pinned model config download, before any model worker. It is closed with
providerOFF and preserved evidence. For a separately owner-started attempt, use
the independently verified local offline bundle rather than assuming the server
can reach model/package origins. It contains the unchanged227 runtime artifacts,
the original3 source-only sdists, explicit build tools, uv0.12.17, CPython3.11.16
Linux standalone, the frozen model/data/split and the published source archive.
There are246 transfer files totaling7,513,836,508bytes (about7GiB). Do not transfer
duplicate `.partial` hardlinks or unselected caches. Verify every SHA remotely.

The60min powered cap and>=35min worker-admission reserve are unchanged. Transfer
and setup must therefore fit in at most25min; a20min transfer alone would need
about6.26MB/s before allowing setup overhead. This is a requirement calculation,
not a measured upload rate. Stop if actual transfer/setup cannot meet the window.
No automatic startup, retry, new stack or scientific continuation is authorized.

After checking the bundle manifest, extract the official Linux standalone Python
into a NEW runtime directory and the uv executable from the verified wheel's
`uv-0.12.17.data/scripts/uv` member. Create an isolated Python3.11 venv. Bootstrap
only the explicit build tools (setuptools81.0.0 and packaging26.3 match the main
lock; wheel0.46.3 is a separately recorded build helper), then install the original
runtime lock with build isolation disabled to prevent hidden network build
dependencies. The intended installer invocations are below; actual new paths
must replace the placeholders, and TMPDIR belongs on the data filesystem:

```sh
UV_BINARY pip install --python NEW_VENV/bin/python --offline --no-index \
  --find-links BUNDLE/build_wheelhouse --require-hashes \
  -r BUNDLE/build-tools.lock.txt --no-cache --link-mode copy
UV_BINARY pip install --python NEW_VENV/bin/python --offline --no-index \
  --find-links BUNDLE/wheelhouse --require-hashes --no-build-isolation \
  --only-binary :all: --no-binary wget --no-binary tempdir \
  --no-binary stop-sequencer -r BUNDLE/runtime.lock.txt --no-cache --link-mode copy
```

For no-card preparation, serialize work with `UV_CONCURRENT_INSTALLS=1`,
`UV_CONCURRENT_BUILDS=1`, and `UV_CONCURRENT_DOWNLOADS=1`; pass
`--no-python-downloads` and do not enable bytecode compilation. These names/flags
were inspected in the available uv CLI, not measured in the target Linux runtime.
The selected runtime wheel contents total9,964,859,795bytes (9.28GiB,72,545entries).
Reserve12GiB on the system filesystem for the new venv and24–26GiB available on
the data filesystem for the bundle, temporary unpacking and future outputs.
Leave the7.514GB tar in file storage and stream its extraction rather than copy
another archive to the data filesystem. Hash in chunks. These are conservative
planning reserves, not observed install disk/RAM peaks; fail closed at the live
limits and preserve logs. Set executable permission on the extracted uv binary.

The archive layouts and all input hashes were checked locally. Linux extraction,
installation/build, shared-library imports and GPU execution are still untested.
Do not interpret a complete download as a successful engineering profile.

Use a new workspace/environment and the published execution source commit.
The next attempt receives the verified offline model/data rather than repeating
the failed online staging. For provenance, the original staging command was:

```sh
python -m experiments.q2_supervision_migration.stage_profile_assets --out PROFILE_ASSETS --include-model --seconds 600
```

The earlier3.1GB model download was gated by `--include-model`; its failure and
partial remain retained with no automatic retry or deletion. After the new
offline bundle and environment pass admission, use the actual new absolute paths
and frozen SHA values from `assets/data_manifest.json`:

```sh
python -m experiments.q2_supervision_migration.gpu_profile \
  --model-path PROFILE_ASSETS/model \
  --model-manifest PROFILE_ASSETS/model_manifest.json \
  --data-json PROFILE_ASSETS/MbppPlus.jsonl --data-sha256 DATA_SHA256 \
  --split-json PROFILE_ASSETS/split.json --split-sha256 SPLIT_SHA256 \
  --out NEW_PROFILE_OUTPUT --max-seconds 1800 --scorer-timeout 120 \
  --execute-engineering-profile
```

These placeholders deliberately require the actual task-local paths and verified
remaining deadline. There is no background scheduler or automatic second phase.
Inspect source/config identity before launch and record provider power-on time.

## Success, failure, and interpretation

Collect installed versions, driver/GPU identity, runtime, raw completion text and
tokens, both suite statuses, update count, scorer failures, and complete model/
tokenizer manifests. Infrastructure failures, outer timeout and missing scores
are not mapped to zero reward. EvalPlus itself contains internal exception-to-
failure handling; preserving its status is not perfect attribution or a semantic
correctness oracle. One official task has zero extra inputs (Mbpp/793); it is not
one of the profile's eight tasks and is not silently removed from the dataset.

A successful profile requires exactly two committed updates, 32 retained outputs,
finite recorded training quantities, complete scoring, and successful verified
weight/tokenizer reload. All-fail/all-pass groups are reported; finite execution
alone is not evidence of a useful gradient or an effect of supervision history.
Any failed or ambiguous attempt stops and preserves evidence. No automatic retry.

Only measured profile results can support a runtime/cost estimate for the next
scientific screen. A candidate small screen is T=K=64: two histories plus three
fresh continuations =320 updates/5,120 training generations, with a separately
frozen evaluation plan. This is not an approved automatic queue and one seed is
not a mechanism, noninferiority, or novelty proof. Retain the stronger-history C
reference and the no-prefix R reference; do not choose branches after seeing
which scores look favorable.
