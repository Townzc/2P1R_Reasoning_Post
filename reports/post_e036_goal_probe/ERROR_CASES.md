# Diagnostic error inventory

Every failed generated answer remains in its measured denominator. This inventory does not select examples for a new run.

| Evaluation | Failure | Count |
|---|---|---:|
| C-S_F_greedy | wrong_answer_or_resources | 46 |
| C-S_H_greedy | parse | 14 |
| C-S_H_greedy | template_violation | 2 |
| C-S_H_greedy | wrong_answer_or_resources | 22 |
| C-S_C_greedy | wrong_answer_or_resources | 5 |
| C-S_F_sampled | parse | 4 |
| C-S_F_sampled | stop_length_cap | 2 |
| C-S_F_sampled | wrong_answer_or_resources | 181 |
| C-S_H_sampled | parse | 67 |
| C-S_H_sampled | stop_length_cap | 1 |
| C-S_H_sampled | template_violation | 12 |
| C-S_H_sampled | wrong_answer_or_resources | 79 |
| C-P_F_greedy | parse | 1 |
| C-P_F_greedy | wrong_answer_or_resources | 44 |
| C-P_H_greedy | parse | 13 |
| C-P_H_greedy | stop_length_cap | 1 |
| C-P_H_greedy | template_violation | 5 |
| C-P_H_greedy | wrong_answer_or_resources | 19 |
| C-P_C_greedy | wrong_answer_or_resources | 3 |
| C-P_F_sampled | parse | 6 |
| C-P_F_sampled | wrong_answer_or_resources | 178 |
| C-P_H_sampled | parse | 60 |
| C-P_H_sampled | template_violation | 21 |
| C-P_H_sampled | wrong_answer_or_resources | 70 |
| B-S_F_greedy | parse | 1 |
| B-S_F_greedy | wrong_answer_or_resources | 46 |
| B-S_H_greedy | parse | 12 |
| B-S_H_greedy | stop_length_cap | 1 |
| B-S_H_greedy | template_violation | 4 |
| B-S_H_greedy | wrong_answer_or_resources | 21 |
| B-S_C_greedy | wrong_answer_or_resources | 4 |
| B-S_F_sampled | parse | 2 |
| B-S_F_sampled | stop_length_cap | 1 |
| B-S_F_sampled | wrong_answer_or_resources | 183 |
| B-S_H_sampled | parse | 63 |
| B-S_H_sampled | template_violation | 15 |
| B-S_H_sampled | wrong_answer_or_resources | 71 |
| B-P_F_greedy | parse | 2 |
| B-P_F_greedy | wrong_answer_or_resources | 43 |
| B-P_H_greedy | parse | 10 |
| B-P_H_greedy | template_violation | 6 |
| B-P_H_greedy | wrong_answer_or_resources | 21 |
| B-P_C_greedy | wrong_answer_or_resources | 1 |
| B-P_F_sampled | parse | 6 |
| B-P_F_sampled | wrong_answer_or_resources | 178 |
| B-P_H_sampled | parse | 60 |
| B-P_H_sampled | template_violation | 25 |
| B-P_H_sampled | wrong_answer_or_resources | 65 |

Full per-output parsed/resource/target/template and local-arithmetic fields are in `SCORED_OUTPUTS.jsonl`; NA is not a verified arithmetic error.
