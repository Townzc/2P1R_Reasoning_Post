# October 11 SFT allocation preparation

Status: **CPU data preparation completed; scientific grid proposed; no new GPU/model work.** The working plan is [P007](../../docs/experiments/P007_midpoint_allocation_plan.md). Prior Q2 and LT002 runs remain closed.

## Motivation and decisions

Prepare a small complete breadth/multiple-answer/repetition comparison for the October15 midpoint, preserving fixed supervision and update budgets. Separately measure the cost and supply of a bounded teacher process. Existing P/R experiments and extrapolation studies preclude novelty claims based only on a ratio sweep.

The new Modal environment needs durable output and duplicate-work protection. Old launchers cannot simply be transplanted: they hard-code historical identities and some save only weights, not optimizer/RNG state. New admission code is platform preparation; it is not evidence that GPU training can already resume exactly.

## Actual CPU evidence

| Check | Observed outcome |
|---|---|
| Pinned public source downloads | 968,697,196 bytes plus11,488,229 bytes of tokenizer/config files; no model weights. |
| Original problem restoration | 21,292 records; complete historical content hash match. |
| Candidate restoration and decision replay | 15,837 candidate records; byte identity and recomputed acceptance decisions match. |
| Independent verifier | 1,746,600 source rows re-enumerated;15,308 accepted responses re-tokenized; zero recorded cross-partition group leakage and zero original-test training rows. |
| Four allocations × two schedules | All eight match archived hashes, expose every selected pair, contain256 updates and524,288 supervised targets with complete responses/EOS. |
| Exposure review | 28,544 tracked run artifacts plus614 tracked JSONL files;81 conservatively exposed/mentioned dev parents,431 unmentioned candidates. No guarantee about semantic aliases or private/remote-only history. |
| New CPU correctness tests | 26 passed:17 admission/reconciliation checks and9 frozen-inventory reconstruction checks. |
| Modal definition import | CPU preflight module imports under Python3.12/Modal1.6.1 without making a remote call. |

The dataset counts include both the historical GSM8K and MATH audit records; the proposed new training uses GSM8K only. A source-data audit is not a teacher-generation measurement or a model result. Independent token verification does not certify proof validity.

| Arm | Acquired problems | Trainable problems | Retained pairs |
|---|---:|---:|---:|
| Repeat | 256 | 253 | 253 |
| Solutions | 256 | 253 | 996 |
| Mixed | 512 | 508 | 1,011 |
| Breadth | 1,024 | 1,013 | 1,013 |

All shortfalls remain visible. There is no replenishment of missing parents or selection of a four-answer-rich cohort. The comparison is approximately equal-inventory, exactly matched in archived target tokens/updates, and not identical in every computation or weighting dimension. Nonpadding processed-token range differs by about0.67%.

## Reproduce and inspect

- [Raw-free inventory audit](INVENTORY_AUDIT.json)
- [Independent reconstruction check](INDEPENDENT_RECONSTRUCTION.json)
- [Non-overwriting CPU assembler](../../scripts/prepare_midpoint_inventory.py)
- [Finite admission module](../../experiments/sft_allocation_midpoint/guard.py)
- [CPU-only Modal smoke check](../../experiments/sft_allocation_midpoint/modal_preflight.py)

The assembler consumes pinned public source files and tokenizer files; run `python -m scripts.prepare_midpoint_inventory --help` from the research root. It refuses existing output directories and rejects changed content, tokens, schedules, and source identities. Public release files contain counts, hashes, provenance and relative paths, not account identifiers, credentials or raw recovered answers. Inputs remain in ignored storage.

Local verification:

```sh
python -m unittest tests.test_midpoint_guard tests.test_midpoint_inventory -v
```

The guard tests cover atomic competing claims, immutable identity, ambiguous crashes/lost responses, deadlines, fixed cost reservations, completed-work replay rejection and explicit recovery ancestry. A fake atomic store in local tests does not validate provider behavior; the bounded CPU cloud check is separate. Reservations are conservative accounting, not provider invoices.

## Reflection and next action

Public sources suffice; no AutoDL startup is needed. GitHub alone lacks cached full answer text, but pinned downloads and these scripts reproduce it. Retain old unique checkpoints on the stopped volume.

The cross-source dev alias shows why original record IDs alone are inadequate. Exclude the known alias from the proposed new endpoint and disclose limits of the remaining431 questions. Do not label them pretraining-clean or definitely unseen by all prior research.

Next: verify CPU cloud persistence/atomic admission; build and validate the new training/checkpoint harness, run the bounded32-example overfit/throughput/recovery profile, then freeze and review the exact main recipe before eight comparative runs. The teacher pilot stays separate from historical bank pricing. No automatic old-run restart or main-grid launch follows this preparation record.
