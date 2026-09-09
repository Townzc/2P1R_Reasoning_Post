"""CPU-only E011 audit adapter: memoize the immutable tokenizer vocabulary size.

The frozen scorer, tokenization, input checks and result schema are unchanged.
Some tokenizers versions make len(tokenizer) expensive; the original auditor
calls it for every generated token. Check the cached value again after auditing.
"""
import argparse
from pathlib import Path

from scripts.audit_family_matching import verified_tokenizer
from scripts.audit_relation_engineering_outputs import audit
from src.relation_engineering import dump


class ReadOnlyVocabularyCache:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.size = len(tokenizer)

    def __len__(self):
        return self.size

    def __call__(self, *args, **kwargs):
        return self.tokenizer(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.tokenizer, name)

    def verify_unchanged(self):
        if len(self.tokenizer) != self.size:
            raise ValueError('Tokenizer vocabulary mutated during read-only audit')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True)
    p.add_argument('--tokenizer-dir', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    if Path(a.out).exists():
        raise FileExistsError('Immutable verification already exists')
    tokenizer, _ = verified_tokenizer(Path(a.tokenizer_dir))
    wrapped = ReadOnlyVocabularyCache(tokenizer)
    result = audit(a.run_dir, wrapped)
    wrapped.verify_unchanged()
    dump(a.out, result)
    print({'verified_compact_outputs': result['verified_compact_outputs'],
           'predictions_rechecked': result['predictions_rechecked'],
           'engineering_gate': result['engineering_gate']})


if __name__ == '__main__':
    main()
