# Tinker LoRA track: MATH pretraining measurements

| Model | 4-shot MATH-500 | 0-shot MATH-500 | Teacher NLL/token | Teacher NLL/character |
|---|---:|---:|---:|---:|
| 4b | 88.40% | 81.80% | 0.647223 | 0.258334 |
| 9b | 91.80% | 91.20% | 0.625836 | 0.249797 |
| 9b_base | 71.40% | Not scheduled | 0.452764 | 0.180717 |

All 11 original endpoints are complete. Frozen C7 conversations, renderer parity, full input hashes and token usage are retained. Baselines use MATH-500; teacher NLL uses the frozen 1,000 solutions.

The original pass@8 outputs and their observed scores are preserved in the ZIPs. Their independent-draw interpretation is invalid: 9B-Base has251/500 questions with all8 token sequences identical and crossed review T4. The approved first8-question diagnostic is complete: original distinct-output counts were1/3/1/4/3/1/1/2, whereas all8 separately seeded single-sample calls differed on everyquestion. The diagnostic scored noanswers and replaced nooutputs. The repairedpass8 path is prepared for review.

4B and9B did not cross the majority-identical threshold; their L/P/R training proceeds. 9B-Base training remains held pending the diagnostic decision. These results are separate from the Modal full-finetuning grid.
