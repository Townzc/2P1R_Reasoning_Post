# Modal checkpoint inventory and authorized L/K4 cleanup

Authority: fb5c77bbf5a46c5d30843fb9f00a94aef1255dfa. Snapshot 2026-11-15T05:09:13.111605+00:00. A8 group A continues independently.

The deletion manifest contains 36 exact weight files from 24 accepted main-grid L/K4 runs, totaling 124.255230 GiB. Public raw outputs, labels and checkpoint manifests were verified against their archived SHA256 and Git objects; remote checkpoint manifests match. Active Modal applications are mapped to new A8 requests and do not reference any deletion target.

| Workspace / volume | a L/K4 files / GiB | b P/K8/R | c other weights/state | d assets/cache | e evidence | f older projects |
|---|---:|---:|---:|---:|---:|---:|
| tangzhice / p012-g0-assets-results-20261111 | 28 / 101.252 | 48 / 179.501 | 39 / 135.879 | 162 / 77.216 | 3062 / 4.523 | 0 / 0.000 |
| tangzhice / sft-allocation-midpoint-v1 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 | 0 / 0.000 | 173382 / 780.299 |
| townzc / p012-g0-assets-results-20261111 | 8 / 23.003 | 24 / 69.010 | 5 / 0.688 | 36 / 5.772 | 782 / 0.825 | 0 / 0.000 |

File sizes are logical regular-file bytes. Symlink targets are counted once; directories are excluded. Category c includes 29.92 GiB of reproduction optimizer/state files, explicitly retained. A8 additions after this snapshot are outside the deletion manifest.

## Storage and pending decisions

Closed UTC days 2026-11-13 / 2026-11-14: tangzhice net volume charges $0 / $0.76402148; townzc $0 / $0. Last checked balances: tangzhice $29.05, townzc $13.74. These are pre-cleanup reads. B/C admission requires a fresh balance and daily-cost read after cleanup.

At the observed $0.09/GiB-month rate, a November daily estimate uses GiB × 0.09 / 30. These per-item estimates are gross storage costs; the actual net bill also reflects the shared free allowance. Detailed per-run/project estimates and recommendations are in READ_ONLY_INVENTORY.json.

| Retained category | GiB | Gross USD/day | Recommendation |
|---|---:|---:|---|
| Main P/K8/R | 248.510 | 0.746 | Keep through 12/14; owner decides any early deletion. |
| Other P012 weights/state | 136.567 | 0.410 | Recommend removing completed A5, reproduction and bridge weights/state after owner approval and archive checks. |
| Older project volume | 780.299 | 2.341 | Prioritize selective cleanup of P010/P011 checkpoints; inspect large tar archives first. Keep evidence files. |

Downloaded assets, logs, evaluation outputs, tokenizer/configuration files and manifests are retained. No entire volume or account/billing setting is changed.

## Deletion procedure

DELETION_MANIFEST.json and the complete verification receipts are published before deletion. cleanup_weights.py rechecks public archive identities, remote manifests, exact file sizes and active application paths for each run. It removes only the listed .safetensors leaf paths with recursive=False, then relists the run directory and checks every retained regular file for unchanged size and mtime. Deletion receipts will be added after execution.

## Execution receipt

All 36 authorized files were removed after manifest publication8f78f7f9, freeing124.255230GiB. AFTER_INVENTORY_CHECKS.json compares every listed path: removed paths exactly equal the published manifest, no other previous files disappeared. All retained files are unchanged apart from ongoing A8 writes. Per-run before/after directory listings are in the workspace DELETION_RECEIPT files.

After-cleanup balances: tangzhice USD28.08, townzc USD13.74. Closed daily net storage costs remain0/0.76402148 and0/0. R-1 storage reserve is0.76402148×10+1=USD8.6402148. A new closed billing day reflecting cleanup is not yet available; no unobserved saving is credited. A remains admitted; B/C await completion/accounting of A and their current gate.

Modal’s [official pricing](https://modal.com/pricing) includes 1 TiB per month of free volume storage. Per-item gross cost estimates therefore differ from net workspace charges. PRICING_CONTEXT.json records this allowance and a constant-inventory illustration; admission continues to use the observed daily net bill required by R-1.
