import pytest
from experiments.p012.freeze_grid import nested_cells


def test_nested_allocation_controls():
    parents = [str(i) for i in range(4096)]
    solutions = {p: [{"parent_id": p, "solution_hash": str(k)} for k in range(8)] for p in parents}
    cells = nested_cells(parents, solutions)
    assert [len(cells[k]) for k in ("P", "K8", "K4", "R", "L")] == [4096, 4096, 4096, 512, 512]
    assert cells["R"] == cells["L"] == cells["P"][:512]
    assert {r["parent_id"] for r in cells["K8"]} == set(parents[:512])
    assert {r["parent_id"] for r in cells["K4"]} == set(parents[:1024])
    solutions["0"][1] = solutions["0"][0]
    with pytest.raises(ValueError, match="Repeated"):
        nested_cells(parents, solutions)


def test_missing_solution_cannot_silently_reduce_dose():
    parents = [str(i) for i in range(4096)]
    solutions = {p: [{"parent_id": p, "solution_hash": str(k)} for k in range(8)] for p in parents}
    solutions["0"].pop()
    with pytest.raises(ValueError, match="dose"):
        nested_cells(parents, solutions)
