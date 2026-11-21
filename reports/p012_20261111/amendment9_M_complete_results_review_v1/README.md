# A9 M04–M09 and complete M analysis: independent review requested

Six new endpoints,7,914 original GSM8K greedy outputs. All sources remain unchanged from the frozen A9 source manifest. Training and evaluation used the registered model,seed,data,dose and workspace. R-2 checks verify Num examples and global_step. Per-endpoint archives retain all outputs,labels,manifests and termination metrics.

| Endpoint | Seed | Correct / questions | Accuracy | Truncated | Loops |
|---|---:|---:|---:|---:|---:|
| M04 | 17 | 921/1319 | 69.825625% | 7 | 6 |
| M05 | 29 | 920/1319 | 69.749810% | 13 | 12 |
| M06 | 29 | 359/1319 | 27.217589% | 11 | 8 |
| M07 | 29 | 647/1319 | 49.052312% | 17 | 16 |
| M08 | 29 | 909/1319 | 68.915845% | 15 | 14 |
| M09 | 29 | 915/1319 | 69.370735% | 15 | 13 |

The accepted adapter ran the four complete M units once,using32 bound endpoints and immutable prior R outputs. INPUT_MANIFEST binds476 public files/archive members. Bootstrap core,predictions and previous result files are unchanged.

| Setting | P mean% | S2 mean% | K4 mean% | K8 mean% | S2 − P,pp [95%CI] | Noticeable |
|---|---:|---:|---:|---:|---|---|
| llama_base_gsm8k | 31.1600 | 29.7953 | 27.2176 | 25.1706 | -1.3647 [-3.2221,+0.5307] | False |
| llama_instruct_gsm8k | 51.6679 | 50.7202 | 49.8863 | 45.1099 | -0.9477 [-2.9568,+1.0614] | False |
| qwen_instruct_gsm8k | 70.4701 | 70.6596 | 68.3093 | 66.9067 | +0.1895 [-1.5542,+1.8954] | False |
| qwen_base_gsm8k | 69.7119 | 69.7877 | 68.2714 | 65.6937 | +0.0758 [-1.8196,+1.9712] | False |

Frozen prediction decisions:
- M-1: True
- M-2: True
- M-3: True
- M-4: True

Please independently rescore M04–M09 and reproduce the four M units,including paired intervals,draw hashes and M-1 through M-4. M01–M03 already passed67f8eed9; earlier main-grid/A8 endpoints and all R units need no repeat scoring. No predictor refit or new experiment. No noticeable difference does not establish equivalence; question-bootstrap intervals condition on the two observed training seeds. All results exploratory,outsideH0–H3. Weights retained pending review.
