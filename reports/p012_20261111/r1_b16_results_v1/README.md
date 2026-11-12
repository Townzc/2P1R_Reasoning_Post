# R1 reproduction: PASS

Qwen2.5-1.5B-Instruct, public UWNSL short-chain data, seed 42, two epochs, global batch 16 (per-device 2 × accumulation 8), 666 optimizer updates. Accepted T2 recipe; detached launch; original failed and superseded runs remain preserved.

| Benchmark | Measured | Paper | Difference | Gate |
|---|---:|---:|---:|---|
| MATH-500, exact OR math-verify | 256 / 500 = **51.20%** | 52.3% | −1.10 pp | PASS |
| GSM8K, Li flexible extraction | 958 / 1,319 = **72.63%** | 71.7% | +0.93 pp | PASS |

MATH exact matching alone: 241 / 500 = 48.20%; math-verify adds 15 correct. The gate uses the union, as fixed by T3. No judge model was loaded. Output cap rates: MATH 4.00%, GSM8K 0.076%; decoding remains Li's 16,384 output / 32,768 context protocol.

The training function took 998.9475 seconds; sampled peak GPU memory was 62,974 MiB. All final checkpoint files were hash-verified before inference. `original_r1_artifacts.zip` contains training metadata/logs, complete original generated tokens/text, and labels for both endpoints. `RESULT_AND_GATE.json` records the recipe and numerical comparison.

The Qwen accuracy gate is now satisfied. The remaining main grid stays stopped under the separate $30 cost gate documented in `../l_cost_probe_v1/`; R2 continues within G0-T. C7's requested review packet is `cb9a63ed`.
