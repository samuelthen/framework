"""Separate follow-up outputs; original validation inputs are read-only."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'results/precision_validation_20261026'
OUT=ROOT/'results/followup_20261026'
SEED=20261026
sys.path.insert(0,str(ROOT/'worktrace'))


def jsonl(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def dump(path,obj):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(obj,indent=2,default=str,allow_nan=False)+'\n')


def lines(path,rows):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(''.join(json.dumps(x,default=str)+'\n' for x in rows))


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
