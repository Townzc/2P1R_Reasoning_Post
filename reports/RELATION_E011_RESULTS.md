# E011 results — full dose completed; engineering gate failed

**The new relation task has not passed its learning gate.** The frozen run
completed normally, but verified complete proofs are **0/32 on training** and
**0/16 on each development view**. Do not start an allocation comparison from
this checkpoint or interpret small answer-only differences as reasoning gains.
No extra GPU run was launched. The original ledger is **5971/7200 seconds used,
1229 remaining**, with no unresolved reservation.

## Why this experiment was run

C014 established full constructive support, exact reference verification and
its finite CPU shortcut checks. It did not establish learnability by the1.5B
base or the cost of1137-token examples. E011 therefore tested a fixed32-world
engineering trajectory before a scientific comparison. The prospective
[E011 registration](../docs/experiments/E011_relation_engineering.md) retains
its original gate, dose, selection and stopping rules.

## Design and execution

The owner started the supplied A800 and authorized this run. The clean published
execution source was `33820d9374d9649db06ed1024532f26fa9962cfd`. Fresh pinned
Qwen2.5-1.5B base, FP32 parameters/BF16 autocast, SDPA, nonreentrant gradient
checkpointing, AdamW5e-5, batch4/micro2; no tuning-method or model substitution.

Use seed401 indices0–31 for training and seed481 indices0–15 for diagnostics,
exactly as frozen. Four routes per train world, eight exposures per route,
256 updates and1024 presentations:103424 supervised tokens including EOS,
1164288 processed tokens, zero padding. No truncation of training data,
early stop, OOM, nonfinite gradient, GPU retry, filtering or holdout access.

All42 Linux tests passed. The first preflight retained41 passes/1 skip because
a historical C014 test expected a canonical private tokenizer-cache path;
a symlink to the existing original cache fixed it, without changing code,
model or data. Both GNU-timeout integrations executed successfully.

## Actual outcomes

| Evaluation | Final answer correct | Complete proof + EOS | EOS observed | Generation cap reached |
| --- | ---: | ---: | ---: | ---: |
| Base, clean dev |0/16|0/16|0/16|16/16|
| Trained, clean train |2/32|0/32|18/32|14/32|
| Trained, clean dev |2/16|0/16|13/16|3/16|
| Trained, useful deletion |1/16|0/16|12/16|4/16|
| Trained, irrelevant deletion |3/16|0/16|13/16|3/16|

These are96 greedy generations with a fixed128-token cap. Gold clean references
have101 EOS-inclusive tokens. Valid route alternatives are accepted; only
outer ASCII whitespace is normalized. A correct final state cannot rescue an
incorrect or incomplete trace. The development views share16 parents.

Final teacher-forced train NLL over all128 references is **0.1193898**. This
satisfies the NLL part of the gate, while the32/32 complete-proof condition
fails decisively. All raw token IDs, text, failure reasons and truncations remain
in the [immutable run directory](../runs/relation_overfit_e011_r1).

## Failure analysis and its limits

A post-hoc CPU count finds **333/333 syntactically parseable generated step
lines use state2 as their after-state**:137 train,69 clean dev,62 useful-delete
and65 irrelevant-delete lines. This is an observed constant-state output,
not a finding that the model performs the relation computation.

The training references are not constant-state: across512 gold step results,
states0/1/2/3/4 appear97/83/116/117/99 times respectively. Among133 training
step lines that cite an existing edge and matching endpoints, only33 satisfy
that edge's local table lookup; clean development has8/66. Local lookup counts
are descriptive and are not independent samples or complete proofs.

The complete training output failures are14 missing finals,13 wrong states
and5 disconnected traces. For clean dev they are3 missing finals,10 wrong
states,2 disconnected traces and1 wrong endpoint. The original scorer returns
the first failure it observes; truncation can therefore obscure earlier errors.

A static token inventory shows that the four after-state value tokens occupy
**4/101 =3.96%** of the supervised sequence. Other tokens include selected
edge/node IDs, syntax and EOS; IDs are not necessarily trivial. Mean NLL can
therefore hide poor performance on the key state values. We did **not** measure
field-specific model NLL, so token weighting, target multimodality, attention,
optimization and insufficient dose remain candidate explanations, not identified
causes. Four equally weighted distinct references also give an idealized
entropy floor of log(4)/101≈0.013726; zero NLL is not the correct target.

Base outputs became more structured and more often terminated after training,
but complete correctness remained zero. The1/16 versus3/16 deletion answer
counts cannot establish a deletion effect or an allocation advantage: there
is one engineering arm, tiny shared diagnostic samples and a constant-state
failure. This result also does not prove that the task is intrinsically
unlearnable; it establishes failure under the frozen256-update recipe.

## Cost, verification and preservation

- Profile updates9–72:64 updates in33.50794 seconds, **771.64 supervised tokens/s**
  and **8686.66 processed tokens/s**.
- Peak allocated memory27833.66MiB (27.18GiB), reserved29832MiB (29.13GiB).
- Bounded process elapsed230.664 seconds, charged **231 seconds**; manifest
  runtime224.133 seconds. No720-second timeout or automatic retry.
- All96 saved token streams and the complete dose were independently rechecked
  on server and locally, yielding **byte-identical CPU audit reports**.
- The initial CPU audit exceeded its60-second orchestration bound. A published
  read-only vocabulary-size cache removed repeated expensive length queries;
  the frozen scorer, tokenizer operations, training dependencies and result
  schema stayed unchanged. The cache checks vocabulary size again on exit.
- All16 receipts match the independently retrieved ledger; prior15 entries are
  unchanged. Latest ledger SHA256:
  `664a177b847b678d41d52fe7dbb62667630256db70f416b11b4facbbb9c82cb5`.
- All12 checkpoint files, **6190803414 bytes**, have an independent local backup
  with matching SHA256. Transfer/verification took621.109 seconds. Weights stay
  outside Git and do not include optimizer/RNG resume state.

The GPU was idle after completion. Existing50GB storage sufficed; no expansion
or deletion was needed. Instance idle/setup/transfer/storage billing is separate
from the231-second process charge. The authenticated provider console subsequently confirmed the exact instance
as **已关机**, after publication and synchronized preservation. See the
[shutdown receipt](relation_e011_shutdown_closeout.json). No instance was deleted
or released; no GPU phase is queued.

## Current decision and next diagnostic proposal

Keep the original task and this failed run intact. First prepare CPU diagnostic
fixtures and a separately bounded proposal; do not reuse E011's run ID or launch
another GPU job automatically. The next question is why state predictions fail,
before asking whether route allocation changes robustness.

A useful first diagnostic keeps the same full prompts and dose but fixes one
reference route per world, removing multiple target trajectories. Separately,
a supplied-route version can test four-step table propagation with route choice
made explicit; a one-edge lookup fixture can test the basic table operation.
These are engineering diagnostics with different information/difficulty, not
interchangeable scientific treatment arms. Freeze selection, labels, semantic
field metrics and strict proof/EOS gates before model evaluation. Decide their
order and complete caps after CPU review, within the remaining1229 seconds or
with a separately approved allowance.

If the basic operation or supplied-route gate fails, inspect that failure before
scaling graph training. If simpler gates pass, return to the full graph with a
clear diagnosis. A later scientific multi/repeated-route comparison still needs
fresh frozen groups, reviewed controls and evidence beyond this observed sandbox.
There is currently no empirical basis for an ICLR contribution claim.

## Records and reproduction

| Record | Location |
| --- | --- |
| Prospective rationale/design/stop rules |[E011 registration](../docs/experiments/E011_relation_engineering.md)|
| Inputs and exact schedule |[C015 bundle](../runs/relation_engineering_c015_r1)|
| Raw outputs, history, model/config provenance |[E011 run](../runs/relation_overfit_e011_r1)|
| Independent scoring and full-dose verification |[CPU audit](relation_e011_output_verification.json),[cross-machine receipt](relation_e011_independent_verification.json)|
| Post-hoc failure counts |[failure analysis](relation_e011_failure_analysis.json)|
| Static supervised-field inventory |[token inventory](relation_e011_semantic_token_inventory.json)|
| Cumulative accounting |[ledger proof](relation_e011_ledger_verification.json)|
| Full checkpoint backup hashes |[backup receipt](relation_e011_checkpoint_backup.json)|
| Linux tests, including retained initial skip |[final log](relation_e011_linux_tests.log),[initial log](relation_e011_linux_tests_initial.log),[receipt](relation_e011_linux_test_receipt.json)|
| Next-session and migration state |[handoff](../docs/NEXT_SESSION.md)|
| Rationale/result/analysis history |[research journal](../docs/RESEARCH_JOURNAL.md)|

Read-only audit reproduction, using the verified original tokenizer and a new
output filename:

```bash
python -m scripts.audit_relation_engineering_cached --run-dir runs/relation_overfit_e011_r1 --tokenizer-dir "$TOKENIZER_DIR" --out reports/new_e011_verification.json
```

The post-hoc counts and static inventory also have an executable
[reproduction script](../scripts/describe_relation_engineering.py); both JSON
descriptions match the earlier counts exactly in the
[replay receipt](relation_e011_description_reproduction.json). This was
implemented after observing the failure and is not a prospective hypothesis test.

```bash
python -m scripts.describe_relation_engineering --tokenizer-dir "$TOKENIZER_DIR" --out-dir reports/new_e011_description
```
