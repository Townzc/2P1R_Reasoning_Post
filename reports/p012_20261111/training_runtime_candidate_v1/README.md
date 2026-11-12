# Training environment and actual template encoder check

CPU-only candidate for F4. Imports the actual pinned LLaMA-Factory package; exports its training formatter directly and compares 0-shot and 4-shot prompt tokens for all four main tokenizers. Native Instruct templates are not accepted as training-template exports. No model generation or training is invoked.

The official flash-attn wheel matches CUDA 12 / Torch 2.5 / CPython 3.11 / cxx11abiFALSE; the downloaded bytes are fixed by SHA256. The training dependency lock remains unchanged. Runtime installation and actual encoder checks are pending at this source milestone. This candidate joins F4/F5 and the launcher in the one review before C8.
