# Public math pilot: resource feasibility and preflight not run

**The GPU preflight did not run, and the four-arm pilot is not complete.** The provider was confirmed OFF at **2026-09-17 19:40:40.554989 UTC**, and its timer was confirmed cleared at **19:42:29.001539 UTC** ([closeout record](COST_AND_CLOSEOUT.json)). No execution source was deployed, no GPU worker or model call ran, and formal/nonformal optimizer updates, mask forwards and generated outputs are all zero. Final CPU missing-image corrections left insufficient time for a bounded preflight plus the required 15-minute export/shutdown reserve. The one-hour/CNY10 preflight authorization closed unused for GPU work; preparation still belongs in the powered-window ledger.

The Math-1.5B base has 1,543,714,304 parameters. Preserving four distinct terminal FP32 models and four FP32 AdamW moment pairs requires at least **74,098,286,592 bytes (69.009 GiB)**, without duplicating inference weights. This is a tensor-only lower bound; metadata, raw outputs and logs add bytes.

The plan permits step64 weights to be temporary. After all midpoint evaluation is durable and either a complete independent backup is acknowledged or the same arm's step128 recovery is verified, those temporary weights may be removed while retaining their hashes, dynamics and full dev outputs. Omitting step64 weight transfers still leaves the terminal lower bound above. Old experiments remain protected.

The operator measured a 64-MiB SSH download in 21.743780792 seconds (**2.943 MiB/s**) and 16-way HTTPS range download in 37.713938542001415 seconds (**1.697 MiB/s**). Applying the SSH rate to just the four terminal states gives **6.669 hours**. The protocol's 1.3 safety factor increases this to **8.670 hours**, already above the usable envelope of at most approximately **8.5 hours** observed during that feasibility check, before subtracting time already spent. This was a historical resource snapshot, not a currently running allocation. At the verified CNY7.98/hour this transfer-only conservative proxy is **CNY69.1842**, not an invoice.

GPU throughput and complete-stage time are **unknown**. For a future admission decision, use one complete resource estimate in seconds:

```text
T = used_setup
    + 1.3 * (T_train_512_measured_updates
             + T_mask_8192_sequences
             + T_generate_31203_outputs
             + T_checkpoint_IO + T_backup)
    + 900
```

`used_setup` is factual powered preparation/idle time already spent. Training, annotation and decoding terms require actual per-arm and length-aware GPU measurements; checkpoint I/O includes saving, verification, hashing and loading. Backup uses measured end-to-end durable transfer; the additional 900 seconds is the minimum export/shutdown contingency. Evaluate the full expression against cumulative time and money limits once, without omitting benchmarks or requesting successive per-arm exceptions. No GPU measurements or complete total are available from this window.

Even within the proposed 12-hour ceiling, the safe raw-backup projection and 900-second reserve leave only **about 3.08 hours before subtracting already-used setup**, for every other term after its safety factor. The factual preparation window already used 2,087.554989 seconds, reducing this hypothetical remainder to about **2.50 hours**. Whether those operations fit is unknown. Compression or faster export could change the projection only after representative full-state size, processing time, integrity and durable-throughput measurements; neither is an established solution. The 12-hour/CNY120 proposal is not proof of available resources or formal admission. No recharge, expansion or extra instance follows from this finding.

Disk is separately manageable with deliberate placement. The operator observed 40,179,576,832 free bytes on data and 31,979,679,744 on system overlay. The helper checks each actual filesystem independently and keeps a 2-GiB reserve. It shares model bytes between inference and recovery, commits a small pointer only after component verification/fsync, and permits terminal optimizer removal only after complete independently verified local backup. Engineering smoke states may be explicitly discarded after verified reload and durable compact receipts; they are not scientific endpoints.

Sixteen tiny CPU tests passed, including exact four-update versus two-plus-two model/AdamW/scheduler/RNG equivalence, pointer-interruption retention, path bounds, per-filesystem space checks and constrained cleanup. This does not establish GPU throughput or whole-pilot feasibility. No model was run; all scientific results remain unavailable. Confirmed shutdown closes this resource window and does not mean the pilot completed.
