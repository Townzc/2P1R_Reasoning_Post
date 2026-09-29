"""Byte-preserved Qwen math judging with bounded, non-executing worker requests.

No math_eval driver, PythonExecutor, tool round, or generation is imported.
Symbolic equivalence is the original grader's CPU symbolic parsing, isolated in
a replaceable process. Timeouts/infrastructure exceptions remain unresolved.
Use MathScorer for many outputs so Python/SymPy imports are amortized.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import threading
import time
import types

VENDOR = Path(__file__).parent / "vendor" / "qwen_math"
QWEN_COMMIT = "a45202bd16f1ec06f433442dc1152d0074773465"
_MODULES = None
_IMPORT_LOCK = threading.Lock()
_PREFIX = "_public_math_qwen_a45202bd"


def source_identity() -> dict:
    manifest = json.loads((VENDOR / "PROVENANCE.json").read_text())
    if manifest["commit"] != QWEN_COMMIT or manifest["bytes_modified"]:
        raise ValueError("Unexpected vendor provenance")
    for record in manifest["files"]:
        if hashlib.sha256((VENDOR / record["path"]).read_bytes()).hexdigest() != record["sha256"]:
            raise ValueError(f"Vendor source SHA mismatch: {record['path']}")
    return {"qwen_commit": QWEN_COMMIT,
            "vendor_manifest_sha256": hashlib.sha256((VENDOR / "PROVENANCE.json").read_bytes()).hexdigest(),
            "files_sha256": {r["path"]: r["sha256"] for r in manifest["files"]}}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _upstream():
    global _MODULES
    with _IMPORT_LOCK:
        if _MODULES is not None:
            return _MODULES
        source_identity()
        # Upstream uses absolute imports. Temporary aliases leave its bytes intact
        # and avoid permanently shadowing unrelated application modules.
        names = ("latex2sympy2", "examples", "utils")
        previous = {name: sys.modules.get(name) for name in names}
        package = types.ModuleType(_PREFIX)
        package.__path__ = [str(VENDOR)]
        sys.modules[_PREFIX] = package
        latex_package = types.ModuleType(_PREFIX + ".latex")
        latex_package.__path__ = [str(VENDOR / "latex2sympy")]
        sys.modules[latex_package.__name__] = latex_package
        try:
            sys.modules["latex2sympy2"] = _load(_PREFIX + ".latex.latex2sympy2", VENDOR / "latex2sympy/latex2sympy2.py")
            sys.modules["examples"] = _load(_PREFIX + ".examples", VENDOR / "examples.py")
            sys.modules["utils"] = _load(_PREFIX + ".utils", VENDOR / "utils.py")
            parser = _load(_PREFIX + ".parser", VENDOR / "parser.py")
            grader = _load(_PREFIX + ".grader", VENDOR / "grader.py")
            _MODULES = parser, grader
        finally:
            for name, old in previous.items():
                if old is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = old
        return _MODULES


def environment_identity() -> dict:
    import sympy
    versions = {name: importlib.metadata.version(name) for name in
                ("sympy", "antlr4-python3-runtime", "word2number", "regex", "numpy")}
    if sympy.__version__ != "1.12" or versions["antlr4-python3-runtime"] != "4.11.1":
        raise RuntimeError("Official grader requires sympy==1.12 and antlr4-python3-runtime==4.11.1")
    return {"python_version": sys.version.split()[0], "dependencies": versions, **source_identity()}


def _dataset(dataset: str) -> str:
    names = {"math500": "math-oai", "MATH500": "math-oai", "math-500": "math-oai",
             "numina": "math", "dev": "math", "GSM8K": "gsm8k"}
    value = names.get(dataset, dataset)
    if value not in {"math", "math-oai", "gsm8k", "minerva_math"}:
        raise ValueError(f"Unsupported dataset: {dataset}")
    return value


def parse_answer(text: str, dataset: str = "math") -> str | None:
    """Official qwen-boxed run_execute path (including double normalization)."""
    parser, _ = _upstream()
    return parser.run_execute(None, text, "qwen-boxed", _dataset(dataset), execute=False)[0]


def ground_truth_info(row: dict, dataset: str = "math") -> dict:
    """Preserve an official answer even if upstream unit stripping empties it.

    This does not repair the vendor or replace a benchmark item. An empty
    normalized official MATH500 answer is an explicit unresolved-reference
    boundary. Numina dev still requires a parseable, nonempty reference.
    """
    parser, _ = _upstream()
    name = _dataset(dataset)
    if name == "math-oai":
        # MATH-500's published final answer is authoritative; do not infer it from
        # reference prose or accidentally invoke unsupported 'math500'.
        raw_reference = row["answer"]
        if not isinstance(raw_reference, str) or not raw_reference.strip():
            raise ValueError("Missing raw official reference answer")
        record = {"gt": raw_reference, "gt_cot": row.get("solution", "")}
    else:
        record = row
        if "gt" in row and "gt_cot" in row:
            raw_reference = row["gt"]
        else:
            raw_reference = row["answer"].split("####")[-1].strip() if name == "gsm8k" else row["solution"]
    answer = parser.parse_ground_truth(record, name)[1]
    empty = answer is None or not str(answer).strip()
    if empty and name != "math-oai":
        raise ValueError("Empty official reference answer")
    return {"reference": "" if answer is None else str(answer), "raw_reference": raw_reference,
            "normalization_empty": empty,
            "reference_normalization_status": "empty_under_upstream" if empty else "nonempty",
            "reference_status": "unresolved_reference" if empty else "resolved_reference"}


def ground_truth(row: dict, dataset: str = "math") -> str:
    return ground_truth_info(row, dataset)["reference"]


def extraction_route(text: str) -> str:
    """Descriptive only; never substitutes a stricter extraction rule."""
    if not text or text == "error":
        return "empty_or_error"
    if "final answer is $" in text and "$. I hope" in text:
        return "minerva_phrase"
    if "boxed" in text:
        return "last_boxed_substring"
    if "he answer is" in text:
        return "answer_phrase"
    if "final answer is" in text:
        return "final_answer_phrase"
    if "答案是" in text:
        return "chinese_answer_phrase"
    return "last_number_fallback"


def _judge(request: dict) -> dict:
    text, reference = request["text"], request["reference"]
    dataset = _dataset(request.get("dataset", "math"))
    if not isinstance(text, str) or not isinstance(reference, str):
        raise ValueError("Judge needs text and a string normalized reference")
    # Official math_eval applies these three stop strings before run_execute.
    # Preserve raw text in the caller's generation journal; this is judging only.
    for stop in ("</s>", "<|im_end|>", "<|endoftext|>"):
        text = text.split(stop)[0]
    text = text.strip()
    if not reference.strip():
        return {"status": "unresolved", "correct": None, "prediction": None,
                "reference": reference, "parseable": None, "reason": "unresolved_reference",
                "reference_normalization_status": "empty_under_upstream",
                "error": None}
    parser, grader = _upstream()
    prediction = parser.run_execute(None, text, "qwen-boxed", dataset, execute=False)[0]
    # The owner contract explicitly gives completed empty/unparsed output zero.
    # Upstream exact string equality occurs before its empty checks, so do not
    # let an empty prediction become correct through that implementation edge.
    correct = bool(prediction) and bool(grader.math_equal(prediction, reference, timeout=False))
    return {"status": "resolved", "correct": correct, "prediction": prediction,
            "reference": reference, "parseable": bool(prediction),
            "extraction_route": extraction_route(text),
            "reason": None if prediction else "unparsed_prediction"}


def _worker():
    # Imports complete before a per-answer timeout begins. Missing dependencies
    # fail the readiness handshake, never manufacture benchmark errors.
    try:
        identity = environment_identity()
        _upstream()
        print(json.dumps({"status": "ready", "identity": identity}), flush=True)
    except Exception as exc:
        print(json.dumps({"status": "unavailable", "error": type(exc).__name__ + ": " + str(exc)}), flush=True)
        return
    for line in sys.stdin:
        started = time.monotonic()
        try:
            result = _judge(json.loads(line))
        except Exception as exc:
            result = {"status": "unresolved", "correct": None, "prediction": None,
                      "reason": "judge_exception", "error": type(exc).__name__ + ": " + str(exc)}
        result["judge_seconds"] = time.monotonic() - started
        print(json.dumps(result, ensure_ascii=True, allow_nan=False), flush=True)


class MathScorer:
    """Persistent sequential judge, killed and recreated after a timed-out row."""

    def __init__(self, timeout_seconds: float = 3.0, startup_timeout: float = 30.0):
        if timeout_seconds <= 0 or startup_timeout <= 0:
            raise ValueError("Judge timeouts must be positive")
        self.timeout_seconds = timeout_seconds
        self.startup_timeout = startup_timeout
        self.process = None
        self.identity = None

    def _read(self, timeout: float) -> dict:
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            if not selector.select(timeout):
                raise TimeoutError("judge deadline")
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("judge process exited without a result")
        return json.loads(line)

    def _start(self):
        if self.process is not None and self.process.poll() is None:
            return
        self.close()
        self.process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--judge-worker"],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, text=True, bufsize=1,
                                        env=os.environ.copy())
        ready = self._read(self.startup_timeout)
        if ready.get("status") != "ready":
            self.close()
            raise RuntimeError(ready.get("error", "judge not ready"))
        self.identity = ready["identity"]

    def score(self, text: str, reference: str, dataset: str = "math", *,
              timeout_seconds: float | None = None) -> dict:
        started = time.monotonic()
        timeout = self.timeout_seconds if timeout_seconds is None else timeout_seconds
        if timeout <= 0:
            raise ValueError("Judge timeout must be positive")
        try:
            self._start()
        except Exception as exc:
            self.close()
            return {"status": "unresolved", "correct": None, "prediction": None,
                    "reason": "judge_unavailable", "error": type(exc).__name__ + ": " + str(exc)}
        try:
            request = {"text": text, "reference": reference, "dataset": _dataset(dataset)}
            self.process.stdin.write(json.dumps(request, ensure_ascii=True, allow_nan=False) + "\n")
            self.process.stdin.flush()
            result = self._read(timeout)
            if result.get("status") not in {"resolved", "unresolved"}:
                raise ValueError("Malformed judge response")
            if (result["status"] == "resolved" and type(result.get("correct")) is not bool) or (
                    result["status"] == "unresolved" and result.get("correct") is not None):
                raise ValueError("Invalid correctness/status combination")
            return result
        except TimeoutError:
            self.close()
            return {"status": "unresolved", "correct": None, "prediction": None,
                    "reason": "judge_timeout", "timeout_seconds": timeout,
                    "wall_seconds": time.monotonic() - started}
        except Exception as exc:
            self.close()
            return {"status": "unresolved", "correct": None, "prediction": None,
                    "reason": "judge_process_failure", "error": type(exc).__name__ + ": " + str(exc)}

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait()
            for stream in (self.process.stdin, self.process.stdout):
                if stream:
                    stream.close()
            self.process = None

    def __enter__(self):
        self._start()
        return self

    def __exit__(self, *args):
        self.close()


def score_completion(text: str, reference: str, dataset: str = "math", *,
                     timeout_seconds: float = 3.0) -> dict:
    scorer = MathScorer(timeout_seconds=timeout_seconds)
    try:
        return scorer.score(text, reference, dataset)
    finally:
        scorer.close()


if __name__ == "__main__":
    if sys.argv[1:] != ["--judge-worker"]:
        raise SystemExit("Use scoring.MathScorer or --judge-worker")
    _worker()
