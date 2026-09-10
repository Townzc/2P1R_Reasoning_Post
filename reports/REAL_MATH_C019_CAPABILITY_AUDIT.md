# C019: saved outputs expose a capability-preservation problem

2026-09-10 UTC. This completed CPU audit changes the next experiment's priority:
check retained capability before training scale. It used no server or new model
call. All 32 original saved token streams, labels and strict scores revalidate.
Published audit source: `a093e742340f811eeb158c849a687c8c8cf00c69`.

| Same 16 observed development parents | Original base | E013 tuned |
|---|---:|---:|
| Original frozen strict correctness | 0/16 | 0/16 |
| Post-hoc marked numeric answer correct | 12/16 | 0/16 |
| Above, with actual EOS and no truncation | 11/16 | 0/16 |
| Above, also no new-problem continuation | 10/16 | 0/16 |
| Parsed by the marked-answer diagnostic | 14/16 | 11/16 |
| Truncated output | 2/16 | 5/16 |

All ten clean base successes are lost, with no gains. For example, on the pizza
question `gsm8k/train/06901`, the base answers two friends using division and
subtracting Ron; E013 instead multiplies 12 by 4 and boxes 48. The book question
`gsm8k/train/00722` has a correct base `#### 210` followed by another answer
statement. The historical extractor consumed that entire tail and failed to
parse it; E013 boxes the wrong value 300. These observations warrant checking
functional damage from small-data tuning. They do not identify its causal
mechanism or establish that the separate E015 endpoint has the same damage.

This extractor was designed **after inspecting these outputs**. These numbers
are a post-hoc diagnostic, not replacements for E013's frozen scores, a new
benchmark result, or an unbiased accuracy estimate. The denominator stays 16.
The old base still has a narrative-only correct calculation excluded by the
conservative marked-answer rule, while a correct endpoint can coexist with
faulty reasoning. We do not claim proof validity for any count.

The [paired records](real_math_c019_saved_capability_r1/paired_answers.jsonl)
retain each extraction, ambiguity and continuation boundary. The
[summary](real_math_c019_saved_capability_r1/summary.json) records input hashes.
`marked_answer_v1` never receives a gold label during extraction, never searches
unmarked working for it, and rejects unresolved/conflicting marked answers.
It preserves all raw text/tokens and gives no clean-success credit to truncation
or generated new questions. Six adversarial fixtures cover these edge cases.

## New primary-source reading and its practical consequence

- **ICLR 2025, Unveiling the Secret Recipe: A Guide For Supervised Fine-Tuning
  Small LLMs.** Sections 3.3, 3.5 and 3.8 distinguish generalization from training
  fit: lower learning rates helped their benchmark performance, lower loss was
  not necessarily better, and constant LR could match cosine under their large
  batch setup. Their models are 3B–7B, and Table 4 uses roughly 1.2M–2.7M sample
  presentations. This motivates checking retained capability and a later bounded
  lower-LR calibration; it does not prescribe their batch sizes for our 32-row,
  1.5B setting or attribute E015's success solely to terminal decay.
  [Paper, Sections 3.3/3.5/3.8](https://proceedings.iclr.cc/paper_files/paper/2025/file/b6e2c96bc4702f761d7d108d6e31930f-Paper-Conference.pdf).
- **ACL 2025 main, HFT: Half Fine-Tuning for Large Language Models.** Section 3
  freezes a selected portion of parameters to preserve earlier capabilities.
  Their Appendix A.3.3 uses two SFT epochs, a decreasing 2e-5 LR and eight A100
  80GB GPUs. This gives a distinct conditional alternative to full tuning, not
  evidence that it fixes our pipeline or that a large replication is affordable.
  If reviewed later, use one common adaptation method in every allocation arm;
  changing it only for one arm would confound that comparison.
  [Paper, Section 3 and Appendix A.3.3](https://aclanthology.org/2025.acl-long.626.pdf).
- **Evaluation implementation cross-check.** The EleutherAI GSM8K task separately
  reports strict and flexible extraction, and stops on new `Question:` text.
  This supports documenting extraction/continuation choices separately from
  mathematical capability. Our custom zero-shot Problem/Solution protocol is
  different from its five-shot task; these scores are not harness scores. We
  avoid adopting unrestricted last-number extraction as the primary endpoint.
  [Official task configuration, accessed 2026-09-10](https://github.com/EleutherAI/lm-evaluation-harness/blob/main/lm_eval/tasks/gsm8k/gsm8k.yaml).

The earlier eleven-paper review remains relevant for the later allocation,
selection and curriculum branches. These two additional papers change the
immediate question rather than adding a model/optimizer grid.

## Next experiment

[E016](../docs/experiments/E016_capability_preservation.md) fixes the next 64
C017 development parents, ranks 17–80, outside training and the 16 observed
parents. Compare the pinned original base and E015 weights with identical
original prompts and greedy decoding. Freeze the new scoring and operational
floor/retention thresholds before generating any answer. This is 128 inference
prompts and zero updates; no fresh checkpoint or teacher is needed.

If base capability survives but E015 fails the screen, do not copy the 32-parent
memorization recipe directly into the scientific study. Review one broader,
lower-dose/lower-LR SFT calibration from a fresh base, with training-policy
selection bias disclosed. A partial-freezing or model-boundary change remains a
separate alternative. If the screen passes, price and review the complete
three-arm minimum; 64 parents still cannot prove noninferiority or a small
allocation advantage. Remaining development reserve is 432, and official test
evaluation remains untouched.
