# Completed exploratory evaluations (non-preregistered)

All three endpoints contain the same 1,319 frozen questions. Independent local raw/dose/source oracles passed; actual-result external review is pending. Original failed parents and all496 saved outputs, including48 unacknowledged parent rows, are retained. No original output was generated again; no student retraining occurred.

|Evaluation|Correct / 1,319|Accuracy|Length caps|
|---|---:|---:|---:|
|base_4shot|823|62.40%|9|
|instruct_0shot|904|68.54%|54|
|wrong_teacher_t1|934|70.81%|43|

Existing frozen references: base0-shot638/1319 (48.37%); correct-answer breadthT1 student969/1319 (73.46%); correct-answer depthT1 student965/1319 (73.16%). These are reused observed references, not newly evaluated models.

- base_4shot: descriptive difference from969reference = -11.07percentagepoints.
- instruct_0shot: descriptive difference from969reference = -4.93percentagepoints.
- wrong_teacher_t1: descriptive difference from969reference = -2.65percentagepoints.

The wrong-teacher student inherits the original256steps/524,287targets/seed17/LoRA/frozenLR checkpoint; all new child training updates are zero. The natural-wrong set contains429answers from101parents, not429independentquestions. Parent coverage, answer length, exposure and label ambiguity differ from the correct-answer arms; scores do not identify a causal effect of answer correctness. Reference969 is the requested breadth control;965depth is descriptive context.

Base4-shot exemplars were fixed from reserved dev only. Four-shot prompting changes content/context as well as format. General Qwen2.5-1.5B-Instruct uses its own chat template and the disclosed Math-style system prompt; it is a reference, not a proven capability ceiling or a reproduction of official leaderboard protocol.

Greedy512/context2048/batch16 and marked_answer_v1 remain frozen. Length-capped outputs count incorrect. The test has been seen previously, so these are exploratory outcomes, not fresh confirmatory evidence. No new bootstrap, statistical selection or equivalence claim is made here. Reviewer prior prefix-only analyses are not substituted for these full endpoints. The reviewer viewed and scored the preserved prefixes after continuation authorization but before suffix completion; this earlier result exposure is disclosed, and it did not change the frozen roster, inputs, arms, training dose or stopping rules.

Spending: original failures/setup/build/download/storage plus new suffix calls belong to the same experimental budget. LATEST_BILLING is delayed metering, not invoice/final cost/balance. Original historical reservations remain in the ledger.

The original P008 registered results and21PDT material freeze remain unchanged; these exploratory results are a separate dated addendum.
