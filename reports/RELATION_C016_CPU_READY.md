# C016 — three diagnostic tasks prepared and independently verified on CPU

All **288/288 derived rows from 48 original parents** are frozen and verified.
All **53 focused CPU tests pass**, including from a clean checkout of the
published source/data. No pretrained model inference, training, server
connection, GPU reservation or additional spending occurred. E011 remains a
failed engineering run. **This is a CPU data/measurement release, not a GPU
runner or evidence of model capability.**

## Question and why these constructions

E011 trained for 256 updates but produced 0/32 complete training proofs. Its
mean target NLL of 0.11939 concealed failed semantic generation: all 333
parseable step results were 2. This motivates a diagnostic ladder that tests
one lookup, propagation along an explicitly supplied route, and original full
questions trained with one fixed reference trajectory.

The constructions retain the same 32 train and 16 previously observed dev
parents. The training anchor is E011's original round-zero route assignment,
not a route chosen after inspecting predictions. Every parent and all four
operations on its assigned route remain. No balancing search, rejection,
redraw, alternative model, final-test access or seed selection occurred.
The detailed motivations, interventions, remaining confounds and prospective
decisions were [published before extraction](../docs/experiments/C016_relation_diagnostics.md).

## Frozen tasks and exact accounting

Each arm has 256 updates, batch four, microbatch two, and 1,024 training
presentations. Parent/update order matches E011 exactly. Each parent has 32
presentations; each lookup subproblem gets eight, whereas each full fixed
reference gets 32. These are explicitly different per-operation exposures.

| Diagnostic | Train / dev rows | Prompt tokens | Target tokens incl. EOS | Total tokens per row | Planned supervised tokens | Planned processed tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Single-step lookup | 128 / 64 | 137 | 29 | 166 | 29,696 | 169,984 |
| Full graph + supplied route | 32 / 16 | 1,122 | 101 | 1,223 | 103,424 | 1,252,352 |
| Full graph + fixed reference | 32 / 16 | 1,036 | 101 | 1,137 | 103,424 | 1,164,288 |

All rows fit the frozen 1,536-token ceiling. There is **zero truncation and
zero padding** under the planned microbatches. Every terminal EOS is supervised.
The original serializer and token-normalized objective remain unchanged.

Fixed-reference prompts are byte-identical to E011; its steps, parent order,
supervised tokens, processed tokens and per-update accounting match exactly.
Only the assigned reference is repeated, replacing four-reference exposure.
This also changes route/table/state frequencies and does not alone identify a
general causal effect of diversity.

The supplied-route input retains all 32 edges and the original query. Its
four oriented edge hints add exactly **86 prompt tokens**, without revealing
intermediate states or the answer. The target is byte-identical to the fixed
reference. Hints remove discovery and also direct attention; success cannot
be attributed uniquely to one internal reasoning operation.

Single-step inputs contain the relevant original edge and the original gold
input state at that step. Intermediate states are now explicitly supplied
query inputs. Shorter context, less propagation, different target length and
repetition all change together; this is a primitive capability gate, not an
effect-size comparison. All 192 lookup train/dev rows traverse tables forward,
matching E011; reverse traversal is tested only in CPU software fixtures.

## Bias and semantic supervision audit

There are **zero overlapping parent orbit groups** across the retained splits.
This does not imply unseen operation generalization: the single-step train/dev
sets share **34 distinct permutation tables** and **13 distinct table/input
operations**. Dev parents were already used in engineering inspection. Report
them as descriptive diagnostics with 16 parent groups, not a fresh test set
or 64 independent lookup observations.

The assigned training route results have the following distribution, counted
once for each of 32 parents × four steps:

| After-state | 0 | 1 | 2 | 3 | 4 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train, 128 operations | 28 | 16 | 31 | 31 | 22 |
| Observed dev, 64 operations | 13 | 12 | 17 | 10 | 12 |

Thus a constant-2 operation prediction would be correct on only **31/128 =
24.22%** of these gold training operations. This is a static hypothetical
baseline, not a newly measured model score. Distributions are not exactly
balanced; e.g. training step two has state 3 on 12/32 parents. We retained
these frequencies instead of selecting an easier or more balanced subset.
This rules out globally constant gold labels, but does not diagnose the
mechanism behind E011's constant output.

The semantic masks partition every supervised token into edge ID, from-node,
before-state, to-node, after-state, final-state, EOS and remaining response.
With the original tokenizer each three-digit edge/node ID occupies three
tokens, and each state value occupies one. After-state values account for
**4/101 = 3.96%** of full-proof targets and **1/29 = 3.45%** of one-step targets.
The short task therefore does **not** automatically repair state-loss dilution.
It also repeats the lookup result as its final answer; this is another target
difference. We measure state-field loss separately without changing weights.

Prospective teacher-forced field accuracy uses gold prefixes and cannot replace
free-generation proof checks. Full fixed-reference NLL also averages a
different reference distribution from E011's 128-reference NLL. Keep these
quantities separate in any later report.

## What has actually been tested

The separate auditor does not import the new diagnostic builder. It recovers
training anchors from archived E011 updates, reconstructs all queries and
targets from the original C015 records, and checks exact token masks/dose.
It shares the original verified tokenizer and proof-checker dependencies;
this is explicit reconstruction independence, not two entirely separate stacks.

- 288 gold references and exact serializations/masks verified.
- 288 source-state counterfactuals change the unique solved answer and reject
  the old proof; 288 wrong-final and 288 wrong-step corruptions are rejected.
- 144 alternative legal routes are accepted for fixed-reference evaluation,
  while the same 144 are rejected when a different route is explicitly required.
- All 1,200 combinations of 120 permutations, five inputs and two directions
  pass the synthetic primitive verifier test; corresponding wrong outputs fail.
- Strict EOS, truncation, missing-final, all-line lookup counts, grouped parent
  denominators, lineage/schedule/mask corruption, target-field loss dilution and
  the original SFT token-normalization/serialization regressions pass.

The first broader regression exposed an old unit fixture reusing the real
E011 run ID; the overwrite guard correctly refused it. Only the test's
temporary identity was fixed, and the explicit local-tokenizer variable was
provided for the release regression. The initial failure log is retained.
The final main and clean-checkout runs both pass **53/53 with no skips**.
No frozen E011 runtime or historical result was changed.

CPU materialization took **2.03 seconds**; first independent verification
**3.56 seconds**; verification from the clean published checkout **3.23 seconds**.
The immutable seven-file input bundle is **203,769 bytes**. These are CPU times,
not model runtime or GPU throughput predictions.

## Next execution proposal and limits

The reviewable order is **lookup → supplied route → full fixed reference**,
with each arm initialized independently from the pinned original 1.5B base.
Continue only if every training proof is correct with EOS, no truncations,
complete 256-update dose/profile, finite metrics and assigned-reference NLL<.2.
Lookup additionally reports all-four-correct success on each of 32 parents.
Dev scores cannot choose a checkpoint or determine continuation.

If lookup fails, inspect primitive/format learning and its finite dose before
spending on larger tasks. If route-given fails after lookup passes, retrieval,
context length and propagation remain mixed explanations. If the full task
alone fails, route discovery is a candidate but the hint-information caveat
remains. If all succeed, fixed-reference learning becomes an engineering
starting point; E011 still fails and any scientific pilot needs a new review.

The unchanged ledger is **5971/7200 seconds used, 1229 remaining, 16 receipts,
zero reservations**. Proposed worst-case reservations are three × (360-second
process cap + 15-second guard) = **1125 seconds**, leaving 104 seconds. This is
a ceiling, not an estimate or new spending approval. No job is queued.

The remaining CPU implementation before requesting startup is the bounded
diagnostic GPU runner and raw-token output auditor, using this frozen data and
these score functions. They must be published, tested and reviewed as a
separate execution release. **There is no reason to open or rent a server for
the current CPU package.** Later inspect actual free disk and preserve current
ledger/checkpoint backups on a clone; this small bundle needs no storage
expansion. No server was contacted in C016; last state evidence is the retained
authenticated E011 shutdown receipt.

## Reproduction, provenance and file index

Preparation source `f073955e6b22416466a78ac679f4c9282baab6f1` was published
before extraction. Data were published at
`4a5ad973f698a0b93f696d788d5e1de23531a685`, then verified from a clean detached
checkout of that commit. Tokenizer remains the original Qwen2.5-1.5B base
revision `8faed761d45a263340a0528343f099c05c9a4323` with all five file hashes
verified. The C016 manifest SHA256 is
`cb923a3e11817682f77b4116d7524e615bdffee29e04e5848b3815352aa8133e`;
the reproduced audit SHA256 is
`23b0c901c88855d4309b40d791273469256336c43e1caedf6eb1a62365a61f95`.

Set `RELATION_DIAGNOSTIC_TOKENIZER` to the verified local tokenizer directory,
then recheck from the repository root without creating a new data attempt:

```sh
TOKENIZERS_PARALLELISM=false python -m scripts.verify_relation_diagnostics \
  --tokenizer-dir "$RELATION_DIAGNOSTIC_TOKENIZER" \
  --output .local/c016_new_verification_receipt.json
```

The receipt path must be unused. Do not rerun the immutable preparer in place.
No network, pretrained model weights or GPU are needed for this check.

| Record | Repository path |
| --- | --- |
| Motivation, controls, failure decision table | [C016 registration](../docs/experiments/C016_relation_diagnostics.md) |
| Exact model-facing examples | [Examples](RELATION_C016_EXAMPLES.md) |
| Frozen rows, schedules, assignments, budgets, masks | [Input bundle](../runs/relation_diagnostics_c016_r1/) |
| Frequencies, overlap and independent reconstruction counts | [Audit](../runs/relation_diagnostics_c016_r1/audit.json) |
| Release identities | [CPU release](../configs/diagnostics/relation_c016_release.json) |
| Proposed finite GPU plan, not launchable | [Proposal](../configs/diagnostics/relation_c016_gpu_proposal.json) |
| First independent check | [Verification](relation_c016_verification.json) |
| Clean published-checkout reproduction | [Fresh-checkout verification](relation_c016_fresh_checkout_verification.json) |
| Final 53-test run | [Test log](relation_c016_fresh_checkout_tests.txt) |
| Retained initial unit-fixture issue | [Initial regression](relation_c016_initial_regression.txt) |
| Unchanged resource ledger | [CPU closeout](relation_c016_resource_closeout.json) |
| Original failed model experiment | [E011 results](RELATION_E011_RESULTS.md) |
| Migration and next work | [Next-session handoff](../docs/NEXT_SESSION.md) |
