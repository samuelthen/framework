"""Fetch only two pinned trajectory shards and one task reference shard.

No credentials, model calls, or task execution. Existing files must match the
archived manifest; partial downloads never become accepted inputs.
"""
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
INPUTS = [
    ('raw/jetbrains/luna-run1.parquet', 'JetBrains-Research/SWE-TaskFlow-SWE-Bench-Pro-Trajectories',
     'a5ec6ad8428715a689ee62cf7cef82334773c958', 'data/single_prompt/luna-run1.parquet',
     '1a7af8a0531b4d1283bca357b00f1e4f42ab65b4a5088bee8082a95ff6e2017b'),
    ('raw/swebenchpro/v1.parquet', 'ScaleAI/SWE-bench_Pro',
     '2d52cb3df914a3fcf80c7f66738b3a88ae37fc50', 'data/v1/test-00000-of-00001.parquet',
     'c8cd7115496ad4e9a8b21d088cef576a65bf821bb542b24336f13f714cef13f8'),
    ('raw/jetbrains/gemini_3_7_flash-run1.parquet', 'JetBrains-Research/SWE-TaskFlow-SWE-Bench-Pro-Trajectories',
     'a5ec6ad8428715a689ee62cf7cef82334773c958', 'data/single_prompt/gemini_3_7_flash-run1.parquet',
     'dee351735e2dd3a1115501c475ec8f7df054ab58da3bf21ea9a9b1fea5c6166e'),
]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): h.update(block)
    return h.hexdigest()


def main():
    (ROOT / 'results/utility_audit_20261028').mkdir(parents=True, exist_ok=True)
    rows = []
    for destination, repository, revision, filename, expected in INPUTS:
        target = ROOT / destination
        url = f'https://huggingface.co/datasets/{repository}/resolve/{revision}/{filename}?download=true'
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_suffix('.partial')
            print(f'Downloading {destination}', flush=True)
            started = time.monotonic()
            request = urllib.request.Request(url, headers={'User-Agent': 'WorkTrace-reproducibility-audit'})
            with urllib.request.urlopen(request, timeout=60) as source, partial.open('wb') as output:
                count, last = 0, time.monotonic()
                while block := source.read(1 << 20):
                    output.write(block); count += len(block)
                    if time.monotonic() - last > 15:
                        print(f'{destination}: {count / 1e6:.1f} MB', flush=True); last = time.monotonic()
            actual = digest(partial)
            if actual != expected:
                raise ValueError(f'Hash mismatch for {destination}; partial retained for diagnosis')
            partial.replace(target)
            print(f'Verified {destination}: {target.stat().st_size} bytes in {time.monotonic()-started:.1f}s', flush=True)
        actual = digest(target)
        if actual != expected: raise ValueError(f'Existing file hash mismatch: {destination}')
        rows.append(dict(path=destination, repository=repository, revision=revision,
                         sha256=actual, bytes=target.stat().st_size, url=url))
        manifest = ROOT / 'results/utility_audit_20261028/download_manifest.json'
        manifest.write_text(json.dumps(dict(status='partial' if len(rows) < len(INPUTS) else 'complete',
                                           verified_inputs=rows, raw_files_excluded_from_git=True), indent=2) + '\n')
    print('All selected inputs verified.', flush=True)


if __name__ == '__main__': main()
