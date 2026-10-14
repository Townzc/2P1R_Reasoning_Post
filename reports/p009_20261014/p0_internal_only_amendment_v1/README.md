# P009 owner amendment: vLLM internal comparisons only

The owner directly resolved the observed base low-gap/high-discordance case after
seeing the complete P0 results. Base and the existing correct-reference endpoint
are designated **internal-only**, subject to actual full P0 A2 and the exact
amendment review. This is a **post-result scope amendment**, not a retrospective
preregistered pass, a change to raw scores, or evidence that engines are equivalent.

| Endpoint | vLLM /1319 | Historical HF /1319 | Discordance | Original frozen decision | Owner-authorized disposition |
|---|---:|---:|---:|---|---|
| Base | 650 | 638 | 126/1319 = 9.552691% | blocked_unspecified_discordance_case | internal-only |
| Correct reference | 950 | 969 | 77/1319 = 5.837756% | pass_internal_only | internal-only |

The original [complete results](../p0_entry_repair_complete_v1/README.md) and
[actual gate projection](../p0_entry_repair_actual_gate_v1/README.md) at
26d7cff6fe2b305542c70a3de1713d42ee87f015 remain immutable. The included
ORIGINAL_P0_RESULTS.json is copied byte-for-byte, including its historical
pending-review label and blocked decision. No raw decoding or scoring is repeated.

All P009 generation/evaluation uses the existing reviewed common high-throughput
vLLM configuration. Both sides of every scientific contrast, G0 and G1 input must
come from that engine and their matching endpoint definitions. HF638/969 remain
historical diagnostic values only; they cannot serve as treatment-effect inputs.
For the same Qwen/GSM zero-shot endpoint, reuse the existing vLLM650 output after
A2. The existing correct-reference checkpoint's vLLM result is950. Its original
training dose remains distinct from future P009 students. Neither number is a
new learning-regime result, and this amendment does not infer parity on MATH or
another model. Training/checkpoint libraries are unchanged.

Future admission packets must bind this exact amendment, the real actual-P0 A2
report, the real amendment report, and the common engine source/observed settings.
No P0 source, frozen gate function, existing plan, raw output or result is edited.
No P0 repetition, new calibration, generation or training is authorized here;
the amendment adds **$0**. The existing$110 allocation and project$450/protected$50
remain. All G0/G1, negative-control, futility, data/dose and runtime/budget gates
still apply. Automatic progression requires those gates and real scoped reviews.

Both reviews are pending when this packet is created. A2 integrity acceptance
must not be described as cross-engine comparability or as automatic Stage1 entry.
Original failed calls, excluded eager128, inherited256 with no parent ack and
all costs remain recorded. The owner has already approved the scope change;
no repeated routine permission is required. Reviewers should assess the exact
scope and binding rather than request another copy of the same owner approval.
