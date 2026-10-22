"""Route only the evidence-store name; call the original v3 cell unchanged."""
import argparse
from experiments.p011 import forced_answer_worker as original
from experiments.p011.forced_answer_relaunch import STORE, REMOTE


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cell', required=True)
    p.add_argument('--deadline', type=float, required=True)
    a = p.parse_args()
    original.STORE = STORE
    if original.REMOTE != REMOTE:
        raise ValueError('Original upload and previously unwritten output path changed')
    original.run(a.cell, a.deadline)


if __name__ == '__main__':
    main()
