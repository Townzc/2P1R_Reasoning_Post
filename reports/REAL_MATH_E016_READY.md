# E016 ready for one bounded capability diagnostic

2026-09-10 UTC. Offline preparation is complete. The next required resource is
the existing A800 for one inference-only base/E015 comparison. No server was
contacted or started during this work; no new model call or reservation occurred.

[C019](REAL_MATH_C019_CAPABILITY_AUDIT.md) reverified the original 32 development
streams and exposed E013 capability loss that strict 0/16 scoring obscured.
Its new scores are post-hoc diagnostics and do not replace historical results.
E015 development capability remains unknown. Two additional ICLR/ACL papers
motivate separating generalization from memorization and keeping lower update
strength / partial freezing as conditional alternatives.

Implementation **d27c17c7b644199ddbdac045ae357cf6b60d6061** and frozen input release
**32240fd8be020a0da9b6871ea532765d0991b91a** are published. Input-release SHA256:
`c95f7c6d48c5aac11b330bab4989d4efe8a231ec1e4c18e3f8b8bbb21a9204ac`.
All prior E013 source and prediction hashes remain unchanged.

The next 64 C017 GSM8K development parents, ranks 17–80, have zero group overlap
with training or the old 16 observed development parents. All prompt/reference
bytes and 64 prompt token streams were independently reconstructed from pinned
source in the main and clean checkout; verification reports are byte-identical.
Maximum prompt length is 146 tokens, leaving full room for 768 generated tokens
within context 1024. Per endpoint, unpadded/padded prompt counts are 4058/6472.
The other 432 development parents stay reserved; no official test text was
opened anew, and none was evaluated. [CPU evidence](real_math_e016_inputs_r1/cpu_evidence.json).

The focused suite has **40 passes and two expected local skips**; both GNU-timeout
integrations must pass on Linux before launch. Default inspection, release
dependency hashes, group/hash/token checks and all 19 ledger receipts pass.
The Git bundle imported successfully into a clean checkout starting at the
server's last executed source e508321. These checks establish CPU/source/input
readiness, not successful CUDA execution or a capability outcome.
[Independent reconstruction](real_math_e016_verification_r1/independent_inputs.json),
[tests](real_math_e016_verification_r1/focused_tests.log),
[release verification](real_math_e016_verification_r1/release_verification.json).

Run only `gsm8k_capability_e016_r1`: original pinned base then exact E015 weights,
64 prompts each, same original serialization and greedy batch8/768-token cap.
No training, teacher, model replacement or new checkpoint. Primary screening is
correct marked numeric answer with actual EOS, no truncation and no generated
new-problem continuation. Prospective operational gates and all secondary
denominators are in the [registration](../docs/experiments/E016_capability_preservation.md).
No scientific grid or additional process allowance follows automatically.

The current ledger remains **6686/7200 used, 514 left, 19 receipts, no reservation**.
Reserve at most 470+15=485 seconds. Plan **15 minutes/CNY2 target; 20 minutes/
CNY2.67 whole-GPU-rental ceiling**, including setup, compact export and shutdown.
This is a planning allowance, not a measured duration or invoice. Require 785
seconds remaining at admission. Set the provider shutdown backstop before the
job; stop on blocked preflight; export compact results/current ledger and obtain
provider-confirmed shutdown. Do analysis/publication locally afterward.

**E015 independent weights backup remains incomplete.** The 12 complete files
are on the stopped instance, and E016 only reads them. Keep that instance; do
not release/delete it. A separate bounded no-card recovery plan targets at most
two hours/about CNY0.20, with an actual throughput admission test and no retry.
No full-weight transfer is included in the GPU window.
[Recovery plan](../docs/E015_RECOVERY_PLAN.md).
