"""Conservative evidence-result memoization, independent of contribution labels.

The caller must assess dependency completeness, determinism and read-only scope.
Those declarations are not inferred from command similarity or graph state IDs.
Only completed, complete observations are reusable; a known deterministic failed
check can be cached, whereas a timeout/infrastructure error is not a certificate.
"""
from dataclasses import dataclass
import hashlib
import json


@dataclass(frozen=True)
class EvidenceContext:
    checker_id: str
    checker_digest: str
    property_id: str
    cwd: str
    environment_digest: str
    dependency_digests: tuple[tuple[str, str], ...]
    goal_context: str
    deterministic: bool = False
    scope_complete: bool = False
    read_only: bool = False


def evidence_key(context):
    if not (context.deterministic and context.scope_complete and context.read_only):
        return None
    values = [context.checker_id, context.checker_digest, context.property_id,
              context.cwd, context.environment_digest, context.goal_context]
    if any(not isinstance(v, str) or not v for v in values): return None
    dependencies = context.dependency_digests
    if not dependencies or len({name for name, _ in dependencies}) != len(dependencies): return None
    if any(not name or not isinstance(digest,str) or len(digest)!=64
           or any(ch not in '0123456789abcdef' for ch in digest) for name,digest in dependencies): return None
    payload = dict(checker=context.checker_id,checker_digest=context.checker_digest,
                   property=context.property_id,cwd=context.cwd,environment=context.environment_digest,
                   dependencies=sorted(dependencies),goal_context=context.goal_context)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',',':')).encode()).hexdigest()


class EvidenceCache:
    def __init__(self): self._records = {}

    def store(self, context, result, *, status, observation_complete, provenance):
        key = evidence_key(context)
        if key is None or status != 'completed' or not observation_complete or not provenance:
            return False
        # Serialize rather than retain mutable references. Pass/fail can both be evidence.
        self._records[key] = json.dumps(dict(result=result,provenance=provenance),sort_keys=True,allow_nan=False)
        return True

    def lookup(self, context):
        key = evidence_key(context)
        if key is None or key not in self._records: return None
        return dict(json.loads(self._records[key]), reused=True, evidence_key=key)
