# Problems or Solutions? Allocating Data Acquisition Budgets for Reasoning SFT

Draft proposal abstract, 2026-09-10 UTC. Based on
[P004](experiments/P004_cost_aware_sft_allocation_proposal.md) and the
[model/compute audit](../reports/RELATED_WORK_MODEL_COMPUTE_20260910.md).
This describes prospective research, not completed acquisition experiments.

## Abstract

Reasoning supervised fine-tuning (SFT) requires both input problems and output solutions, but their acquisition costs can differ substantially. This project asks how to divide a limited data-acquisition budget between more unique problems and additional solutions to existing problems under fixed SFT supervision and update budgets.

I will conduct controlled experiments with Qwen2.5-1.5B base on GSM8K, comparing problem-first, solution-first, and balanced allocations, with exact repetition as an exposure control. A bounded acquisition pilot will assess reusable multi-solution data and Qwen2.5-Math-1.5B-Instruct as a candidate generator. Each comparison will fix the solution source and student training method, with audits of supervised tokens, optimizer updates, sequence lengths, and runtime.

Cost accounting will include unsuccessful and duplicate generations, filtering, and verification. Measured local costs will be distinguished from hypothetical problem prices and unknown historical costs of public corpora. Targeted analyses will examine problem difficulty, coverage, and solution quality; paraphrases will be treated separately from structural solution diversity. Evaluation will measure held-out pass@1, pass@k under a fixed inference budget, and learning dynamics. Allocation recommendations will be tested on fresh problem draws and allocation settings not used to develop them, with uncertainty reported across problems and training seeds.

Verifiable synthetic tasks will support diagnostic tests of repetition and solution structure. Subject to feasibility, decisive comparisons will be replicated with OLMo-2-0425-1B base. The intended contribution is a reproducible evaluation framework and empirically validated guidance on when to invest in new problems or additional solutions for reasoning SFT.

## Scope and status of this revision

The primary question is the cost-dependent acquisition decision. Exact repeats,
paraphrases and structural paths provide controls or diagnostics; RL is excluded.
The generator and second-family model are candidates, not tested assets. No
claim of superior allocation or real-dollar savings follows from earlier pilots.

Existing evidence remains in the [model-selection report](../reports/MODEL_SELECTION_EVIDENCE_20260910.md):
arithmetic training overfit succeeded, broader generalization was weak, and
E011 failed complete-proof training. P004's acquisition study has not run.
This abstract does not change the frozen E012 source/data or authorize a new
grid. E012 remains paused; no GPU or server action accompanies the text revision.

## Planned deliverables accompanying the abstract

Dates below are from the supplied course plan. Candidate P/K ranges and the
complete acquisition/training/evaluation budget must be profiled before freezing
an executable subset. No full nine-cell sweep is promised by this document.

- **October 20, 2026:** Qwen2.5-1.5B/GSM8K feasibility and a small allocation study;
  two seeds for key comparisons; acquisition-yield/cost and token/update audits;
  preliminary learning curves, held-out pass@1/pass@k and cost/performance curves;
  midpoint report and presentation.
- **December 14, 2026:** three seeds for key comparisons; validate a recommendation
  on fresh problem draws and allocations not used to develop it; selected
  OLMo-2-0425-1B comparisons after feasibility; targeted quality/difficulty checks;
  reproducible code, data manifests, accounting and final report.

The official GSM8K test remains reserved for frozen final evaluation. Failed
acquisition attempts and unfilled per-problem solution targets remain in the
denominators. Public cached outputs without generation logs cannot identify
effective generation price or acceptance yield. See P004 for these design limits.
