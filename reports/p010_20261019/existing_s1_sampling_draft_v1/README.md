# Original S1 sample-only adapters — prepared, not run

P010 v3 §2.5 explicitly calls for four new sample passes for both already completed S1 students. These adapters prepare that existing scope:500 MATH questions ×seeds0–3, T=.6,p=.95,max1024,2000new outputs per model. Existing273/276 greedy counts and original outputs are reused. No training or old greedy generation is proposed.

The original P009 merged models were saved in temporary worker directories. The persistent final checkpoints and original merge hashes remain. A future new inference worker must load each original final state once, copy every original FP32 adapter exactly, merge inFP32/saveBF16, and match every original saved merged-model/tokenizer file hash. No optimizer instance, optimizer/RNG restore, update, checkpoint selection or old local full-state oracle is invoked. This new reconstruction is necessary for the approved sample evaluation; it is not a training continuation. Full runtime will require actual child exit before vLLM and original parent/source/claim bindings.

Seven new synthetic checks passed once in0.022s, including exact tiny CPU parameter copying and an actual restore-function body with model/state mocked. No original checkpoint was loaded, no old scorer/test was repeated, and no model inference ran. Original metadata copies do not claim external access to private binaries.

There is no Modal entry, actual reservation, upload, dispatch or complete verification/scoring implementation in this draft. The prospective1200-second/2.52USD per-cell T budget is not admitted; the eventual full exact A2 must bind actual input/source/proof, all preceding T/I reservations, original timings, provider capacity and original deadline. No separate code-only approval gate is introduced. Pending original K1/E1d entry/source stays unchanged. Future orchestration must not overlap an untracked pending inference slot with its frozen T-only admission helper.

This is code and evidence preparation, not course-report prose. P009 remains closed; only newly authorized P010 sample outputs are contemplated.
