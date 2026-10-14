# Claude audit 20261013al — p008-t8-public-collection-provenance-r1 @ b4796e6e: **PASS**

## Diff against the reviewed publisher
I compared `publish_t8_cap_result_v2.py` with the publisher I reviewed in 20261013aj (94eb84e6). Apart from one rewrapped line of README text, **the change is purely additive**.

These parts are byte-identical to the reviewed version:
- every earlier assertion;
- archive selection, which still excludes `intent.json` and any `.pt` file;
- tar creation;
- per-member readback;
- the copies of ENVELOPE, SOURCE_BINDING, RESOURCE_RELEASE, LEDGER and SUMMARY.

The new collection metadata is computed **before** the output directory and the first immutable file are created, so a completed packet is never patched afterwards.

## Q1. The route is reported honestly
- **Named-wave route.** It applies only when `closeouts/<run>/COLLECTION.json` exists. All of the following are required:
  - `passed`, with 0 model calls and 0 remote writes;
  - one ledger scan, with the terminal unchanged before and after;
  - the run present in a duplicate-free run list;
  - the common ledger sha equal to the closeout ledger;
  - the wave directory under `t8_collection_waves`;
  - `READ_INTENT.runs` = `COLLECTION.runs` = `COMPLETED.runs`, with `COMPLETED.passed` true and its ledger sha equal;
  - the envelope sha in the intent equal to the canonical `result.json` sha.

  **A partial or failed wave has no `COMPLETED.json`, so the publish fails closed and cannot claim the run as complete.**
- **Single-run route.** It is claimed only if no wave intent names the run. In git, only the wave collector writes `closeouts/<run>/COLLECTION.json`. The single-run collector itself is local and not in git, so I could not inspect it. If it ever wrote that file without the wave fields, the publish would fail closed rather than mislabel the run.
- **Callback recovery.** It is recorded only when `receipt_recovery_t8_cap/<run>` exists. It requires:
  - a passing proof with 0 model calls and 0 remote writes;
  - the N2 and deviation flags;
  - the retained `return_error.type == ConnectionError`;
  - exactly the 4 recovered files, each with sha and size equal to the exported evidence.

  The route is then labelled `bounded_readonly_original_volume_reconstruction`, and the error-file and proof hashes are recorded.

## Q2. Hashes and privacy
- **Hashes.** Public COLLECTION records the sha of each of these: the original `result.json`, `ledger.json`, `provider.json`, `TIMING_READ_METADATA.json` and the wave files, plus the recovery hashes where they apply.
- **Privacy.** No private gate payload and no full recovery payload is copied.

## Note
**L1 (LOW).** The publisher reads `c['wave']` as a stored absolute path. That is acceptable on the same host, but the packet should not be republished from a different checkout path. That is consistent with "never rerun publisher".
