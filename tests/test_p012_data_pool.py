import hashlib
import json
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq

from experiments.p012.data_pool import collect, ngrams, normalized


def test_normalized_contiguous_13gram_rule():
    phrase = "one two three four five six seven eight nine ten eleven twelve thirteen"
    assert ngrams(phrase) & ngrams("prefix " + phrase.upper() + " suffix")
    assert not ngrams("one two three four five six seven eight nine ten eleven twelve")
    assert normalized("  ＡＢＣ  ") == "ABC"


def test_real_parquet_collection_keeps_reserved_questions_out_and_deduplicates(tmp_path, monkeypatch):
    monkeypatch.setenv("P012_CODE_COMMIT", "0" * 40)
    assets, manifests = tmp_path / "assets", tmp_path / "manifests"
    manifests.mkdir()
    omi = []
    def save(slug, name, rows):
        path = assets / slug / name
        path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pylist(rows), path)
        return {"path": name, "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    for task, slug, folder in [("math", "DigitalLearningGmbH__MATH-lighteval", "data"),
                                ("gsm8k", "openai__gsm8k", "main")]:
        field = "problem" if task == "math" else "question"
        response = "solution" if task == "math" else "answer"
        train = [{field: f"Synthetic {task} problem {i}: add one and one", response: r"\boxed{2}" if task == "math" else "1+1=2. #### 2"} for i in range(6)]
        test = [{field: "Exact heldout question", response: r"\boxed{2}" if task == "math" else "#### 2"}]
        files = [save(slug, f"{folder}/train-00000-of-00001.parquet", train + test),
                 save(slug, f"{folder}/test-00000-of-00001.parquet", test)]
        (manifests / f"{slug}_FILES.json").write_text(json.dumps({"repo": slug, "revision": "fixed", "files": files}))
        for row in train:
            for solution, source in [(r"\boxed{2}", task), (r"\boxed{2}", task), (r"\boxed{3}", task), (r"\boxed{2}", "augmented_" + task)]:
                omi.append({"problem": row[field], "generated_solution": solution,
                            "expected_answer": "2", "problem_source": source})
    file = save("nvidia__OpenMathInstruct-2", "data/train-00000-of-00001.parquet", omi)
    (manifests / "nvidia__OpenMathInstruct-2_FILES.json").write_text(json.dumps({"repo": "omi", "revision": "fixed", "files": [file]}))
    result = collect(assets, manifests, tmp_path / "output")
    assert result["counts"]["unique_solutions"] == 4
    assert result["counts"]["answer_rejected"] == 4
    assert result["counts"]["correct_before_dedupe"] == 8
    assert result["length_filter_complete"] is False
    removed = json.loads((tmp_path / "output/DECONTAMINATION.json").read_text())
    assert all(r["removed_counts"] == {"exact_test": 1} for r in removed.values())
    assert all(r["unique_candidates_after_demo_reservation"] == 2 for r in removed.values())
