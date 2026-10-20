# P010 T1.5 completed output and exact K4/K8 inputs — A1

Request `p010-T15-complete-data-A1-r1`, scope `p010-T15-complete-data-A1`.
The fixed target commit is recorded in INDEX. This is the actual data audit required
by P010 v3 §7, not an additional code-only or per-slot review.

Packets: `teacher_t15_complete_v1` and `t15_data_candidate_v1`.
Original generation used the exact 22-source `teacher_runtime_v2` closure at
`6a04af4eb28e16b43690d1f4fcac935c58abd5fe`. Original app
`ap-uBb1UKh3xULFnefyTJoQ7R` is STOPPED with zero owned containers.

Please independently verify:

1. All 5,940 new raw outputs, input/prompt/attempt identities, native EOS and cap
   handling, saved frozen score journals, acknowledgments and metadata. The
   original tar is byte-identical; failed/truncated outputs are retained. The
   frozen P1 scorer SHA is `d310d7e61b049cdd750f14c65f0ad12551ee45b7eeb0913646a6447a4cbc36fe`.
2. Exactly 460 original P2 output records and original P1 verdicts were reused,
   not generated or scored again. Full original physical raw files are archived;
   `T15_REUSE.json` identifies the exact records. The two projected P1 subsets
   contain unchanged row objects; complete original-file SHA bindings are supplied.
3. Exact S1 question identities/order, P008 within-question normalized text
   deduplication, first-K usable answers, K1 ⊂ K4 ⊂ K8, and all original questions
   retained. K4 has 1,592 answers / 400 questions / 5 underfilled; K8 has 3,146 /
   400 / 14 underfilled. No >10% threshold or nesting conflict was observed.
4. Selected original answer bytes, tokenizer/mask/EOS lengths and whole-answer
   plans: once-each totals 742,953 and 1,457,460; q=2 and 1; exposures 2–3 and 1–2;
   seed17, exactly 1,024 updates / 2,097,148 targets and original LR SHA14ac59d2.
   The source closure includes the actual executed preparation script. No answer
   filtering, truncation, q=0, scientific dose change or baseline retraining.
5. Gross delayed app meter versus conservative reservations, and the explicit
   private-locator/provider-actor projections. T1.5's tagged delayed meter is
   $0.58853757; no claim of final invoice, free failures or current balance.

Please bind both packet MANIFEST SHAs, the selected input archive SHA, source map,
and decisions for raw integrity, saved-score truth, selection and coverage in the
fixed full report. Describe any limits of independent scoring/tool availability.
Actual training additionally needs the C4 exact runtime/A2 binding; this request
does not admit an unprepared training entry. Existing T1.5 K1 results 273/500 and
276/500 remain unchanged references.

These are execution/audit records and must not be pasted into the course report.
