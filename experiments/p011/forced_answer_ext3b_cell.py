"""Route the unchanged accepted generation worker to the two new cells."""
import argparse
from experiments.p011 import forced_answer_worker as original
from experiments.p011.forced_answer_ext3b import CELLS, STORE, REMOTE

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--cell', choices=CELLS, required=True)
    p.add_argument('--deadline', type=float, required=True)
    a = p.parse_args()
    original.STORE, original.REMOTE = STORE, REMOTE
    original.run(a.cell, a.deadline)
