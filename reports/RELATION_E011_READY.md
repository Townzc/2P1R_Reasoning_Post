# E011 ready for an owner-started A800 — CPU preparation only

**Ready locally; GPU experiment not_run.** C015 extracted and independently
rechecked the fixed engineering subset from published C014 records. The original
ledger is unchanged:5740/7200 process-seconds used,1460 remaining,zero reservations.
No server was contacted or started and no model inference/training was performed.

## What this step resolves

The new task's CPU support and shortcut gates do not establish whether the
pinned1.5B base can learn valid certificates, or how much its1137-token examples
cost. E011 makes those questions executable in one bounded engineering run. It
is multi-route only and cannot establish an allocation treatment effect. Passing
memorization is insufficient for generalization or an ICLR contribution.

## Prepared data and verification

Source/configuration were published at
`8eeb0f9883759a69ca42540932b98d71b2c64414` before extraction. C015 selected the
predeclared seed401 indices0–31 and seed481 indices0–15, with no filtering or
replacement. Extraction took0.824 seconds; independent reload/check took3.374
seconds. The five-file compact input directory totals167,834 bytes.

- 32 training worlds,128 references;16 development parents,all world groups distinct.
- 48 records match the original C014 archives exactly;192 clean references and240
 view prompts pass exposed-table and exact tokenizer checks.
- 256 updates,1024 presentations,each question32 times and each route8 times.
- 103,424 supervised response tokens including EOS,1,164,288 processed tokens,
 zero padding and no truncation. All clean sequences1137 tokens.
- 48 clean evaluation prompts have1036 tokens;32 deletion prompts have949.
 With128 generated tokens,maximum generation context1164 is within1536.
- 42 focused checks:40 passed,2 GNU-timeout integration checks deferred to the
 supplied Linux server. Real pinned-tokenizer release regression passed.
 CPU toy-gradient fixtures do not verify actual CUDA/model execution.

The launcher refuses stale/missing ledger, reused run identities, dirty or
unpublished source, changed compact inputs and incomplete full-phase budget.
Exact ledger/full-cap checks run again under the reservation lock, so a competing
reservation cannot silently shorten this phase. Old callers keep their original
behavior. No live ledger is committed to the public repository.

## Frozen GPU plan

Fresh pinned Qwen2.5-1.5B base,full FP32 parameters/BF16 autocast,AdamW5e-5,
batch4/micro2,nonreentrant gradient checkpointing andSDPA. Fixed256 updates;
profile updates9–72. One trajectory,no automatic retry,seed sweep or extension.

Greedy baseline16 clean dev; final32 clean train and16 dev parents across
clean/useful-delete/irrelevant-delete:96 generations total. Save all token IDs,
raw outputs,proof/answer/EOS metrics,and final teacher-forced NLL on128 train
references. Only outer ASCII whitespace is normalized. Engineering gate:
32/32 complete verified EOS-terminated train proofs,zero train truncations,
NLL<.2,and complete dose/profile. Any legal route may pass; a correct final
answer without a valid complete certificate cannot pass.

720-second process cap plus15-second guard reserves at most735 of1460 remaining,
leaving725 unreserved. Actual process time is charged; this is a cap,not a speed
forecast. Setup and provider idle/storage billing are separate. No scientific
pair or additional GPU allowance is approved by this preparation.

The [clean-checkout receipt](relation_engineering_c015_clean_checkout.json)
verifies default launcher inspection at published commit
`f4aec50dab56b50fcdef0295835303a38866b115` using only tracked inputs plus the
externally supplied pinned tokenizer and current private ledger. It completed
in3.143 seconds,created no run/runtime directory and left the ledger byte-identical.
No private matching inventory or server state was needed for input verification.

## Start and recovery

The owner can now start/provide **one A80080GB**. On connection,fetch current Git,
restore the exact current15-receipt ledger and original base,check the environment,
run mandatory Linux timeout tests,confirm an idle GPU and at least12GiB free on
the run filesystem after cache setup. A50GB disk need not be expanded in advance;
measure free space first. One final FP32 checkpoint is approximately6.2GB.
Do not delete uniquely required prior artifacts or automatically start training
on an instance clone.

The default command only inspects; `--execute` launches the single bounded job.
After completion or failure,save compact outputs and receipt,reconcile the ledger,
independently score outputs,verify required weights and a separate backup,publish
the result/analysis,and follow the owner's existing normal-shutdown preference.
The process watchdog itself does not switch off a provider instance.

## Files and reproduction

All public paths are relative to the repository root and recoverable from GitHub:

| Artifact | Path |
| --- | --- |
| Motivation, hypotheses, fixed design, stop rules | [E011 registration](../docs/experiments/E011_relation_engineering.md) |
| Exact recipe | [overfit.json](../configs/relation_engineering_e011/overfit.json) |
| Frozen release identities | [release.json](../configs/relation_engineering_e011/release.json) |
| Compact48-world bundle and source manifest | [input directory](../runs/relation_engineering_c015_r1) |
| Complete token/exposure accounting | [budget.json](../runs/relation_engineering_c015_r1/budget.json) |
| CPU re-verification | [verification receipt](relation_engineering_c015_verification.json) |
| Test evidence | [test receipt](relation_engineering_c015_test_receipt.json),[full log](relation_engineering_c015_tests.log) |
| Default-inspect bounded launcher | [run_relation_engineering.py](../scripts/run_relation_engineering.py) |
| Standalone training and generation | [relation_experiment.py](../src/relation_experiment.py) |
| Post-run raw-token/proof/dose audit | [output auditor](../scripts/audit_relation_engineering_outputs.py) |
| Migration and next commands | [NEXT_SESSION.md](../docs/NEXT_SESSION.md) |
| Running rationale/result/analysis history | [RESEARCH_JOURNAL.md](../docs/RESEARCH_JOURNAL.md) |

Data manifest SHA256:
`ddb0068a2ddef8150948b7f8eaf0f2b86d3c3f9a42268c7d7725f44ee1afb854`.
Do not overwrite C015 or relabel these observed diagnostic worlds as a final test.

After actual execution,the next decision depends on the preserved failure types,
full-proof gate,measured cost and development behavior. A successful engineering
run would support preparing a separately reviewed paired allocation experiment
with fresh frozen scientific groups; it does not authorize that experiment.
