# Decisions and open questions

## D001 — 2026-09-05 UTC: public reproducible workspace
The user requested starting the agreed project and updating the provided GitHub repository after code and experiments. Import only code and synthetic fixtures; keep private handoffs and connection information outside the public repository.

## D002 — 2026-09-05 UTC: bounded initial compute
The user approved 2 GPU-hours (7200 process-seconds on one GPU) for first-stage checks and feasible pilots. Instance idle billing is separate. Record and enforce cumulative job time. Do not automatically rent another GPU.

## D003 — engineering recipe, not a scientific result
Use the already selected 0.5B base model for correctness/debugging with FP32 trainable parameters and BF16 autocast. The intended 1.5B base remains the main candidate. No switch to LoRA or lower-precision optimizer state is implied by a memory failure.

## D004 — 2026-09-05 UTC: owner-provided A800 continuation
The owner supplied a new A800 server and requested continuation of the planned experiments. Continue the existing 7200-second cumulative budget, carrying forward 737 seconds already charged. First repeat the unchanged 1.5B memory profile, then run the 32-example engineering gate at the previously debugged LR 5e-5. Capture greedy and four-sample development performance before and after adaptation. This does not settle the still-open scientific arm/domain definitions. The A800 hourly price is not known; do not apply the old 4090 reference price to A800 runtime.

## OPEN-001 — coverage matching and exposure budget
The updated condition table specifies one path and one exposure on a fixed problem set. At comparable response lengths this has fewer supervised tokens than the multi-path condition. A concrete matched-exposure proposal, structural-frequency residuals and length audit must be reviewed before launching this decisive scientific comparison.

## OPEN-002 — main data domain
Four distinct inputs in 1..20 yield at most C(20,4)=4845 groups before eligibility filtering. A 4096-problem breadth pool plus large disjoint holdouts does not fit comfortably. Keep the present data engineering-only; review an expanded domain or task design before creating final splits.
