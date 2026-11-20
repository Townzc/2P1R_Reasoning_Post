# Audit 20261014ce: `p009-stage1-NC-replacement-closeout-code-r1`

- **Scope:** `p009-stage1-NC-replacement-observation-and-pair-publication-code`
- **Target:** `b63ab5182db63844680be958759fa477fe21000c`
- **Manifest:** `cd8a5410457ca53eb1cea8abaef232ce703f1d6605283c107ad7fd643d69decc`
- **source_files** (exact, as listed in SOURCE_BINDING; all three hashes recomputed at the target):
  - `scripts/p009_nc_replacement_observe.py`: `8536d22c27f4fc87066d2c6c26e9819e1b28f8767b3fc9c542da1318da5761c8`
  - `scripts/publish_p009_nc_replacement_pair.py`: `3c7dad52132614585720883545b6b9198bce55952586b3cddc48fe7d42dfadc7`
  - `scripts/publish_p009_stage0_result.py`: `708d426fc1097e00e5f8a56b5daa6441c87c25c7eb62b3cf1477fb8d6f94ab26`
- **runtime49:** pinned. All 49 hashes match the bytes I accepted in cd Part B.

## Decision: PASS-WITH-NOTES
This verdict covers the helper code only. No replacement result is reviewed here.

## What I checked
**Pair publisher**
- **Validation order.** These all run before `mkdir`:
  - the code review and the registered analysis review (target `2c7d6b5c`), with the runtime and analysis bytes;
  - the sent-vs-dispatch payload;
  - both report files;
  - `check_lineage`, which requires:
    - the new claim and terminal to be `completed` with 655¢;
    - every `required_records` entry, including the old campaign;
    - the old NC3200 terminal to still be `failed` with evidence `bcf84754…`;
    - the dispatch and logical markers to equal `marker(...)`;
    - all 10 apps to be stopped with zero containers;
    - the full oracle to be bound to the new envelope and its state SHA.
  - Also before `mkdir`: `verify()` of the new export, `original_sibling()`, the 1319-ID equality for both runs, and the projection.
- **`original_sibling()`.** It reads only the fixed parent packet (manifest `74c4590c…`), with each used member's size and SHA checked. That covers:
  - the NC400 oracle gz, checked through `check_oracle` against state `f9aca4bf…` and against SUMMARY;
  - `PRESERVED.json` = `75f29c75…`;
  - the failure manifest digest = `bcf84754…`.
  It never rebuilds old archives or loads state.
- **Decision call.** `nc_result(ids, NC400, replacement)` gives `n3200_minus_n400`, the registered signed rule. It is called once. The failed parent is recorded with `filled_as_zero=False`.
- **Projection.** It removes only the `local_report_path` and `source_snapshot` keys, at any depth, each with its digest recorded. Provider actors are removed. The "not blind to NC400" chronology is written into SUMMARY and README.

**Observer**
- **Remote access.** It uses only `Dict.from_name`, `Volume.from_name` reads, `container list` and `app info`. It makes no remote writes, no spawn and no scoring.
- **Local writes.** Create-only.
- **Timer.** A hard 600 s `os._exit(124)` timer.

**Tests.** 8/8 new tests pass here.

## Notes
- **N1 (same as cc N1, low risk).** `PROVIDER_PROJECTION` (`lifecycle['created_at']`), `archive_original` and `nc_result` still run after `mkdir`. A `KeyError` or I/O failure there would leave a permanent partial publication. Real Modal `app info` has always included `created_at`. I accept this as is.
- **N2.** The `'/Users/'` guard only catches macOS-style paths. The key-based projection is the real protection, and it is enough for the known keys.
- **N3.** Pair A4 will re-score all 1319 replacement outputs from the published raw data, independently of the oracle, as I did for NC400.

## 科学信号检查 (science-signal check)
No new outcome.
