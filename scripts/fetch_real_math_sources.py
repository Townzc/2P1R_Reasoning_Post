"""Fetch pinned public CPU-audit inputs, with a finite download cap.

Original references and released generated solutions are separate commands.
Never execute downloaded dataset scripts. Existing files must match receipts.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request

SUBJECTS = ('algebra', 'counting_and_probability', 'geometry',
            'intermediate_algebra', 'number_theory', 'prealgebra', 'precalculus')


def specifications(config, solutions=False):
    def hf(repo, revision, path):
        return f'https://huggingface.co/datasets/{repo}/resolve/{revision}/{path}'
    if solutions:
        return [(f'omi_{i:05d}.parquet', hf('nvidia/OpenMathInstruct-2',
                 config['solution_revision'], f'data/train-{i:05d}-of-00032.parquet'), sha)
                for i, sha in zip(config['solution_shards'], config['solution_shard_sha256'])]
    items = []
    for split in ('train', 'test'):
        items.append((f'gsm8k_{split}.jsonl', 'https://raw.githubusercontent.com/'
                      f"openai/grade-school-math/{config['gsm8k_revision']}/grade_school_math/data/{split}.jsonl", None))
        items.append((f'math_benchmark_{split}.parquet', hf('nlile/hendrycks-MATH-benchmark',
                      config['math_id_revision'], f'data/{split}-00000-of-00001.parquet'), None))
        for subject in SUBJECTS:
            items.append((f'math_{subject}_{split}.parquet', hf('EleutherAI/hendrycks_math',
                          config['math_revision'], f'{subject}/{split}-00000-of-00001.parquet'), None))
    items += [
        ('math_merged.parquet', hf('qwedsacf/competition_math', config['math_merged_revision'],
                                 'data/train-00000-of-00001-7320a6f3aba8ebd2.parquet'), None),
        ('math_legacy_loader.py.txt', hf('EleutherAI/hendrycks_math', config['math_loader_revision'],
                                       'hendrycks_math.py'), None),
        ('gsm_symbolic.zip', f"https://codeload.github.com/apple/ml-gsm-symbolic/zip/{config['gsm_symbolic_revision']}", None),
        ('omi_README.md', hf('nvidia/OpenMathInstruct-2', config['solution_revision'], 'README.md'), None),
    ]
    return items


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for b in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', default='configs/diagnostics/real_math_c017.json')
    p.add_argument('--cache', required=True)
    p.add_argument('--solutions', action='store_true')
    p.add_argument('--frozen-manifest')
    args = p.parse_args()
    c = json.loads(Path(args.config).read_text())
    root = Path(args.cache)
    root.mkdir(parents=True, exist_ok=True)
    if args.solutions:
        if not args.frozen_manifest:
            p.error('--solutions requires a frozen problem manifest')
        manifest = Path(args.frozen_manifest)
        frozen = json.loads((manifest.parent / 'freeze.json').read_text())
        if digest(manifest) != frozen['problem_manifest_sha256']:
            raise ValueError('Frozen problem manifest changed')
        if digest(Path(args.config)) != frozen['config_sha256']:
            raise ValueError('Audit configuration changed since problem freeze')
    started = time.monotonic()
    for name, url, expected in specifications(c, args.solutions):
        dest = root / name
        receipt = root / f'{name}.receipt.json'
        if dest.exists() and receipt.exists():
            r = json.loads(receipt.read_text())
            if r['url'] != url or digest(dest) != r['sha256'] or (expected and r['sha256'] != expected):
                raise ValueError(f'Cached input differs: {name}')
            print(f'verified cache {name}', flush=True)
            continue
        if dest.exists():
            # Adopt a read-only discovery download only after hashing it; never overwrite it.
            sha = digest(dest)
            if expected and sha != expected:
                raise ValueError(f'Existing source checksum mismatch: {name}')
            r = {'url': url, 'sha256': sha, 'bytes': dest.stat().st_size,
                 'download_seconds': None, 'preaudit_discovery_download': True}
        else:
            before = time.monotonic()
            partial = dest.with_suffix(dest.suffix + '.partial')
            if partial.exists():
                raise FileExistsError(f'Retain failed download and choose a new cache: {partial}')
            with urllib.request.urlopen(url, timeout=60) as response, partial.open('xb') as out:
                for block in iter(lambda: response.read(1024 * 1024), b''):
                    out.write(block)
                    if sum(x.stat().st_size for x in root.iterdir() if x.is_file()) > c['source_download_byte_cap']:
                        raise RuntimeError('CPU source download cap exceeded')
            sha = digest(partial)
            if expected and sha != expected:
                raise ValueError(f'Download checksum mismatch: {name}')
            partial.rename(dest)
            r = {'url': url, 'sha256': sha, 'bytes': dest.stat().st_size,
                 'download_seconds': time.monotonic() - before, 'preaudit_discovery_download': False}
        with receipt.open('x') as out:
            json.dump(r, out, indent=2)
            out.write('\n')
        print(json.dumps({'file': name, 'bytes': r['bytes'], 'seconds': r['download_seconds']}), flush=True)
    print(json.dumps({'phase_seconds': time.monotonic() - started}), flush=True)


if __name__ == '__main__':
    main()
