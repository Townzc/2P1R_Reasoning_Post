# C1 NLL and B/C2 saved-verdict leaf functions — prepared, not run

These new functions have no cloud entry, model loader, scorer invocation or
production IO path. They require a complete shared-path CR/A1/A2-lite with input,
base-weight, budget/window and once-only journal binding before real use. No
independent code-only blocking request is added by publishing this draft.

C1 uses the original base Qwen2.5-1.5B revision8faed761, exact original encoded
input_ids/labels, prompt mask and EOS151643. T1.5 K1 is inherited P009 S1; T7/T72
are P010 student_inputs_r2. All six seed17 n400/n3200 config digests and exact
nesting are checked. Literal identical token/mask pairs can share one forward
while each answer retains group membership/fallback. Causal position j uses
logits j-1; FP32 cross-entropy, no optimizer/LoRA/generation/tokenizer. The real
base manifest and runtime dtype still need binding. Each saved answer counts
once, not multiplied by training exposure. Per-token vectors, token-weighted
NLL/perplexity, per-answer linear quantiles and fallback subsets are retained.
Missing/nonfinite vectors block aggregation; no tests or bootstrap are added.

B uses P010 native prompt IDs and seed function; only T changes to1.0 (optional
.6). Exact400x16 attempts are required. New-temperature K1 selects first usable
within4 else original first attempt, rather than substituting the oldT.8 S1
answer. K4/K8 unique correct nesting conflicts are exposed and require a new
actual disposition, never inherit P010's cancelled-cell permission.

C2 traverses the unchanged E1d order, consumes confirmed oldT72 results, requests
only missing T15 attempts, and never passes an unknown earlier parent. Known
T72 exhausted parents are deterministically ineligible without generating new
T15 outputs for them. First400 common usable parents preserve allowed S1 overlap.
The future IO path must verify original raw/verdict/model/prompt/sampling source
identity before reuse; these functions do not imply that those checks ran.

13 new synthetic/tinyCPU checks passed once (11 then2 newly added input checks).
No real original encoded corpus was processed by these draft functions; no real
model, old scorer or old successful fixture was run. No claim of full runtime
admission, actual C1 values or actual B/C2 selections is made.
