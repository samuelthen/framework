"""Recover selected records and pinned source archives after download_inputs.py.

Uses the frozen blinding key; does not choose cases based on these new results.
Extracts ordinary archive files only, with paths confined to the selected root.
"""
import csv
import json
from pathlib import Path
import shutil
import tarfile
import urllib.request

import pyarrow.parquet as pq
from worktrace.loaders.jetbrains import load_row

ROOT = Path(__file__).resolve().parents[2]


def extract_archive(archive, destination):
    with tarfile.open(archive) as source:
        for member in source:
            if not member.isfile():
                continue
            relative = Path(*Path(member.name).parts[1:])
            if relative.is_absolute() or '..' in relative.parts or not relative.parts:
                raise ValueError('Unsafe archive path')
            target = destination / relative
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError('Unsafe archive target')
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.extractfile(member) as incoming, target.open('wb') as output:
                shutil.copyfileobj(incoming, output)


def main():
    key = list(csv.DictReader((ROOT/'results/one_day_precision_20261026/packets/blinding_key.csv').open()))
    annotations = [json.loads(s) for s in (ROOT/'results/precision_validation_20261026/reconciled_component_annotations.jsonl').read_text().splitlines() if s.strip()]
    included = {(int(r['order']),r['blinded_label']) for r in annotations}
    selected = {r['run_id']: r for r in key if (int(r['order']),r['label']) in included}
    output = ROOT/'raw/utility_selected'; output.mkdir(parents=True, exist_ok=True)
    operations, runs, cases = [], [], {}
    for model in ['luna', 'gemini_3_7_flash']:
        parquet = pq.ParquetFile(ROOT/f'raw/jetbrains/{model}-run1.parquet')
        for batch in parquet.iter_batches(batch_size=10):
            for row in batch.to_pylist():
                rid = f"jb:{row['model']}:{row['instance_id']}:r{int(row['run'])}"
                if rid not in selected:
                    continue
                info = selected[rid]; order = int(info['order'])
                run, ops = load_row(row); run.update(order=order, blinded_label=info['label'])
                for index, op in enumerate(ops):
                    op.update(order=order, blinded_label=info['label'], action_index=index)
                operations.extend(ops); runs.append(run)
                (output/f'{order:02d}_{model}.json').write_text(json.dumps(row))
                if order in [3,4] and model == 'luna': cases[order] = row['instance_id']
    if len(runs) != 16: raise ValueError('Frozen selection must contain 16 runs')
    for name, records in [('operations',operations), ('runs',runs)]:
        (output/f'{name}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
    refs = {r['instance_id']: r for r in pq.read_table(ROOT/'raw/swebenchpro/v1.parquet').to_pylist()}
    for order, instance in cases.items():
        ref = refs[instance]; folder = ROOT/f'raw/utility_replay/task{order:02d}'
        folder.mkdir(parents=True, exist_ok=True)
        archive = folder/'base.tar.gz'
        url = f"https://codeload.github.com/{ref['repo']}/tar.gz/{ref['base_commit']}"
        if not archive.exists():
            with urllib.request.urlopen(url, timeout=60) as source, archive.open('wb') as output_file:
                shutil.copyfileobj(source,output_file)
        # A pre-existing base is immutable input; do not erase it on repeat.
        if not (folder/'base').exists(): extract_archive(archive,folder/'base')
    for cache in ['go_modcache','go_buildcache']:
        (ROOT/'raw/utility_replay'/cache).mkdir(parents=True, exist_ok=True)
    print(f'Recovered {len(runs)} runs and {len(operations)} native calls.')


if __name__ == '__main__': main()
