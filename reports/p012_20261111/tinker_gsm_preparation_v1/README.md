# T-GSM unchanged-path CPU preparation

All11 pretraining endpoints and27 planned training cells use frozen C6/C7 GSM8K inputs. The preflight verified every row under each fixed model tokenizer and renderer, prompt parity, assistant-only masking, maximum lengths and exact input hashes. No scientific source was changed. Preparation does not admit training.

[Manifest](MANIFEST.json) · [Pretraining checks](PRETRAINING_PREFLIGHT.json) · [Training token counts](TRAINING_COUNTS.json)
