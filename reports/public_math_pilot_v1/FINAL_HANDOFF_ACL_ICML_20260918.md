# Final handoff to long-term ACL/ICML research

Status: complete, provider OFF, heartbeat paused, no work queued. Read
[FINAL_EXECUTION_SUMMARY_ZH.md](FINAL_EXECUTION_SUMMARY_ZH.md) first.

The current branch is `codex/iclr-2027-sprint`. The existing long-term branch
`codex/icml-acl-2027` was previously observed at
`17d765e863249870ccfab4340e3611b4798a2f81`; it was not modified or merged.
The owner will decide the next direction there. That branch's old LT001 status
and budget cannot supersede the completed experiment history on this branch.

## Carry forward

- E044-B0/E044/E045/E046/E047 are complete; all science, source/data identities,
  retained failures, score bounds and final receipts are linked from the final report.
- Preserve the negative primary result, single-seed limitation, non-bitwise TrimSFT
  replay,128 lost generations and32 lost updates; do not relabel them as new seeds.
- Public MATH-500 and GSM8K outputs have now been seen. Neither is a fresh tuning
  holdout. New development decisions require a distinct confirmation plan.
- Existing E031–E043 arithmetic results retain their original small-sample and
  exploratory limits. The prior stage review remains historical, not final status.
- All final128 model/optimizer/RNG artifacts and raw journals stay on the stopped
  persistent volume. Compact scores/hashes are independently retained; full binary
  second-copy backup is not claimed. Old E015 unique-weight recovery remains open.
- The provider showed automatic release after15 stopped days, approximately
  October3 for the current instance. Decide durable storage before that boundary.
  No release, deletion, renewal, automatic restart or migration is authorized here.

## Resume rule

Do not replay training, preparation, completed generation or scoring. No remaining
coverage exists. The next task starts with owner selection of a research question
and a finite protocol; source, CPU checks, budget and measured/assumed throughput
must be ready before requesting GPU startup. Use server identity information only
from the private handoff, never publish credentials or SSH endpoints.

Before every future experiment estimate training, generation, CPU scoring, setup
and closeout wall time, GPU-hours, cost range/ceiling, disk/memory and stop rules.
CPU analysis and documentation do not require two idle A800s. Exact-contract
outputs can be reused; unrelated scientific settings cannot silently inherit them.

The final publication commit is the Git commit adding this handoff and FINAL_*
artifacts. It supersedes the earlier benchmark-only milestone e74785f0. Find it
with `git log -1 -- reports/public_math_pilot_v1/FINAL_EXECUTION_SUMMARY_ZH.md`.
