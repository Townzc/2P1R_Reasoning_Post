# UWNSL short-checkpoint G0-E results

Executed once at `444aed91`, official fixed revision `b42204c7a2d5215e740c07234bfe04e25682eaac`, Li release prompts and scorers.

| Endpoint | Result | Terminator / cap / string stop | Unknown stops |
|---|---|---|---|
| MATH-500 | Normalized exact 244/500 = 48.8%; 231 pending judge | 476 / 24 / 0 | 0 |
| GSM8K test | Flexible extract 949/1319 = 71.95% | 1314 / 5 / 0 | 0 |

GSM8K differs from paper Table 8 (71.7%) by +0.2484 pp, within the accepted 3 pp numeric gate. MATH final Li accuracy is pending the consolidated 32B judge; its exact score is not the final paper-comparable score. Independent 10% raw-output review remains pending.

Raw archives contain full inputs, config, token/text/stop records, hardware, runtime logs and manifests. Score archives contain every label and the pending judge queue. The original prospective forecast is retained. No output was regenerated or selected by accuracy.
