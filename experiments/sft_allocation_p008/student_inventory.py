"""Adapt verified P008 parent metadata to the existing full-answer SFT contract.

P008 eligible parents contain id/problem/answer/reference. The older converter
also expects group_id; for GSM8K each original question is its own group. This
adds that identity metadata to copies only, without rewriting a parent, prompt,
teacher response, score, acquisition decision or usable-answer selection.
"""
from experiments.sft_allocation_acquisition.student_contract import training_rows as _convert


def training_rows(parents, acquired_ids, records):
    normalized = []
    for parent in parents:
        if set(parent) != {'id', 'problem', 'answer', 'reference'}:
            raise ValueError('Expected exact original P008 eligible-parent schema')
        normalized.append(dict(parent, group_id=parent['id']))
    return _convert(normalized, acquired_ids, records)
