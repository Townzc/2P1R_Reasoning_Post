"""Exercise the complete disk-output path with a deterministic fake vLLM."""
from dataclasses import dataclass
import json
import sys
from types import SimpleNamespace

import pytest

from experiments.p012.evaluation import EvalConfig, run_vllm, sha256_file


def test_raw_tokens_and_stop_causes_survive_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("P012_CODE_COMMIT", "0" * 40)
    monkeypatch.setattr("importlib.metadata.version", lambda _: "fixture")
    @dataclass
    class FakeTokenizer:
        eos_token_id: int = 99
        unk_token_id: int | None = None
        chat_template: str = "frozen synthetic template"
        def encode(self, text, add_special_tokens):
            assert not add_special_tokens
            return [98] if text == "<|im_end|>" else [11, 12]
        def apply_chat_template(self, *args, **kwargs):
            return [11, 12]
    class FakeLLM:
        def __init__(self, **kwargs):
            assert kwargs["generation_config"] == "vllm"
        def get_tokenizer(self):
            return FakeTokenizer()
        def generate(self, prompts, params, use_tqdm):
            assert params["stop_token_ids"] == [98, 99]
            return [SimpleNamespace(outputs=[
                SimpleNamespace(index=0, token_ids=[20, 99], text=r"\boxed{1}",
                                finish_reason="stop", stop_reason=99),
                SimpleNamespace(index=1, token_ids=[20, 21], text="unfinished",
                                finish_reason="length", stop_reason=None)])]
    monkeypatch.setitem(sys.modules, "vllm", SimpleNamespace(LLM=FakeLLM, SamplingParams=lambda **kw: kw))
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(GenerationConfig=SimpleNamespace(
        from_pretrained=lambda *a, **kw: SimpleNamespace(eos_token_id=[98, 99]))))
    source = tmp_path / "inputs.jsonl"
    source.write_text(json.dumps({"id": "a", "problem": "1+0"}) + "\n")
    template_file = tmp_path / "training.jinja"
    template_file.write_text("frozen synthetic template")
    config = EvalConfig("fixture", "fixed", "omi2", "math", "qwen", max_tokens=2,
                        max_model_len=4, n=2, temperature=0.7,
                        chat_template_file=str(template_file))
    out = tmp_path / "raw"
    run_vllm(config, source, out)
    rows = [json.loads(x) for x in (out / "raw.jsonl").read_text().splitlines()]
    assert rows[0]["stopped_on_terminator"] and not rows[0]["length_capped"]
    assert rows[0]["stop_token_id"] == 99
    assert rows[1]["length_capped"] and not rows[1]["stopped_on_terminator"]
    assert rows[0]["prompt_token_ids"] == [11, 12]
    assert rows[0]["token_ids"] == [20, 99]
    assert json.loads((out / "MANIFEST.json").read_text())["chat_template_sha256"] == sha256_file(template_file)
    assert json.loads((out / "GENERATION_COMPLETE.json").read_text())["raw_sha256"] == sha256_file(out / "raw.jsonl")
    with pytest.raises(FileExistsError):
        run_vllm(config, source, out)
