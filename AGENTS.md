# Project instructions

Read README.md, docs/PROTOCOL.md, docs/DECISIONS.md and reports/STATUS.md before substantive changes.

## Scope and evidence
- Controlled SFT only. Main question: within-problem paths beyond global structure coverage, repetition and surface rendering.
- Arithmetic first; graph/relational task and OLMo 2 1B are planned boundary checks. RL is out of scope unless the user explicitly reopens it.
- Main model candidate Qwen/Qwen2.5-1.5B base. Qwen/Qwen2.5-0.5B is engineering/debug only. Never silently substitute Instruct or change tuning methods across conditions.
- P/T/R are constrained under fixed budget. Structural syntax is a proxy, not cognitive-strategy equivalence. Never invent outcomes or novelty.

## Workflow
- Before substantial work, classify the task and recommend Max or Ultra to the owner, with a short reason. Distinguish a recommendation from an actual settings change; do not claim to have switched modes without evidence. This preference does not itself authorize delegation or additional compute.
- The user authorized this repository for code and experiment updates. Commit and push each completed code/experiment milestone, including failures and limitations.
- Server replacement is routine. Treat GitHub as the authoritative code/compact-record history and keep a current next-session handoff. Before declaring an instance disposable, verify publication, checkpoint backups and the latest cumulative ledger; never leave unique required state only on that instance.
- A cloned instance is a transfer convenience, not a new experiment or compute budget. Verify its commit, environment, artifacts and ledger before reuse; restore only artifacts needed for the next task. Do not auto-launch training when an instance starts or is cloned.
- Keep private correspondence, handoffs, credentials, SSH endpoints and local absolute user paths out of this public repository.
- Record code commit, model/tokenizer revisions, data hashes, commands, seeds, token counts, steps, duration, GPU peak memory and evaluation configuration.
- Keep raw predictions and small logs; checkpoints and caches are excluded. Maintain migration and artifact-transfer instructions.
- Data outputs are immutable. Refuse overwrite; group-split before path/render augmentation. Never tune on final test. Parse arithmetic using AST whitelist and exact rationals, never eval.
- Tokenize exact serialization; mask prompts/padding; include EOS; no cross-sample packing. Normalize each update by total supervised target tokens.
- Run meaningful correctness tests, 32-example overfit and measured profile before scaling. Preserve failed runs.
- First-session GPU process runtime budget: 7200 seconds, explicitly approved by the user. Enforce per-job bounds and a cumulative ledger. No paid APIs or extra machines are authorized.
- Main-grid, scientific protocol changes and submissions need user review. Prepare a concrete proposal before requesting review. CPU/data/documentation work can continue independently.
- The owner approved the finite pilot v1 sequence on 2026-09-08. Follow docs/PILOT_V1.md and program.md: CPU preflight, bounded A800 calibration, then one paired-seed comparison only if the gate and complete-phase budget pass. This does not authorize a main grid or holdout evaluation.
- Chinese user updates; English code and paper text. Maintain AI_USE_LOG.md.
