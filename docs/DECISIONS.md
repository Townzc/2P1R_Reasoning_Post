# Decisions and open questions

## D001 — 2026-09-05 UTC: public reproducible workspace
The user requested starting the agreed project and updating the provided GitHub repository after code and experiments. Import only code and synthetic fixtures; keep private handoffs and connection information outside the public repository.

## D002 — 2026-09-05 UTC: bounded initial compute
The user approved 2 GPU-hours (7200 process-seconds on one GPU) for first-stage checks and feasible pilots. Instance idle billing is separate. Record and enforce cumulative job time. Do not automatically rent another GPU.

## D003 — engineering recipe, not a scientific result
Use the already selected 0.5B base model for correctness/debugging with FP32 trainable parameters and BF16 autocast. The intended 1.5B base remains the main candidate. No switch to LoRA or lower-precision optimizer state is implied by a memory failure.

## D004 — 2026-09-05 UTC: owner-provided A800 continuation
The owner supplied a new A800 server and requested continuation of the planned experiments. Continue the existing 7200-second cumulative budget, carrying forward 737 seconds already charged. First repeat the unchanged 1.5B memory profile, then run the 32-example engineering gate at the previously debugged LR 5e-5. Capture greedy and four-sample development performance before and after adaptation. This does not settle the still-open scientific arm/domain definitions. The A800 hourly price is not known; do not apply the old 4090 reference price to A800 runtime.

## D005 — 2026-09-08: approved staged pilot preparation

The owner approved the proposed sequence: finish data/control preparation locally,
then A800 calibration, then one paired-seed four-arm pilot if calibration and cost
permit. The owner will supply a replacement A800 when needed. Routine CPU design
choices are specified in PILOT_V1.md: expanded raw number domain, presolver splits,
exact shared-block schedules, sentence-frame Surface control, and a common four-cycle
dose. The existing 7200-second cumulative budget remains unchanged. Main-grid,
additional seeds and holdout evaluation remain later decisions.

The owner also suggested karpathy/autoresearch as a reference. Adapt its compact,
bounded iteration and fixed-evaluation workflow to this causal comparison. Retain
all attempted runs in Git; use token/update matching plus finite runtime ceilings.
No open-ended autonomous optimization or extra spending is implied.

## D006 — 2026-09-09 UTC: ICLR evidence review and fixed next-pair preparation

The owner asked to continue, prepare the next experimental idea, then tell them
when to start or rent a replacement server; the goal is ICLR with efficiency and
quality. Codex prepared seed23 Paths/GCM on CPU, retaining the selected problems,
base model, training recipe, 1024 updates and exact token/structure matching.
Assignment/order/training use seed23 while evaluation keeps seed17. The proposed
pair reserves 2130 of the 3488 remaining seconds under the original budget.
No prior server was contacted and no GPU work or additional rental occurred.

Independent intermediate-step and identity-operation audits are post hoc for
seed17 and fixed secondary diagnostics for seed23. They do not replace greedy
final-expression correctness. Recent prior work directly overlaps the broad
question; the new roadmap requires a substantive controlled boundary study,
independent pools/seeds and broader evaluation before any strong paper claim.
The next pair is a limited stability gate. The owner will supply/start the
instance after reviewing this concrete next phase; the later roadmap remains a
design and budget decision, not an open-ended training authorization.

## D007 — 2026-09-09 UTC: supplied A800, fixed pair and explicit research journal

The owner supplied a replacement A800 for the prepared seed23 pair and requested
separate records of attempted ideas, motivations, experiment designs, results
and interpretation, followed by a current assessment and local/GitHub paths.
The owner also authorized removal of unneeded old server files given a 50 GB
data disk. All 48 old scientific checkpoint files were independently SHA-256
verified locally and remotely before deleting only the redundant remote
checkpoint directories; code, predictions, manifests and local backups remain.
The data filesystem now has about 41.16 GiB free, so no expansion is needed for
this pair. All 96 Linux tests, nine pinned model-file checks, frozen-data checks
and the 3712-second ledger match passed on the supplied instance.

Execute only the published seed23 Paths/GCM comparison under the original
cumulative budget and full-phase guard. The execution code is the verified
`6128e4266d62f14f063585d4c8e94dbe3ad8c711` milestone. The new
RESEARCH_JOURNAL.md and experiments/E009_seed23_paired_replication.md record
the reasoning before any seed23 output; historical entries are explicitly
retrospective reconstructions. No broader grid or additional budget is implied.

## RESOLVED FOR PILOT V1 — coverage matching and exposure budget
The updated condition table specifies one path and one exposure on a fixed problem set. At comparable response lengths this has fewer supervised tokens than the multi-path condition. A concrete matched-exposure proposal, structural-frequency residuals and length audit must be reviewed before launching this decisive scientific comparison.

Pilot v1 uses four exposures per problem per cycle in every arm, including GCM,
and demonstrates exact per-example token and per-update Paths/GCM structure matching.
See PILOT_V1.md and the immutable matching audit. The earlier issue is retained
above to explain why the original one-exposure row was not implemented.

## RESOLVED FOR PILOT V1 — main data domain
Four distinct inputs in 1..20 yield at most C(20,4)=4845 groups before eligibility filtering. A 4096-problem breadth pool plus large disjoint holdouts does not fit comfortably. Keep the present data engineering-only; review an expanded domain or task design before creating final splits.

Pilot v1 expands to 1..40 and assigns 4096 train, 2048 development and 2048
reserved holdout raw groups before solving. It is a restricted pilot, with large
selection shifts reported explicitly, not the final broad benchmark.
