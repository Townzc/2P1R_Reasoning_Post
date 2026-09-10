# Evidence that changes the capability-preservation plan

2026-09-10 UTC. Primary-source methods/setup review, with the server kept off.
This supplements the earlier eleven-paper review and C019. It does not claim
an exhaustive literature search or a successful new method. Source scopes below
are substantially larger or different from this1.5B/253-parent calibration.

| Source and checked location | Relevant evidence | Decision for this project |
|---|---|---|
| [Unveiling the Secret Recipe, ICLR2025, Sections3.3/3.5/3.7](https://proceedings.iclr.cc/paper_files/paper/2025/file/b6e2c96bc4702f761d7d108d6e31930f-Paper-Conference.pdf) | In their Granite7B setup,2e-5 generally outperforms higher tested rates; lower training loss does not track better downstream performance. Constant LR can match cosine in their large-batch comparison. | Keep a lower-LR full-SFT alternative, but stop using near-perfect32-row fit as the optimization target. Do not import a3840-example batch, their training volume or a universal cosine claim. |
| [LoRA Learns Less and Forgets Less, TMLR2024, Sections3/4.1/4.2/5 and AppendixB](https://arxiv.org/html/2405.09673v2) | Llama2-7B experiments cover coding/math instruction tuning and continued pretraining. LoRA can retain more out-of-domain performance while learning less; low rank is not automatically sufficient. The study uses method-specific LR tuning and finds that LoRA need not train faster at fixed batch size. | Make one small LoRA recipe a concrete candidate for retention and affordable checkpoint preservation. Measure learning as well as retention. Rank16 is a budget-conscious hypothesis, not the paper's guaranteed optimum; no rank/LR sweep is authorized. |
| [HFT, ACL2025 main, Algorithm1 and AppendixA.3.3](https://aclanthology.org/2025.acl-long.626.pdf) | The method selects parameter tensors within attention, feed-forward and normalization groups; it is not simply freezing half the transformer layers. Their SFT setup uses2 epochs,2e-5 and8A10080GB GPUs. | Keep HFT as a separately reviewed fallback with an explicit parameter mask. Do not label arbitrary layer freezing a faithful replication, or assume half the tensor count means half the parameter bytes on Qwen GQA. |
| [Self-Synthesized Rehearsal, ACL2024 main, Sections4/5.4 and AppendixD](https://aclanthology.org/2024.acl-long.77.pdf) | SSR generates synthetic inputs, refines outputs and selects rehearsal examples for7B continual-learning settings. Its generalization study also uses instruction-following evaluation with an external judge. | Replay is a distinct fallback if adapter or lower-LR calibration still loses capability. Synthetic generation, quality filtering and extra training tokens must be charged; copying its full teacher/judge pipeline is outside the minimum plan. |
| [EleutherAI GSM8K task configuration](https://github.com/EleutherAI/lm-evaluation-harness/blob/main/lm_eval/tasks/gsm8k/gsm8k.yaml), read2026-09-10; Git blob9266ab1f80af13b228f55f474442eb8db34f8a13 | The task has explicit generation stop strings, five-shot prompting, and separate strict/flexible extraction. | Treat task completion and native EOS as distinct. Our stop-only proposal retains zero-shot Problem/Solution prompts and conservative marked extraction; it is not the harness benchmark and does not adopt unrestricted final-number extraction. |

The LoRA paper is TMLR, not an ICLR/ACL acceptance. The two ACL papers are main
conference publications. The inaccessible OpenReview rendering was not treated
as full text; the author-hosted arXiv version supplied the LoRA methods/setup.
The official GitHub connector verified the harness file's current content and
blob hash after the web API route did not return it. No benchmark was run.

The recommendation is an inference from these sources **and our local failure**:
first validate task-boundary stopping without changing the prompt or arithmetic
extractor; then test one modest LoRA recipe on broader existing data, measuring
learning and paired mathematical retention. Full SFT with lower LR, HFT and
replay stay explicit alternatives with separate costs and stopping rules.

GSM8K before/after performance supports a claim about mathematical capability
under this protocol. It does not by itself establish retention of general
knowledge, language ability or safety. Those broader claims need separately
registered out-of-domain evaluations. No method is established to fix E015,
and numerical drift between older runs still prevents isolated LR attribution.

[C020 CPU evidence](REAL_MATH_C020_COMPLETION_AUDIT.md),
[P006 finite proposal](../docs/experiments/P006_evaluation_and_capability_preservation.md).
