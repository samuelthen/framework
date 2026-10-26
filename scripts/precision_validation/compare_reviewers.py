"""Compare two blinded component passes under common units/requirements.

Disagreements remain exported. Conservative reconciliation is an uncertainty
sensitivity, not manufactured semantic consensus or a human reference.
"""
import json
from collections import Counter

import pandas as pd

from analyze import (OUT, OLD, read_jsonl, load_reviews, apply_role_adjudications,
                     precision_tables, verification, baselines, kappa, write_json, manifest)


def reconcile(b, c):
    """Keep agreement, require both reviewers to establish skipped execution.
    A verification-role disagreement also prevents certain verification credit.
    """
    reasons = []
    if b['contribution_label'] != c['contribution_label']:
        reasons.append('contribution_disagreement')
    if b['execution_status'] != c['execution_status']:
        reasons.append('execution_disagreement')
    status = b['execution_status'] if b['execution_status'] == c['execution_status'] else 'uncertain'
    label = b['contribution_label'] if not reasons else 'uncertain'
    if status == 'uncertain':
        label = 'uncertain'
    role = b['role']
    if b['role'] != c['role'] and 'verification' in (b['role'], c['role']):
        role, label = 'verification', 'uncertain'
        reasons.append('verification_role_disagreement')
    common_requirements = sorted(set(b['requirement_ids']) & set(c['requirement_ids']))
    if label == 'direct' and not common_requirements:
        label = 'uncertain'
        reasons.append('requirement_scope_disagreement')
    verification_fields = {}
    if role == 'verification':
        verification_fields = {
            'property_checked': {'reviewer_b': b.get('property_checked'), 'reviewer_c': c.get('property_checked')},
            'relevant_state_changed': b.get('relevant_state_changed') if b.get('relevant_state_changed') == c.get('relevant_state_changed') else 'uncertain',
            'earlier_check_ids': sorted(set(b.get('earlier_check_ids', [])) | set(c.get('earlier_check_ids', []))),
            'verification_gain': b.get('verification_gain') if b.get('verification_gain') == c.get('verification_gain') else 'uncertain'}
    return {**b, 'role': role, 'contribution_label': label, 'execution_status': status,
            'requirement_ids': common_requirements if label == 'direct' else b['requirement_ids'],
            'reason': ';'.join(reasons) if reasons else b['reason'],
            'uncertainty_reason': ';'.join(reasons) if reasons else b.get('uncertainty_reason'),
            'reviewer_b_label': b['contribution_label'], 'reviewer_c_label': c['contribution_label'],
            'reviewer_b_role': b['role'], 'reviewer_c_role': c['role'],
            'reviewer_b_execution': b['execution_status'], 'reviewer_c_execution': c['execution_status'],
            'reviewer_c_evidence': c['evidence'],
            **verification_fields,
            'review_provenance': 'Conservative cross-review uncertainty sensitivity; not semantic adjudication'}


def main():
    inv = read_jsonl(OUT / 'components.jsonl')
    mb, b, _ = load_reviews(inv, 'reviewer_b')
    mc, c, _ = load_reviews(inv, 'reviewer_c')
    if mb or mc:
        write_json(OUT / 'component_review_status.json', {'missing_b': mb, 'missing_c': mc,
                   'status': 'incomplete; no component agreement or reconciliation claimed'})
        print('Component review pending', mb, mc)
        raise SystemExit(2)
    b = apply_role_adjudications(b)
    bm, cm = {r['component_id']: r for r in b}, {r['component_id']: r for r in c}
    assert bm.keys() == cm.keys()
    frozen = {r['order']: r['requirements'] for r in read_jsonl(OUT / 'reviewer_requirements.jsonl')}
    for order in range(3,11):
        supplied = json.loads((OUT / f'reviewer_c/{order:02d}.json').read_text())['requirements']
        assert supplied == frozen[order], f'reviewer C changed frozen requirements in {order}'
    key = pd.read_csv(OLD / 'packets/blinding_key.csv').rename(columns={'label': 'blinded_label'})
    key = key[key.order.between(3,10)]
    cf, cr, cn, _ = precision_tables(c, key, prefix='reviewer_c_')
    verification(cf, prefix='reviewer_c_')
    contrasts, combined = [], []
    for cid in bm:
        a, d = bm[cid], cm[cid]
        contrasts.append({'component_id': cid, 'order': a['order'], 'blinded_label': a['blinded_label'],
                          'action_index': a['action_index'], 'component_index': a['component_index'],
                          'command': a['command'],
                          'b_label': a['contribution_label'], 'c_label': d['contribution_label'],
                          'b_role': a['role'], 'c_role': d['role'],
                          'b_execution': a['execution_status'], 'c_execution': d['execution_status'],
                          'b_requirement_ids': a['requirement_ids'], 'c_requirement_ids': d['requirement_ids'],
                          'b_evidence': a['evidence'], 'c_evidence': d['evidence'],
                          'b_reason': a['reason'], 'c_reason': d['reason'],
                          'label_disagreement': a['contribution_label'] != d['contribution_label'],
                          'role_disagreement': a['role'] != d['role'],
                          'execution_disagreement': a['execution_status'] != d['execution_status']})
        combined.append(reconcile(a, d))
    D = pd.DataFrame(contrasts)
    D.to_csv(OUT / 'component_reviewer_comparison.csv', index=False)
    D[D.label_disagreement | D.role_disagreement | D.execution_disagreement].to_csv(
        OUT / 'component_disagreements.csv', index=False)
    panels = {'all_candidates': D,
              'executed_by_both': D[(D.b_execution == 'executed') & (D.c_execution == 'executed')],
              'both_assessable_executed': D[(D.b_execution == 'executed') & (D.c_execution == 'executed') &
                                           (D.b_label != 'uncertain') & (D.c_label != 'uncertain')]}
    agreements = {}
    for name, p in panels.items():
        agreements[name] = {**kappa(p.b_label.tolist(), p.c_label.tolist()),
                            'role_agreement': float((p.b_role == p.c_role).mean()) if len(p) else None,
                            'execution_agreement': float((p.b_execution == p.c_execution).mean()) if len(p) else None}
    agreements['limits'] = ['Two blinded Codex model-coded passes, not independent human or independent model-family validation.',
                            'Common units and frozen requirement sheets; unresolved reference conflicts remain.',
                            'Worker groups cover disjoint tasks within each pass. Run style/length can weaken model blinding.',
                            'Five first-pass role-only adjudications are explicit and do not change its contribution labels.']
    write_json(OUT / 'component_agreement.json', agreements)
    gf, gr, gn, pair = precision_tables(combined, key, prefix='reconciled_')
    verification(gf, prefix='reconciled_')
    baselines(gn, prefix='reconciled_')
    status = {'status': 'two complete blinded component passes compared',
              'components_each_pass': len(b), 'contribution_disagreements': int(D.label_disagreement.sum()),
              'role_disagreements': int(D.role_disagreement.sum()),
              'execution_disagreements': int(D.execution_disagreement.sum()),
              'reconciliation': 'Disagreements remain unresolved and widen uncertainty; no manufactured consensus.',
              'reconciled_label_counts': dict(Counter(r['contribution_label'] for r in combined)),
              'included_reconciled_label_counts': dict(Counter(r['contribution_label'] for r in combined
                                                              if r['execution_status'] != 'not_executed')),
              'human_validation': 'not_performed', 'failed_run_recall': 'deferred'}
    write_json(OUT / 'component_review_status.json', status)
    original_status = json.loads((OUT / 'status.json').read_text())
    original_status.update({'component_independent_agreement': agreements,
                            'precision': 'computed: two blinded component passes and conservative cross-review bounds; model-coded',
                            'component_precision_validation': 'two model-coded passes completed; accuracy not established',
                            'conservative_reconciliation': 'reconciled_* files; disagreement-as-uncertainty sensitivity'})
    write_json(OUT / 'status.json', original_status)
    manifest()
    print(json.dumps(status, indent=2))


if __name__ == '__main__':
    main()
