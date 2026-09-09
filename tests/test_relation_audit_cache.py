import unittest
from scripts.audit_relation_engineering_cached import ReadOnlyVocabularyCache


class CacheTests(unittest.TestCase):
    def test_immutable_size_is_cached_and_methods_are_forwarded(self):
        class Tokenizer:
            size = 17
            calls = 0
            eos_token_id = 2
            def __len__(self): self.calls += 1; return self.size
            def __call__(self, text, **kwargs): return {'text': text, **kwargs}
            def decode(self, ids): return str(ids)
        original = Tokenizer(); cached = ReadOnlyVocabularyCache(original)
        self.assertEqual([len(cached) for _ in range(100)], [17]*100)
        self.assertEqual(original.calls, 1)
        self.assertEqual(cached('x', padding=False), original('x', padding=False))
        self.assertEqual(cached.decode([3,2]), original.decode([3,2]))
        self.assertEqual(cached.eos_token_id, 2)
        cached.verify_unchanged(); self.assertEqual(original.calls, 2)
        original.size += 1
        with self.assertRaises(ValueError): cached.verify_unchanged()


if __name__ == '__main__':
    unittest.main()
