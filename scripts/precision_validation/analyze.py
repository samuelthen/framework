"""Recompute reviewed precision, shared-unit agreement and descriptive baselines.

No labeling APIs or trajectory commands are invoked. Original study is read-only.
Missing reviews are reported, never replaced by projected labels.
"""
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/precision_validation_20261026'
OLD = ROOT / 'results/one_day_precision_20261026'
LABELS = ('direct', 'non_direct', 'uncertain')
ROLES = ('exploration', 'edit', 'verification', 'administration')
G, L = 'gemini-3.7-flash', 'gpt-5.6-luna'
SEED = 20261026


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=str, allow_nan=False) + '\n')


def scalar(x):
    return None if pd.isna(x) else float(x)


def score(rows):
    """One label throughout all roles; known-unexecuted candidates excluded.

    Unknown execution stays uncertain, bounding both execution and attribution.
    Unannotated components are rejected by validate_review, not quietly dropped.
    """
    rows = [r for r in rows if r.get('execution_status') != 'not_executed']
    n = len(rows)
    d = sum(r['contribution_label'] == 'direct' for r in rows)
    u = sum(r['contribution_label'] == 'uncertain' for r in rows)
    nd = n - d - u
    return {'N': n, 'D': d, 'ND': nd, 'U': u,
            'P_lower': d / n if n else None,
            'P_upper': (d + u) / n if n else None,
            'non_direct_share': nd / n if n else None,
            'uncertain_share': u / n if n else None}


def validate_review(review, inventory):
    expected = {(r['blinded_label'], r['action_index'], r['component_index']) for r in inventory}
    actual = [(r['blinded_label'], r['action_index'], r['component_index']) for r in review['components']]
    assert len(actual) == len(set(actual)), 'duplicate component labels'
    assert set(actual) == expected, f'incomplete components: missing {expected-set(actual)}, extra {set(actual)-expected}'
    reqs = {r['id'] for r in review['requirements']}
    for r in review['components']:
        assert r['contribution_label'] in LABELS and r['role'] in ROLES, r
        assert r.get('evidence'), r
        assert r.get('execution_status') in ('executed', 'not_executed', 'uncertain'), r
        assert set(r.get('requirement_ids', [])) <= reqs, r
        if r['contribution_label'] == 'direct':
            assert r.get('requirement_ids'), r
        if r.get('execution_status') == 'uncertain':
            assert r['contribution_label'] == 'uncertain', r
        if r.get('execution_status') == 'not_executed':
            assert r['contribution_label'] != 'direct', r
        if r['contribution_label'] == 'non_direct':
            assert r.get('reason'), r
        if r['role'] == 'verification':
            for field in ('property_checked', 'relevant_state_changed', 'earlier_check_ids', 'verification_gain'):
                assert field in r, (field, r)
            assert r['relevant_state_changed'] in ('changed', 'unchanged', 'uncertain'), r


def project_native(rows):
    """Legacy strongest-component projection only for a common-unit diagnostic.
    This never supplies a component label or validates component agreement.
    """
    labels = [r['contribution_label'] for r in rows if r.get('execution_status') != 'not_executed']
    return 'direct' if 'direct' in labels else ('uncertain' if 'uncertain' in labels or not labels else 'non_direct')


def kappa(a, b):
    if not a:
        return {'n': 0, 'agreement': None, 'kappa': None}
    observed = np.mean(np.array(a) == np.array(b))
    expected = sum(a.count(c) * b.count(c) for c in LABELS) / len(a) ** 2
    return {'n': len(a), 'agreement': float(observed),
            'kappa': float((observed - expected) / (1 - expected)) if expected != 1 else None}


def structural(inventory, key):
    c = pd.DataFrame(inventory).merge(key, on=['order', 'blinded_label'], validate='many_to_one')
    callcounts = c.groupby(['order', 'blinded_label', 'action_index']).size().rename('components').reset_index()
    calls = callcounts.merge(key, on=['order', 'blinded_label'], validate='many_to_one')
    rows = []
    for m, group in calls.groupby('model'):
        rows.append({'model': m, 'native_calls': len(group), 'components': int(group.components.sum()),
                     'mean_components_per_call': float(group.components.mean()),
                     'median_components_per_call': float(group.components.median()),
                     'share_multicomponent_calls': float((group.components > 1).mean())})
    pd.DataFrame(rows).to_csv(OUT / 'corrected_units.csv', index=False)
    calls.to_csv(OUT / 'components_per_call.csv', index=False)
    return c, calls


def load_reviews(inventory, reviewer='reviewer_b'):
    missing, annotations, requirements = [], [], []
    lookup = {(r['order'], r['blinded_label'], r['action_index'], r['component_index']): r for r in inventory}
    for order in range(3, 11):
        path = OUT / f'{reviewer}/{order:02d}.json'
        if not path.exists():
            missing.append(order)
            continue
        review = json.loads(path.read_text())
        validate_review(review, [r for r in inventory if r['order'] == order])
        requirements.append({'order': order, 'requirements': review['requirements']})
        for r in review['components']:
            base = lookup[(order, r['blinded_label'], r['action_index'], r['component_index'])]
            annotations.append({**base, **r, 'order': order,
                'review_provenance': f'Codex model-coded blinded {reviewer} pass; not human validation'})
    return missing, annotations, requirements


def apply_role_adjudications(annotations):
    overrides = {r['component_id']: r for r in json.loads((OUT / 'role_adjudications.json').read_text())}
    applied = []
    for row in annotations:
        if row['component_id'] in overrides:
            change = overrides[row['component_id']]
            applied.append({'component_id': row['component_id'], 'original_role': row['role'],
                            'reviewed_role': change['role'], 'rationale': change['rationale'],
                            'contribution_label_unchanged': row['contribution_label']})
            row['reviewer_original_role'] = row['role']
            row['reviewer_original_reason'] = row.get('reason')
            row['role'], row['reason'] = change['role'], change['reason']
            row['role_adjudication'] = 'Codex primary role-only review; original reviewer file preserved'
    write_json(OUT / 'role_adjudications_applied.json', applied)
    return annotations


def precision_tables(annotations, key, prefix=''):
    frame = pd.DataFrame(annotations).merge(key, on=['order', 'blinded_label'], validate='many_to_one')
    records, native = [], []
    for (order, label), group in frame.groupby(['order', 'blinded_label']):
        rows = group.to_dict('records')
        meta = {k: rows[0][k] for k in ('order', 'blinded_label', 'run_id', 'task_id', 'model')}
        for unit, selected in [('components', rows),
                               ('single_component_calls', [r for _, call in group.groupby('action_index')
                                                           if len(call) == 1 for r in call.to_dict('records')]),
                               ('components_excluding_submission_calls', [r for r in rows
                                if not any(mark in x['command'] for x in rows if x['action_index'] == r['action_index']
                                           for mark in ('COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT', 'MINI_SWE_AGENT_FINAL_OUTPUT'))])]:
            records.append({**meta, 'unit': unit, **score(selected)})
        for action, call in group.groupby('action_index'):
            rs = call.to_dict('records')
            native.append({**meta, 'action_index': int(action), 'component_count': len(rs),
                           'contribution_label': project_native(rs),
                           'component_ids': ';'.join(r['component_id'] for r in rs),
                           'mixed_labels': len({r['contribution_label'] for r in rs}) > 1})
        parent_rows = [r for r in native if r['order'] == order and r['blinded_label'] == label]
        records.append({**meta, 'unit': 'native_strongest_component_sensitivity', **score(parent_rows)})
    pd.DataFrame(records).to_csv(OUT / f'{prefix}scores_by_run.csv', index=False)
    R = pd.DataFrame(records)
    summaries = []
    pairs = []
    for unit, group in R.groupby('unit'):
        eligible = group[group.P_lower.notna()].groupby('order').model.nunique()
        group = group[group.order.isin(eligible[eligible == 2].index)]
        for model, g in group.groupby('model'):
            summaries.append({'unit': unit, 'model': model, 'runs': len(g),
                              'N': int(g.N.sum()), 'D': int(g.D.sum()), 'U': int(g.U.sum()),
                              'P_lower_mean': scalar(g.P_lower.mean()), 'P_upper_mean': scalar(g.P_upper.mean()),
                              'P_lower_median': scalar(g.P_lower.median()), 'P_upper_median': scalar(g.P_upper.median())})
        for order, g in group.groupby('order'):
            a, b = g.set_index('model').loc[G], g.set_index('model').loc[L]
            pairs.append({'order': int(order), 'task_id': a.task_id, 'unit': unit,
                          'N_gemini': int(a.N), 'N_luna': int(b.N),
                          'P_lower_gemini': a.P_lower, 'P_upper_gemini': a.P_upper,
                          'P_lower_luna': b.P_lower, 'P_upper_luna': b.P_upper,
                          'diff_min': a.P_lower - b.P_upper,
                          'diff_max': a.P_upper - b.P_lower,
                          'diff_lower_labels': a.P_lower - b.P_lower})
    pd.DataFrame(summaries).to_csv(OUT / f'{prefix}precision_summary.csv', index=False)
    P = pd.DataFrame(pairs)
    P.to_csv(OUT / f'{prefix}paired_precision.csv', index=False)
    contrast = []
    for unit, g in P.groupby('unit'):
        contrasts = g[['diff_min', 'diff_max']].dropna()
        idx = np.random.default_rng(SEED).integers(0, len(contrasts), size=(5000, len(contrasts)))
        boot = contrasts.values[idx].mean(axis=1)
        contrast.append({'unit': unit, 'pairs': len(g),
                         'mean_difference_min': scalar(g.diff_min.mean()),
                         'mean_difference_max': scalar(g.diff_max.mean()),
                         'median_difference_min': scalar(g.diff_min.median()),
                         'median_difference_max': scalar(g.diff_max.median()),
                         'task_bootstrap_envelope95': [float(np.percentile(boot[:, 0], 2.5)), float(np.percentile(boot[:, 1], 97.5))],
                         'luna_higher_every_uncertain_resolution_pairs': int((g.diff_max < 0).sum()),
                         'gemini_higher_every_uncertain_resolution_pairs': int((g.diff_min > 0).sum()),
                         'note': f'Exploratory {len(g)}-task bootstrap; envelope combines endpoint sampling and unresolved label bounds, not annotation accuracy.'})
    write_json(OUT / f'{prefix}paired_summary.json', contrast)
    (OUT / f'{prefix}component_annotations.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in annotations))
    return frame, R, pd.DataFrame(native), contrast


def evidence_links(frame):
    """Export reviewer evidence claims, without inferring causal/progress edges."""
    links = []
    for r in frame.to_dict('records'):
        for relation, field in [('reviewer_support_reference', 'support_links'), ('reviewer_invalidation_reference', 'invalidation_links')]:
            for target in r.get(field, []):
                links.append({'source': r['component_id'], 'relation': relation, 'target': target,
                              'evidence': r['evidence'], 'status': 'model_coded_reference; direction/causality not inferred'})
        if r['contribution_label'] == 'direct':
            for req in r.get('requirement_ids', []):
                links.append({'source': r['component_id'], 'relation': 'requirement_support',
                              'target': f"reviewer_b:{r['order']:02d}:{req}",
                              'evidence': r['evidence'], 'status': 'model_coded_trace_claim'})
    (OUT / 'evidence_links.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in links))


def verification(frame, prefix=''):
    rows = []
    checks = frame[(frame.role == 'verification') & (frame.execution_status != 'not_executed')]
    for (order, label), g in frame.groupby(['order', 'blinded_label']):
        v = g[g.role == 'verification']
        rows.append({'order': int(order), 'blinded_label': label, 'model': g.model.iloc[0], **score(v.to_dict('records'))})
    pd.DataFrame(rows).to_csv(OUT / f'{prefix}verification_by_run.csv', index=False)
    summary = []
    for model, group in checks.groupby('model'):
        per_run = pd.DataFrame(rows)
        per_run = per_run[per_run.model == model]
        summary.append({'model': model, **score(group.to_dict('records')),
                        'runs_with_checks': int((per_run.N > 0).sum()),
                        'P_lower_run_mean': scalar(per_run.P_lower.mean()),
                        'P_upper_run_mean': scalar(per_run.P_upper.mean())})
    pd.DataFrame(summary).to_csv(OUT / f'{prefix}verification_summary.csv', index=False)
    checks.groupby(['model', 'contribution_label', 'reason'], dropna=False).size().rename('components').reset_index().to_csv(
        OUT / f'{prefix}verification_reasons.csv', index=False)


def agreement(native):
    old = pd.read_json(OLD / 'action_annotations.jsonl', lines=True)
    old = old[old.split == 'evaluation'][['run_id', 'action_index', 'contribution_label', 'evidence_spans',
                                         'contributed_content', 'requirement_ids', 'uncertainty_reason']]
    old = old.rename(columns={'contribution_label': 'legacy_label', 'evidence_spans': 'legacy_evidence',
                              'contributed_content': 'legacy_content', 'requirement_ids': 'legacy_requirement_ids',
                              'uncertainty_reason': 'legacy_uncertainty'})
    compare = native.merge(old, on=['run_id', 'action_index'], validate='one_to_one')
    assert len(compare) == len(native)
    compare['disagrees'] = compare.contribution_label != compare.legacy_label
    compare.to_csv(OUT / 'native_label_comparison.csv', index=False)
    compare[compare.disagrees].to_csv(OUT / 'native_disagreements.csv', index=False)
    stats = kappa(compare.legacy_label.tolist(), compare.contribution_label.tolist())
    stats.update({'unit': 'native calls; reviewer B projected by legacy strongest-component rule',
                  'component_agreement': 'not identifiable: no independently annotated reviewer A components',
                  'human_validation': 'none',
                  'note': 'Blinded model second pass, with revised guide and units. Native-call disagreement mixes attribution, requirement, guide and unit changes; not a clean inter-rater accuracy estimate.'})
    write_json(OUT / 'agreement.json', stats)
    return compare, stats


def baselines(native, prefix=''):
    # Compare diagnoses at the shared native unit. This is construct comparison,
    # not validated predictive accuracy, and no threshold is tuned to labels.
    ops = pd.read_parquet(ROOT / 'data/ops_compact.parquet')
    ops = ops[ops.run_id.isin(native.run_id)].rename(columns={'op_index': 'action_index'})
    b = native.merge(ops[['run_id', 'action_index', 'op_id', 'exact_repeat', 'has_cand_object']],
                     on=['run_id', 'action_index'], validate='one_to_one')
    assert len(b) == len(native)
    wanted = set(b.op_id)
    novelty = {}
    # Latest scale labels override earlier pilot labels. Missing means missing,
    # never implicitly distinct. Preserve LLM/rule provenance.
    for name in ('pilot_v2.jsonl', 'scale_gemini_3_7_flash-run1.jsonl', 'scale_luna-run1.jsonl'):
        for line in (ROOT / 'data/labels' / name).open():
            r = json.loads(line)
            if r.get('op_id') in wanted:
                novelty[r['op_id']] = r
    b['novelty_label'] = b.op_id.map(lambda x: novelty.get(x, {}).get('contribution'))
    b['novelty_provenance'] = b.op_id.map(lambda x: novelty.get(x, {}).get('reasoning'))
    corrected = pd.DataFrame(read_jsonl(OUT / 'corrected_facts.jsonl'))
    corrected = corrected[['run_id', 'action_index', 'exact_repeat', 'has_cand_object']].rename(
        columns={'exact_repeat': 'corrected_exact_repeat', 'has_cand_object': 'corrected_has_cand_object'})
    b = b.merge(corrected, on=['run_id', 'action_index'], validate='one_to_one')
    b['predict_exact_repeat'] = b.corrected_exact_repeat.astype(bool)
    b['predict_target_revisit'] = b.corrected_has_cand_object.astype(bool)
    b['predict_novelty_non_distinct'] = b.novelty_label.map({'non_distinct': True, 'distinct': False})
    b.to_csv(OUT / f'{prefix}baseline_diagnoses.csv', index=False)
    metrics = []
    common = b[b.predict_novelty_non_distinct.notna()]
    for scope, panel in [('available_per_baseline', b), ('common_novelty_coverage', common)]:
        for name in ('predict_exact_repeat', 'predict_target_revisit', 'predict_novelty_non_distinct'):
            cov = panel[panel[name].notna()]
            known = cov[cov.contribution_label != 'uncertain']
            pred = known[name].astype(bool)
            truth = known.contribution_label == 'non_direct'
            tp = int((pred & truth).sum()); fp = int((pred & ~truth).sum())
            fn = int((~pred & truth).sum()); tn = int((~pred & ~truth).sum())
            metrics.append({'scope': scope, 'baseline': name, 'covered_calls': len(cov),
                            'uncertain_reference_calls': int((cov.contribution_label == 'uncertain').sum()),
                            'assessable_calls': len(known), 'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
                            'precision_vs_second_review': tp/(tp+fp) if tp+fp else None,
                            'recall_vs_second_review': tp/(tp+fn) if tp+fn else None,
                            'interpretation': 'Descriptive disagreement with model-coded contribution; different constructs, not ground-truth accuracy.'})
    pd.DataFrame(metrics).to_csv(OUT / f'{prefix}baseline_comparison.csv', index=False)
    # Fixed diagnosis categories; retain every case, not only favorable examples.
    b['diagnosis'] = np.select([
        (b.contribution_label == 'non_direct') & ~b.predict_exact_repeat & ~b.predict_target_revisit,
        (b.contribution_label == 'direct') & b.predict_target_revisit,
        b.mixed_labels,
    ], ['non_direct_without_repeat_or_revisit', 'direct_revisit', 'mixed_call'], default='other')
    b[b.diagnosis != 'other'].to_csv(OUT / f'{prefix}baseline_counterexamples.csv', index=False)
    return b


def figures(R):
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/worktrace-validation-mpl')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for ax, unit, title in zip(axes, ['components', 'native_strongest_component_sensitivity'],
                               ['Reviewed work components', 'Native-call sensitivity']):
        for model, color, offset in [(G, '#2676bd', -.13), (L, '#da7135', .13)]:
            g = R[(R.unit == unit) & (R.model == model)].sort_values('order')
            y = np.arange(len(g)) + offset
            ax.hlines(y, g.P_lower, g.P_upper, color=color, lw=3)
            ax.scatter(g.P_lower, y, s=18, color=color, label=model)
        ax.set(yticks=np.arange(8), yticklabels=[f'{o:02d}' for o in range(3,11)],
               xlabel='Contribution precision bounds', ylabel='Task order', xlim=(-.02, 1.02), title=title)
        ax.grid(axis='x', alpha=.2)
    axes[0].legend(fontsize=7, loc='lower right')
    fig.suptitle('8 matched task pairs • blinded model-coded review • uncertainty retained', fontsize=10)
    for ext in ('png', 'pdf'):
        fig.savefig(OUT / f'fig_reviewed_precision.{ext}', dpi=180)
    plt.close(fig)


def manifest():
    def digest(path):
        h = hashlib.sha256()
        with path.open('rb') as f:
            for chunk in iter(lambda: f.read(1 << 20), b''):
                h.update(chunk)
        return h.hexdigest()
    sources = list((ROOT / 'scripts/precision_validation').glob('*.py')) + [ROOT / 'scripts/precision_validation/run_all.sh']
    sources += [ROOT / s for s in ['worktrace/worktrace/facts.py', 'worktrace/worktrace/versions.py',
                 'worktrace/worktrace/parse/shell.py', 'worktrace/worktrace/parse/pyinline.py',
                 'worktrace/worktrace/loaders/jetbrains.py', 'scripts/one_day_precision/pilot_analysis.py']]
    sources += [OLD / 'action_annotations.jsonl', OLD / 'packets/blinding_key.csv', OLD / 'sample_manifest.csv']
    sources += list((OLD / 'requirements_raw').glob('*.json')) + list((OLD / 'packets').glob('*.md'))
    sources += [ROOT / p for p in ['raw/jetbrains/gemini_3_7_flash-run1.parquet', 'raw/jetbrains/luna-run1.parquet',
                                 'data/ops_compact.parquet', 'data/labels/pilot_v2.jsonl',
                                 'data/labels/scale_gemini_3_7_flash-run1.jsonl', 'data/labels/scale_luna-run1.jsonl']]
    sources += list((OUT / 'reviewer_b').rglob('*.json')) + list((OUT / 'reviewer_c').rglob('*.json')) + list(OUT.glob('evidence_*.json'))
    sources += [OUT / 'components.jsonl', OUT / 'requirements_review.jsonl', OUT / 'annotation_guide.md', OUT / 'role_adjudications.json',
                OUT / 'scoped_links.json', OUT / 'corrected_facts.jsonl', ROOT / 'data/version_graphs_v2.jsonl']
    sources += [OUT / 'annotation_guide_firstpass.md']
    files = {str(p.relative_to(ROOT)): digest(p) for p in sources if p.exists()}
    outputs = {str(p.relative_to(OUT)): digest(p) for p in OUT.iterdir()
               if p.is_file() and p.name not in ('manifest.json', 'run.log')}
    write_json(OUT / 'manifest.json', {'python': platform.python_version(), 'seed': SEED, 'bootstrap_samples': 5000,
        'packages': {p: importlib.metadata.version(p) for p in ['numpy', 'pandas', 'pyarrow', 'pytest', 'matplotlib']},
        'input_and_code_sha256': files,
        'output_sha256': outputs,
        'reproduce': 'bash scripts/precision_validation/run_all.sh',
        'historical_outputs_rebuilt': False, 'new_task_executions': 0, 'new_paid_model_api_jobs': 0})


def main():
    inventory = read_jsonl(OUT / 'components.jsonl')
    key = pd.read_csv(OLD / 'packets/blinding_key.csv').rename(columns={'label': 'blinded_label'})
    key = key[key.order.between(3,10)]
    _, calls = structural(inventory, key)
    missing, annotations, requirements = load_reviews(inventory)
    status = {'inventory_components': len(inventory), 'native_calls': len(calls), 'evaluation_pairs': 8,
              'missing_second_review_tasks': missing, 'human_validation': 'not_performed',
              'failed_run_recall': 'deferred: independent accepted requirements and final states not established',
              'historical_graphs': '16 pilot default graphs rebuilt separately; historical graphs/labels retain pre-repair facts',
              'state_repairs': 'seven audit regressions repaired; general state identity remains conservative heuristic'}
    if missing:
        status['precision'] = 'pending_complete_review; no labels fabricated or copied to components'
        write_json(OUT / 'status.json', status)
        manifest()
        print('Missing review tasks:', missing)
        return
    annotations = apply_role_adjudications(annotations)
    frame, R, native, contrast = precision_tables(annotations, key)
    evidence_links(frame)
    verification(frame)
    compare, stats = agreement(native)
    baselines(native)
    figures(R)
    (OUT / 'reviewer_requirements.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in requirements))
    status.update({'precision': 'computed: one blinded model-coded component pass; provisional',
                   'native_call_second_review_comparison': stats,
                   'component_independent_agreement': 'not_identifiable: legacy first reviewer labeled calls',
                   'requirement_adjudication': 'conflicts documented, no independent executable acceptance check'})
    write_json(OUT / 'status.json', status)
    manifest()
    print(json.dumps(contrast, indent=2))


if __name__ == '__main__':
    main()
