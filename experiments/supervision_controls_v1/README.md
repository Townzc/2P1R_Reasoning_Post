# LT002 execution package

Read [PROTOCOL.md](PROTOCOL.md) for the scientific question, exact finite dose,
interpretation limits, estimated time and hard resource ceiling. This package
does not restart the completed pilot and does not implement three-seed confirmation.

## Components

- `analyze_existing.py`: local descriptive audit of already-observed MATH scores;
  all-question uncertainty bounds, no model or judge calls.
- `freeze.py` and `masks.py`: create immutable random and joint position/difficulty
  masks from the original verified annotations. No re-annotation or outcome selection.
- `runner.py` and `train.py`: artifact admission, two fresh-base training runs and
  eight development generation runs. Defaults to artifact-only preflight; model
  execution additionally requires `--execute` and finite power-on/deadline arguments.
- `analyze.py`: independent CPU process, exact reuse of four old score runs,
  scoring of eight new runs, paired contrasts and decoding interactions.
- `io.py`: disjoint output paths, physical caps, immutable records and source guard.
- `HISTORICAL_BINDINGS.json`: endpoint, raw-batch and old-score hashes extracted
  from the independently retained final pilot audit. Source identity is recorded.

## Deployment sequence

1. Publish the tested source on the assigned long-term branch. Build a portable
   archive with both experiment packages and the original frozen input release.
   Bind Python sources, configuration files and protocol to the published commit
   in `SOURCE_INVENTORY.json`; provide its SHA256 independently to the launcher.
2. Confirm the owner-opened original instance, price, account balance, retained
   volume and one visible A80080GB. Record actual power-on time. Inspect PIDs before
   launching anything. Original endpoint weights, annotations and raw greedy-dev
   outputs must still exist. Never reconstruct missing artifacts by replaying them.
3. Run `freeze` with `--prior`, `--release` and a unique, disjoint `--output`.
   Review `MASK_AUDIT.json`, including forced overlap and residual continuous-feature
   imbalance, before training. Report poor balance/low mask variation instead of
   tuning bin counts from outcomes or claiming a decisive semantic control.
4. Run `runner` **without** `--execute`; supply the original model/input paths,
   separate new checkpoint volume root, original checkpoint root, published source
   commit and archive inventory SHA. Its full artifact preflight must pass.
5. Use the existing Linux environment for focused tests and the real tokenizer
   checks. Verify current host-memory/disk headroom and allocator settings. Do not
   leave GPUs idle to repair an unprepared source/runtime deployment.
6. Establish a finite detached launcher and independently verified provider normal-
   shutdown backstop. Record the absolute GPU deadline at least15min before the
   eight-hour whole-instance cap. Run `runner --execute` under a hard GNU timeout
   and `analyze --watch` under its own bounded CPU deadline. No duplicate workers.
7. Stop early on completed GPU/CPU markers, collect compact raw outputs/scores,
   verify new final checkpoint/RNG manifests and ledgers, and confirm provider OFF.
   Do analysis/publication locally after shutdown. Check raw record hashes before
   calling any run complete. Preserve failures, unresolved scores and unique states.

The runner does not start, stop, rent, reconfigure, charge or delete an instance.
Provider supervision and publication remain necessary deployment steps. The CPU
toy tests do not verify GPU feasibility or the continued availability of old files.
Runtime/software drift fails admission; it does not silently create permission to
rerun the historical baselines. Existing sampling results are not fresh holdouts.
