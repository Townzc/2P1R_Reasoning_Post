# Accepted E8 export-only recovery

Review 2edeee5169c9a05213a0264e57aae96dcad30727 accepted subject to R-1, implemented here. The owner authorizes exactly one export-only recovery and confirms paid checkpoint storage has been enabled, charged from existing Tinker credits. No checkpoint is deleted and all TTLs are retained. USD30 is reserved once inside original T USD340 and combined USD485.

The exporter now reads aggregate checkpoint count and bytes before creating a training client, records a receipt, and stops at either free limit without an explicit paid-storage declaration. The approval binds the revised source and plan hashes. Current API effective rate is reported as returned; the owner confirmation, not the rate field, establishes paid-storage enablement.

E8 has completed 1,024 updates. Recovery performs zero training updates, forward calls or sampling calls, and exports only a sampler. An export failure will not be retried. Original failed evidence stays intact.
