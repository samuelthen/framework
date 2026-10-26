"""Recorded Codex review of eight task references. Does not infer test outcomes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / 'results/one_day_precision_20261026'
OUT = ROOT / 'results/precision_validation_20261026'

# These are explicit review decisions after reading issue, dataset bullets,
# reference diffs, and both submitted diffs. They are not automatic correctness
# labels and are intentionally kept distinct from the blinded reviewer files.
REVIEWS = {
    3: {
        'decision': 'Keep cancellation, deadline and auth propagation as three repair obligations. Keep unrelated flows as preservation, not a new repair.',
        'alternatives': 'errors.Is with switch/early return, aliased standard errors import, or raw auth context error passed to outer classifier can support the requirements. Interceptor-chain refactoring is not itself a required behavior.',
        'conflicts': ['Run Y retains status.FromError before the context checks; plain/wrapped context-error route is visible, but preservation of arbitrary pre-existing status errors and custom cancellation wrappers requires targeted evidence. Do not infer exhaustive correctness from resolved.'],
        'uncertain_requirements': [],
    },
    4: {
        'decision': 'Separate the invariant explicit-key loading repair from the conflicting absent-key default. Existing default/deprecated fixture compatibility is preservation.',
        'alternatives': 'Field/key declarations and guarded viper reads can be implemented by targeted edits or file rewrite. SQL pool application in the broad reference is outside the stated loader repair; do not require its exact patch.',
        'conflicts': ['Dataset bullet 3 requires absent meta.check_for_updates=false. The issue and bullet 4 require preserving Default(); the reference retains Default().Meta.CheckForUpdates=true and uses IsSet. Run X retains true; Run Y changes Default() to false. The same reference cannot establish both branches.'],
        'uncertain_requirements': ['R3_absent_default'],
    },
    5: {
        'decision': 'The utility and state-to-liveness mapping plus exclusive update path are repairs. Initial not-live and change-only event guard are already present preservation obligations.',
        'alternatives': 'Switch or conditional mapping and appropriate imports are acceptable. setState/start/position/chunk paths must stop independently changing liveness. A renamed helper is acceptable only if the specified importable interface remains available.',
        'conflicts': [], 'uncertain_requirements': [],
    },
    6: {
        'decision': 'Separate enum/schema creation from each evaluator outcome. Unknown/no-match is an explicit obligation even though zero enum value supplies it; classify as preserve_by_zero_default after the new enum exists, not a separately observed repair.',
        'alternatives': 'Generated or carefully maintained Go/Swagger changes can support the behavior if consistent with the proto; generator installation alone is scaffolding. Returning the new field on gRPC and REST matters, not the generator sequence.',
        'conflicts': ['Broad regenerated artifacts can contain unrelated changes; a regeneration call must not receive all credit because its evaluator portion contributes. No isolated task test environment was executed in this validation.'],
        'uncertain_requirements': [],
    },
    7: {
        'decision': 'Keep path/zip resource discovery, extension exclusions, POSIX keys and preload integration. Validate the ext precondition and directory existence from explicit evidence, not just a passing helper example.',
        'alternatives': 'Pathlib glob plus zip traversal or equivalent traversal preserving the required relative names is acceptable; widened type annotations are support, not a separate behavioral obligation.',
        'conflicts': [], 'uncertain_requirements': [],
    },
    8: {
        'decision': 'Rename registration, completion providers and user-facing references. Numeric/substring matching, count precedence, window references and activation already exist; preserve them rather than crediting their rediscovery as newly implemented repairs.',
        'alternatives': 'Rename existing methods/providers or equivalent delegation while removing deprecated user-visible buffer entries. Do not require implementation restructuring in the reference.',
        'conflicts': ['The title/issue includes configuration examples and help, and the reference changes configdata.yml gt binding. Run X final patch omits that binding while recorded resolved. Task/harness source-boundary instructions may restrict YAML changes. Retain the binding as a disputed scope obligation; recorded success does not establish complete migration.'],
        'uncertain_requirements': ['R5'],
    },
    9: {
        'decision': 'Scope is the importable pure _sort_values helper: ordered names, unknown ID omission and exclusion of unrequested values. Do not require unrelated observations feature migration from the broad reference.',
        'alternatives': 'Lookup-map or nested traversal implementations are valid for the stated inputs; no exact line/file migration sequence is required beyond exposing the specified helper in observations.py.',
        'conflicts': ['The broad reference includes unrelated observations work. Ignore that extra patch scope when judging solution contribution for this issue.'],
        'uncertain_requirements': [],
    },
    10: {
        'decision': 'Map access and per-server configuration selection are repairs. Existing value/ok signaling and Status==inactive filtering are preservation obligations unless the trace demonstrates a defect in that behavior.',
        'alternatives': 'Map-valued parameters with updated call sites are directly consistent. A compatibility interface{} wrapper may permit valid direct-map calls, but its pointer branch is outside the required direct-map path and is not automatically credited.',
        'conflicts': ['Run X combines global and per-server ignore flags with OR; whether an explicit per-server false must override global true is not resolved by the saved accepted outcome.', 'Run Y accepts both map and legacy pointer through interface{}; judge the normal map path separately from the literal no-pointer requirement and legacy test compatibility.'],
        'uncertain_requirements': ['R1_legacy_pointer_compatibility', 'R3_global_override_precedence'],
    },
}


def main():
    records = []
    for order, review in REVIEWS.items():
        source = json.loads((OLD / f'requirements_raw/{order:02d}.json').read_text())
        rec = {'order': order, 'task_id': source['task_id'],
               'provenance': 'Codex review of saved issue/reference/trace/submission; model-coded; not execution- or human-validated',
               'source_packet': str(next((OLD / 'packets').glob(f'{order:02d}_*.md')).relative_to(ROOT)),
               'requirements': source['requirements'], **review}
        if order == 4:
            rec['requirements'].append({'id': 'R3_absent_default', 'kind': 'disputed',
                'description': 'Value when meta.check_for_updates is absent: false versus preserved Default() true.',
                'source': 'dataset bullet 3 versus issue, bullet 4 and reference',
                'alternatives': 'Report both interpretations; do not adjudicate from recorded resolved alone.'})
        if order == 6:
            rec['requirements'][4]['kind'] = 'preserve_by_zero_default'
        records.append(rec)
    (OUT / 'requirements_review.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in records))
    lines = ['# Requirement review', '', 'Eight existing evaluation tasks; no new task execution. Conflicting references remain explicit.', '']
    for r in records:
        lines += [f"## Task {r['order']:02d}", '', r['decision'], '', r['alternatives'], '']
        lines += [f'- {c}' for c in r['conflicts']] or ['No reference conflict identified in this review.']
        lines.append('')
    (OUT / 'requirements_review.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
