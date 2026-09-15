# E017: task stopping passes the observed-development usability screen

September 15, 2026 UTC (September 14 in Los Angeles). The single registered
`gsm8k_stop_e017_r1` run completed from published source
`73170a459e9fed2c5fdea6a9afb40b4b80837bb2`. All 64 Linux checks passed before
launch, including the two pending watchdog integrations. Independent server
and local raw-token audits agree byte for byte. The provider confirmed normal
shutdown; all 18 compact/auxiliary files and the updated ledger were independently
exported and hash-verified before the shutdown request.

## Registered result

The original Qwen2.5-1.5B base generated answers for the same 64 observed E016
parents, development ranks 17–80. Prompts/order, greedy seed17, batch8, context1024,
cap768, FP32 weights/BF16 autocast/SDPA and TF32-off settings stayed fixed.
The sole change was per-row stopping at true native EOS or a complete recognized
new-question boundary, preserving the trigger and subsequent batch padding.

| Measurement | E017 | Registered requirement |
| --- | ---: | --- |
| Complete audited records | 64/64 | 64/64 |
| Parsed marked answers | 49/64 | At least48 |
| Task-completed correct answers | 39/64 (60.94%) | At least8 |
| Native EOS stops | 47 | Report separately |
| New-question boundary stops | 16 | Report separately |
| Actual length-cap stops | 1 | At most8 |
| Invalid stop records | 0 | Zero |
| False native-EOS records | 0 | Zero |
| Operational usability | **Pass** | All requirements jointly |

Of the 39 task-correct outputs,26 end at true native EOS and13 at a recognized
new-question boundary. The length-capped output is not task-correct. Fourteen
outputs lack a marked answer and one has an unresolved marked answer;49 parsed
is only one above the operational floor. A passing screen does not establish
general reliability or verify intermediate reasoning.

## Comparison with the historical run

Every retained E017 token sequence equals the corresponding prefix of its
E016 base output: **64/64 exact prefix matches, zero mismatches**. The comparison
therefore validates this implementation on the observed streams; it does not
promise deterministic replay on other hardware, settings or inputs.

| Endpoint and contract | Correct count | Length-cap count |
| --- | ---: | ---: |
| E016 base, frozen clean-answer contract | 26/64 | 14 |
| E016 base, separately reported marked numeric answer | 39/64 | 14 |
| C020 saved-prefix proposal, post-hoc | 39/64 | A saved-stream calculation |
| E017 base, registered task-completion contract | 39/64 | 1 |

The old-clean/new-task comparison has26 both-correct,13 new-task-only,
zero old-clean-only and25 both-wrong. These are **different completion contracts**,
not an accuracy gain from training. E016's original scores, both failed screens,
and E015's0/64 development result remain unchanged. No E015 weights were loaded.

## Measured runtime and accounting

| Measurement | E017 |
| --- | ---: |
| Model load | 2.025 seconds |
| Generation | 72.381 seconds |
| Raw-record audit inside worker | 0.116 seconds |
| Worker wall time | 74.523 seconds |
| Guarded-process elapsed / charged | 79.757 /80 seconds |
| Retained generated tokens, including stop triggers | 9,960 |
| Padded batch output tokens | 20,808 |
| Post-stop padding tokens | 10,848 |
| Sum of eight batch maximum lengths | 2,601 |
| Peak allocated / reserved GPU memory | 6,738.53 /7,042.00 MiB |

The historical E016 base generation took145.356 seconds; this E017 run took
49.80% as long. This is one measurement per cloned A800 instance, not a repeated
causal throughput benchmark. Retained lengths alone do not describe batch work.

The80-second charge extends the unchanged20-receipt history to21 complete
receipts: **7,001/7,200 seconds used,199 remaining,zero reservations**. Every
public receipt equals its private ledger entry, and all first20 entries remain
unchanged. Current ledger SHA256:
`48541b40ec441c1c5d5870d7c198c00a5e567ef7bc3804e03ccc1d61a63fda8e`.
No new phase allowance was created.

Owner-notification proxy05:35:16UTC to the recorded provider-off confirmation
by05:42:32UTC spans436 seconds, about7 minutes16 seconds, or **CNY0.97** at
CNY8/hour. Actual provider power-on time and the exact invoice are unavailable;
this observed proxy span is not a billing reconciliation. The planned rental
ceiling was15 minutes/CNY2. A provider shutdown backstop was set before launch
and cancelled after shutdown. The stopped volume was retained, not released.

## Scope and next decision

This is an observed-development stopping calibration, with no SFT, teacher
generation, new checkpoint, new development parent, or official-test access.
The shared exposure history remains80 observed and432 reserved development
parents. The complete E015 weights still lack an independent full backup;
preserve the retained instance and handle recovery separately.

E017 resolves the completion prerequisite for reviewing P006 Stage B. The
proposed E018 is one253-parent/two-epoch LoRA recipe with both learning and
paired-retention gates; it is not implemented or authorized for execution yet.
Its reviewed process/rental proposal remains915 seconds and30 minutes/CNY4.
Any added allowance must start from the actual21-receipt ledger above. If its
paired base again solves39 questions, the90% survival rule requires retaining
at least36 of those exact successes. Do not replace the planned paired baseline
with E017 or treat that conditional count as an E018 result.
[Concrete next-phase review](../docs/tracks/iclr_2027/NEXT_PHASE_REVIEW.md).

## Reproduction and retained evidence

- [Frozen run records](../runs/gsm8k_stop_e017_r1/metrics.json),
  [source manifest](../runs/gsm8k_stop_e017_r1/run_manifest.json), and
  [measured profile](../runs/gsm8k_stop_e017_r1/base_profile.json).
- [Local raw-token audit](real_math_e017_execution_r1/local_record_verification.json),
  [server audit](real_math_e017_execution_r1/server_record_verification.json),
  [64 Linux checks](real_math_e017_execution_r1/linux_tests.log).
- [Descriptive summary](real_math_e017_execution_r1/summary.json),
  [64 prefix comparisons](real_math_e017_execution_r1/paired_stop_comparison.jsonl),
  [21-receipt reconciliation](real_math_e017_execution_r1/ledger_verification.json).
- [Compact transfer verification](real_math_e017_execution_r1/compact_export_verification.json)
  and [provider closeout](real_math_e017_execution_r1/shutdown_closeout.json).

Use the existing CPU environment (Python3.10+), pinned original tokenizer and
the independently retained current/prior ledgers. These commands make no model
call; output paths must be new. The summary directory must contain copies of
the two published record-audit files.

```sh
TOKENIZERS_PARALLELISM=false python -m analyses.e017 audit --tokenizer-dir "$E017_TOKENIZER" --out NEW_AUDIT_JSON
python -m analyses.e017_result_summary --ledger CURRENT_PRIVATE_LEDGER --prior-ledger PRE_E017_PRIVATE_LEDGER --out-dir NEW_SUMMARY_DIRECTORY
```

Do not rerun `launch --execute`: E017 is complete and its run ID, pre-run ledger
hash and allowance state cannot be reused. All104 frozen runtime/input dependency
files remain unchanged by this closeout.
