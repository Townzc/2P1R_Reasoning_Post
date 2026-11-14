# A6-2 Tinker LoRA9B paired M512 result

| Arm | MATH5000 | Caps | Loops | Supervised training tokens |
|---|---:|---:|---:|---:|
| Short |3610/5000 =72.20% |4.00% |113 |302,694 |
| Long |4557/5000 =91.14% |6.76% |4 |766,734 |

Long minus short:18.94pp. Both arms use the same ordered512 questions, two epochs, batch8,128updates andseed17. The short solutions are frozenOMI-2P rows; the long solutions are qualifying9B generations. Both solution source/content and length differ. Full token distributions and all three selection checks are in `../a6_2_9b_m512_v1/`. Raw outputs and training evidence are in the two per-arm result directories. This is exploratory and excluded fromH0–H3; independent numeric audit is pending. Prediction18f64e2d preceded all scoring.
