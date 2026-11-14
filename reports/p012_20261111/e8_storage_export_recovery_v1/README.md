# E8 completed training: storage and sampler export recovery

E8 finished all 1,024 updates and saved its final training state. Its first sampler export failed when the organization reached the free limit of 100 checkpoints. E4 completed and its MATH-5000 accuracy is 55.32%; E4 and later new results remain pending the next combined result review.

The saved E8 state is verified through the API as Qwen3.5-4B, LoRA rank32, with attention, MLP and unembedding enabled. Original request, all losses, row order, partial token usage and state reference are archived. The failed trace is preserved privately byte for byte and redacted only for the public copy. This state has all1,024 updates; no training restart is proposed.

## Concrete storage proposal for the owner

Current usage:100 checkpoints,64.29GiB. Enable the paid storage plan while keeping all existing artifacts and TTLs. [Official pricing](https://tinker-docs.thinkingmachines.ai/administration/checkpoint-storage-pricing/) is $0.10 per GB per month, applying to all storage once paid is enabled. The maximum-size projection for all existing checkpoints, E8 export, L64 and27 original GSM cells is108.23 decimalGB. Assuming the entire maximum remains65 days and using28 days per month gives $25.13. Reserve **$30 within the existing original T $340 and combined $485**; no topup. Initial original T math reserve199.747345 plus full GSM cap105 plus30 is334.747345, within340. The current ledger already reserves the first GSM batch as part of that105, not in addition to it.

## Concrete E8 export proposal and first-use review

`experiments/p012/tinker_export_recovery.py` verifies the bound complete state, loads its weights using the standard SDK and calls `save_weights_for_sampler` exactly once. It makes zero forward, optimizer or generation calls. It writes a new export directory; the original failed attempt is never overwritten. Nine contract tests, a read-only preflight against the actual saved run, and remote checkpoint identity checks pass.

The export is gated on owner permission for this additional infrastructure recovery, storage disposition, and Claude's review of this new path. The E8 training run has already used its one automatic retry. P012 §12 states “每条新代码路径（评测器、训练配置与启动器、数据构建、分析脚本）在首次运行前由 Claude 审查一次”. Review this export-only path once; existing GSM scientific paths remain approved and their sampling queue proceeds.

After an approved successful export: preserve the failed attempt, attach the original training request/loss/order/state and the export receipt to a completed training evidence directory, and use the original reserved full MATH5,000 greedy generation/scoring paths. Preserve partial-usage evidence and count the training tokens once; no update or dataset changes. Do not run another automatic retry if the export fails. The new export receipt must be included in the combined result review.

[Plan and exact evidence hashes](PLAN.json) · [Failed-export evidence](failed_export_evidence.zip) · [Storage projection](STORAGE_PROPOSAL.json) · [Remote weight identity](REMOTE_WEIGHTS_INFO.json) · [Checks](CHECKS.json) · [Tests](CPU_TESTS.txt)
