# Accepted E8 export-only recovery

Review 2edeee5169c9a05213a0264e57aae96dcad30727 accepted subject to R-1, implemented here. The owner authorizes exactly one export-only recovery and confirms paid checkpoint storage has been enabled, charged from existing Tinker credits. No checkpoint is deleted and all TTLs are retained. USD30 is reserved once inside original T USD340 and combined USD485.

The exporter now reads aggregate checkpoint count and bytes before creating a training client, records a receipt, and stops at either free limit without an explicit paid-storage declaration. The approval binds the revised source and plan hashes. Current API effective rate is reported as returned; the owner confirmation, not the rate field, establishes paid-storage enablement.

E8 has completed 1,024 updates. Recovery performs zero training updates, forward calls or sampling calls, and exports only a sampler. An export failure will not be retried. Original failed evidence stays intact.

Storage chronology: the owner initially reported Paid enabled, but the account was still Free. R-1 recorded rate0 and100checkpoints and admitted against the explicit owner declaration. The single export succeeded at23:24:51UTC. Three subsequent NLL clients received402before any forward calls. The authorized Paid switch was actually saved at23:28UTC and verified at rate0.1 before the NLL retries. STORAGE_TIMELINE.json records this discrepancy; historical approvals and receipts are unchanged. CHECKPOINT_RETENTION_VERIFIED.json confirms all100originalcheckpoints retain identity,size andexpiry.
