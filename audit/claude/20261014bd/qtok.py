"""Minimal pure-Python Qwen2 byte-level BPE encoder/decoder for audit (no external deps)."""
import json, re, sys, unicodedata
from functools import lru_cache

def _ranges(pred):
    out = []; start = None
    for cp in range(0x110000):
        ok = pred(cp)
        if ok and start is None: start = cp
        if not ok and start is not None:
            out.append((start, cp - 1)); start = None
    if start is not None: out.append((start, 0x10FFFF))
    def esc(c): return '\\U%08x' % c
    return ''.join(esc(a) if a == b else esc(a) + '-' + esc(b) for a, b in out)

_L = _ranges(lambda c: unicodedata.category(chr(c)).startswith('L'))
_N = _ranges(lambda c: unicodedata.category(chr(c)).startswith('N'))

def build(path, nfc=None):
    tj = json.load(open(path, encoding='utf-8'))
    pat = tj['pre_tokenizer']['pretokenizers'][0]['pattern']['Regex']
    pat = pat.replace('\\p{L}\\p{N}]', _L + _N + ']').replace('\\p{L}', '[' + _L + ']').replace('\\p{N}', '[' + _N + ']')
    rx = re.compile(pat)
    use_nfc = (tj.get('normalizer') or {}).get('type') == 'NFC' if nfc is None else nfc
    vocab = tj['model']['vocab']
    merges = tj['model']['merges']
    ranks = {}
    for i, m in enumerate(merges):
        a, b = (m.split(' ') if isinstance(m, str) else m)
        ranks[(a, b)] = i
    added = {a['content']: a['id'] for a in tj['added_tokens']}
    inv = {v: k for k, v in vocab.items()}
    for c, i in added.items(): inv[i] = c
    special = set(added.values())
    bs = list(range(ord('!'), ord('~') + 1)) + list(range(ord('¡'), ord('¬') + 1)) + list(range(ord('®'), ord('ÿ') + 1))
    cs = bs[:]; n = 0
    for b in range(256):
        if b not in bs: bs.append(b); cs.append(256 + n); n += 1
    benc = {b: chr(c) for b, c in zip(bs, cs)}
    bdec = {chr(c): b for b, c in zip(bs, cs)}
    addrx = re.compile('(' + '|'.join(re.escape(k) for k in sorted(added, key=len, reverse=True)) + ')')

    @lru_cache(maxsize=200000)
    def bpe(word):
        parts = list(word)
        while len(parts) > 1:
            best = None
            for i in range(len(parts) - 1):
                r = ranks.get((parts[i], parts[i + 1]))
                if r is not None and (best is None or r < best[0]): best = (r, i)
            if best is None: break
            i = best[1]; parts[i:i + 2] = [parts[i] + parts[i + 1]]
        return tuple(vocab[p] for p in parts)

    def encode(text):
        text = unicodedata.normalize('NFC', text) if use_nfc else text
        ids = []
        for seg in addrx.split(text):
            if not seg: continue
            if seg in added: ids.append(added[seg]); continue
            for piece in rx.findall(seg):
                ids.extend(bpe(''.join(benc[b] for b in piece.encode('utf-8'))))
        return ids

    def decode(ids, skip_special=False):
        out = bytearray(); txt = []
        for i in ids:
            if i in special:
                if skip_special: continue
                out_s = out.decode('utf-8', errors='replace'); txt.append(out_s); out = bytearray(); txt.append(inv[i]); continue
            out += bytes(bdec[ch] for ch in inv[i])
        txt.append(out.decode('utf-8', errors='replace'))
        return ''.join(txt)
    return encode, decode, added
