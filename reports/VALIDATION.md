# Validation record — 2026-09-05 UTC

- Original 20 unit tests passed locally under Python 3.12.14. The system Python 3.9 is unsupported (integer bit_count); an initial wrong-directory/old-interpreter attempt failed and was corrected without changing arithmetic semantics.
- Expanded suite: 35 tests passed on the training server with Python 3.12.3 and PyTorch 2.8.0+cu128. Includes exact arithmetic and safe parser rejection, deterministic group splits, prompt/EOS/padding labels, accumulated-gradient equivalence under token normalization, independent attention batch rows, timeout accounting, stale reservation refusal, and exhausted-budget nonexecution.
- `pip check` on the training environment: no broken requirements.
- CPU generator reproduced 176 eligible problems, 704 stored paths and five 128-presentation arms; eight JSONL SHA-256 digests exactly match the imported fixture. See cpu_reproduction.json. This is engineering data, not a final scientific split.
- Remote direct Hugging Face access failed with network unreachable. Public model bytes are being obtained from a mirror; trusted expected digests were fetched from the official API at exact revisions. Verification reports will be added before model execution.

The environment overlays pinned project packages in a venv with system site packages, reusing the image's PyTorch. It is not a fully independent environment. A hardware/package manifest and explicit recreation checks document that limitation.

## GPU diagnostic milestone
`overfit_debug_20260905_r1` is invalidated for uncommitted server source provenance. The repaired guard requires every source/config file to be Git-tracked. The first valid run (`r2`, code 922d517) completed 400 updates, with 100 measured updates after 10 warmups. It did not meet the 95% train-correctness gate (25/32); low reference NLL alone is insufficient. Raw generation failures remain in the denominator. It used 342 charged seconds; the aborted launch reserves a conservative 120-second upper bound. Total so far: 462/7200 seconds.
