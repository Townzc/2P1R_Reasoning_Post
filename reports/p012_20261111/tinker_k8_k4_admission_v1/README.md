# Tinker LoRA K8 and K4 admission, MATH seed17

All three corrected pretraining pass@8 endpoints passed the accepted diversity check. L/P/R were submitted first for each model; the next submissions are K8 and then K4. Cells remain independent and may run in parallel under approved Amendment4.

The six training requests use the original C6 files, fixed rank32, model-specific frozen learning rate, seed17 and 1024 updates. Their 5000-question greedy forecasts use each model’s completed L token count times1.5. Previous reservations are retained in full. See `ADMISSION.json` for the combined total and hard limit; no recipe or shared code changes.
