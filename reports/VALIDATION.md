# Validation record — 2026-09-05 UTC

- Original 20 unit tests passed locally under Python 3.12.14. The system Python 3.9 is unsupported (integer bit_count); an initial wrong-directory/old-interpreter attempt failed and was corrected without changing arithmetic semantics.
- Expanded suite: 35 tests passed on the training server with Python 3.12.3 and PyTorch 2.8.0+cu128. Includes exact arithmetic and safe parser rejection, deterministic group splits, prompt/EOS/padding labels, accumulated-gradient equivalence under token normalization, independent attention batch rows, timeout accounting, stale reservation refusal, and exhausted-budget nonexecution.
- `pip check` on the training environment: no broken requirements.
- CPU generator reproduced 176 eligible problems, 704 stored paths and five 128-presentation arms; eight JSONL SHA-256 digests exactly match the imported fixture. See cpu_reproduction.json. This is engineering data, not a final scientific split.
- Remote direct Hugging Face access failed with network unreachable. Public model bytes are being obtained from a mirror; trusted expected digests were fetched from the official API at exact revisions. Verification reports will be added before model execution.

The environment overlays pinned project packages in a venv with system site packages, reusing the image's PyTorch. It is not a fully independent environment. A hardware/package manifest and explicit recreation checks document that limitation.
