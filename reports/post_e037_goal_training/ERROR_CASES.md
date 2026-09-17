# Strict-score error inventory

All invalid and incomplete generations remain in denominators. H categories are mutually exclusive with incomplete stops assigned before parse errors. No output is repaired or rescored under a relaxed rule.

| Evaluation | Error category | Count |
|---|---|---:|
| E031_F_greedy | parse | 82 |
| E031_F_greedy | wrong_answer_or_resources | 14 |
| E031_H_greedy | parse_other_or_missing_answer | 31 |
| E031_H_greedy | parse_unfilled_question_mark | 2 |
| E031_H_greedy | strict_correct | 4 |
| E031_H_greedy | template_fixed_operator_changed | 4 |
| E031_H_greedy | template_followed_wrong_hole_operator | 5 |
| E031_H_greedy | template_input_resources_changed | 50 |
| E031_C_greedy | none | 89 |
| E031_C_greedy | wrong_answer_or_resources | 7 |
| E031_F_sampled | none | 1 |
| E031_F_sampled | parse | 254 |
| E031_F_sampled | wrong_answer_or_resources | 129 |
| E031_H_sampled | parse_other_or_missing_answer | 142 |
| E031_H_sampled | parse_unfilled_question_mark | 12 |
| E031_H_sampled | strict_correct | 10 |
| E031_H_sampled | template_fixed_operator_changed | 3 |
| E031_H_sampled | template_followed_wrong_hole_operator | 16 |
| E031_H_sampled | template_input_resources_changed | 195 |
| E031_H_sampled | template_tree_or_leaf_order_changed | 6 |
| G-single_F_greedy | none | 3 |
| G-single_F_greedy | parse | 1 |
| G-single_F_greedy | wrong_answer_or_resources | 92 |
| G-single_H_greedy | strict_correct | 40 |
| G-single_H_greedy | template_followed_wrong_hole_operator | 55 |
| G-single_H_greedy | template_input_resources_changed | 1 |
| G-single_C_greedy | none | 92 |
| G-single_C_greedy | wrong_answer_or_resources | 4 |
| G-single_F_sampled | none | 14 |
| G-single_F_sampled | parse | 10 |
| G-single_F_sampled | stop_length_cap | 1 |
| G-single_F_sampled | wrong_answer_or_resources | 359 |
| G-single_H_sampled | strict_correct | 149 |
| G-single_H_sampled | template_followed_wrong_hole_operator | 230 |
| G-single_H_sampled | template_input_resources_changed | 5 |
| G-paired_F_greedy | none | 3 |
| G-paired_F_greedy | wrong_answer_or_resources | 93 |
| G-paired_H_greedy | strict_correct | 45 |
| G-paired_H_greedy | template_followed_wrong_hole_operator | 51 |
| G-paired_C_greedy | none | 94 |
| G-paired_C_greedy | wrong_answer_or_resources | 2 |
| G-paired_F_sampled | none | 13 |
| G-paired_F_sampled | parse | 11 |
| G-paired_F_sampled | stop_length_cap | 1 |
| G-paired_F_sampled | wrong_answer_or_resources | 359 |
| G-paired_H_sampled | strict_correct | 158 |
| G-paired_H_sampled | template_followed_wrong_hole_operator | 221 |
| G-paired_H_sampled | template_input_resources_changed | 5 |
| G-single_midpoint_H_greedy | strict_correct | 9 |
| G-single_midpoint_H_greedy | template_followed_wrong_hole_operator | 15 |
| G-single_train_F_greedy | none | 2 |
| G-single_train_F_greedy | wrong_answer_or_resources | 30 |
| G-single_train_H_greedy | strict_correct | 17 |
| G-single_train_H_greedy | template_followed_wrong_hole_operator | 15 |
| G-paired_midpoint_H_greedy | strict_correct | 10 |
| G-paired_midpoint_H_greedy | template_followed_wrong_hole_operator | 14 |
| G-paired_train_F_greedy | none | 1 |
| G-paired_train_F_greedy | parse | 1 |
| G-paired_train_F_greedy | wrong_answer_or_resources | 30 |
| G-paired_train_H_greedy | strict_correct | 16 |
| G-paired_train_H_greedy | template_followed_wrong_hole_operator | 16 |

C strict scores evaluate the original expression. A wrong C answer with consistent local equations may still change numbers, operand order or grouping. Those descriptive program changes require trace-level review; local consistency is not expression fidelity. Missing arithmetic evidence remains NA. Per-output text, original strict scores and resource/target/local-arithmetic fields are retained in SCORED_OUTPUTS.jsonl.
