#4B M512 freeze and matched cross-teacher arms

All three construction checks passed. All four arms share the identical ordered512 questions:4B short/long and9B matched-short/cross-long. Each student tokenizer checked all actual rows, masks and the2300-token maximum. Each arm has1024 presentations,128 updates and seed17; token counts differ and are reported. The9B arms use prediction46694f51; the original4B arms retain18f64e2d. All are exploratory and use the existing A6-2 USD50 cap. Prepared requests remain unadmitted pending the recorded budget check.

Posthoc construction review **passed** at [6af18b72](https://github.com/Townzc/2P1R_Reasoning_Post/blob/6af18b7263cdafa1c6c34efb89fdea763d74d21e/audit/claude/20261113j/AUDIT_f6785133_5_endpoints_and_4B_M512.md): all856 attempts and all512 selected long answers independently checked. The frozen manifest, training files and evidence archive are unchanged; see AUDIT_STATUS.json.
