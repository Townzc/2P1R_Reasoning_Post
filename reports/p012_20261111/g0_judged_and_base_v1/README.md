# Original G0 judge and standard-base results

The four original MATH queues were judged together in one H200 load, 742 decisions, zero unparsed responses. Final Li MATH-500 accuracies: Qwen Instruct 48.0%, UWNSL short 51.8%, UWNSL long 38.2%, Llama Instruct 16.2%. The short checkpoint passes the 2 pp paper-comparison threshold (51.8 versus 52.3); its previously audited GSM8K result is 949/1,319 (71.95%) versus 71.7.

Standard Qwen base results use the fixed plain four-shot harness prompts, greedy, 2,048 output / 8,192 context, and one full-test batch. MATH: 1,409/5,000 (28.18%); fixed MATH-500 subset: 143/500 (28.6%). GSM8K: flexible-extract 815/1,319 (61.79%); strict-match 805/1,319 (61.03%). These descriptive protocols are not the main-grid Delta_SFT baseline and do not receive an unmatched official-score gate.

B1 stop records: Qwen full MATH capped 547/5,000 (10.94%); preserve its completed output without further generation on that path. Both Llama base 20-question task probes capped 6/20 (30%); neither full endpoint started. Qwen GSM8K full capped 10/1,319 (0.76%). Probe accuracy was not computed.

The owner-approved public Llama alternative decision is in `../review_54f697e6/`: 1B short repository unavailable; the sole permitted 3B alternative has weights but its prospective cost exceeded $0.8, so it was not run. R2 remains an independent reproduction.

Archives contain original saved outputs and grouped labels; hashes are in `FILES.json`. The original eight endpoint initial labels passed Claude's full independent audit. New judge decisions and standard-base labels await the designated independent review. No completed model call was repeated for this packet.
