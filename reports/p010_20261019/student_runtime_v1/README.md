# P010 C4/C5 exact A2 candidate — no student calls yet

The actual input configs cover only T1.5 n400 K4 and K8. Original selected rows,
encoded answers and plans are copied byte-for-byte from A1 candidate8303d26c.
No selection, schedule, tokenizer, old scoring or old model was rerun.

The entire `train_and_merge` function is source/AST-identical to the P009 core.
The surrounding recipe check permits multiple distinct answer paths per question,
but retains positive q/q+1 exposure, exact1,024 updates/2,097,148 targets, seed17,
original LR, LoRA, target normalization, no packing/truncation and final-state-only
FP32 merge/BF16 save. The training subprocess must exit successfully before vLLM.

One worker then generates all500 original MATH prompts for greedy and four sampled
endpoints (temperature.6/top-p.95/seeds0–3/max1024), saving all2,500 raw outputs and
stop metadata before any CPU scoring. Ten batches total. Sampling never selects
the checkpoint. Frozen CPU scoring and independent A3 remain necessary afterward.

The initial timing scenario retains all1,496 original training intervals from23
hosts and32 endpoint intervals, including historical failure proxies. It forecasts
4,290.960235 seconds / $6.091168 against4500worker/4560platform/600startup and a
$6.55 T reservation. Greedy-to-sampling transfer and the600-second/20% allowances
are uncalibrated; they are not a future host or preemption guarantee. Every actual
batch/block updates the retained maximum before subsequent work. No paid bootstrap
exception, automatic retry or category transfer.

Six new checks passed: five on the first run, plus the actual-worker mock after a
fixture cloud-path mapping correction. The original failure is preserved. The mock
checks allfive endpoints,10generate calls,2500rows and no mutation on replay refusal;
it is not a GPU execution. The Modal definition imported locally without deployment.

Actual A1 data and exact `p010-C4-A2` full report bindings are required before any
new input upload/dispatch. This candidate does not authorize existing T1.5 seed17
K1 retraining, an extra scientific cell, or Tier3 before actualA4. The frozen grid
lists future cells for validation; no input/config or admission is provided for them.

Future one-time sequence, only after the real reports are read:

1. Save actual data A1 and source A2 decisions/report SHA/exact packet bindings.
2. `scripts/p010_student_io.py --root .local/p010_20261019/r1 --spec reports/p010_20261019/student_runtime_v1/SPEC.json`
3. For each admitted cell, call `experiments.p010.modal_students::main` once with
   canonical receipt `.local/p010_20261019/r1/student_runs/RUN`, actual report files
   and fresh T-budget JSON. The entry checks all original attempted E4/student
   reservation records under a local dispatch lock, then a cloud once-only claim.
4. Original RESULT + STOPPED0, then one `p010_transfer.py collect`; local full-state
   and raw/dose oracle and frozen scoring before independentA3. No whole-tool retry.

Original runtime inputs are in `actual_inputs.tar.gz`; source byte hashes are in
SPEC and SOURCE_BINDING. Original files stay immutable. This is an execution/audit
record, not prose for the course report.
