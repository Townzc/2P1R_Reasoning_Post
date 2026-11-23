# A10 LogiQA execution and endpoint reviews

[Live queue, budgets and published packets](STATUS.json) · [Initial API receipt](INITIAL_BILLING_AND_STORAGE.json) · [Accepted data and source review](../../../audit/claude/20261122a/REVIEW_b8f08cc7_A10_combined_pretraining.md)

The 4B and 9B untrained baselines run first. The twelve 4B training arms follow the order in the amendment. Each trained checkpoint is evaluated on all 1,572 test items. Every endpoint gets a separate archive, manifest and result for independent review.

Each call has a published [admission](admissions), [request](requests) and [launch receipt](launches). The timestamped prediction and output hash are published before scoring. Each finished packet is pushed before the next endpoint starts. The controller runs on the local Mac and needs connectivity and an awake system to submit later steps. User relays review requests to Claude.

The ledger counts S1 once at $40.314645282. Until provider billing settles, completed calls use measured uncached token cost. Outstanding calls retain their reservations. A training admission also holds its subsequent evaluation. The greedy reservation uses 1.5 times the highest measured full 4B greedy cost available at admission, starting with the 4B baseline and incorporating L when it finishes. The post-training call replaces its existing hold. Training uses frozen input tokens times the training rate times 1.5 plus $0.10. The baseline, training/evaluation and whole-phase caps are $6, $125 and $200.

The supervisor verifies source and request identities before each launch. A hard budget breach or incomplete service call stops the queue with its reservation and local evidence. A restart adopts recorded calls and completed outputs. LogiQA prompts and reversible prompt tokens stay local. The scientific runner, scorer and configuration match the accepted hashes.
