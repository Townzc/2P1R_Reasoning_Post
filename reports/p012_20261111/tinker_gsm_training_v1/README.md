# Original authorized Tinker GSM8K continuation

The original 27 cells use unchanged reviewed training, generation and scoring code on the C6 frozen GSM8K files: three models, seed17 L/P/R/K8/K4 and seed29 L/P/R/K8. Batch8; L128 updates, other cells1024. The three models run in parallel; each model follows L, P, R, K8, K4. NLL completion precedes training.

Admission uses measured GSM8K completion tokens, exact posttraining prompt token counts and a1.5 sampling margin. The complete GSM block reserves USD90.851501, inside105; original T including USD30 storage reserves320.598846/340; all tracks429.008213/485. Completed costs replace reservations before each batch; all remaining reservations stay included. Ledgers are immutable snapshots, with the shared private pointer updated under the budget lock.

4B pretraining pass@8 is complete but held unscored after the diversity guard. It is excluded from statistical summaries until disposition; a56115d6 section3 permits training independently. No pass@8 output is used for training. No new scientific path or configuration is introduced. Every evaluation retains a timestamped prediction binding to8bbf06a7 and all raw evidence. Results are exploratory and excluded from H0–H3.
