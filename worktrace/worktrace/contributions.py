"""Versioned contribution review; legacy non-direct is not a zero-credit label."""
from collections import Counter
from copy import deepcopy
import hashlib

CONTRIBUTION_LABELS = ('direct', 'indirect', 'no_demonstrated', 'uncertain')
CONTRIBUTION_COLORS = {'direct': '#237A3B', 'indirect': '#2878B5',
                       'no_demonstrated': '#C35E18', 'uncertain': '#777777',
                       'non_direct': '#B6B0A7'}
CONTRIBUTION_NAMES = {'direct': 'Direct', 'indirect': 'Indirect',
                      'no_demonstrated': 'No demonstrated contribution',
                      'uncertain': 'Uncertain', 'non_direct': 'Legacy non-direct (unsplit)'}


def command_sha(component):
    return hashlib.sha256(component['command'].encode()).hexdigest()


def review_sample(components):
    """Up to 5 cases/run: three legacy negatives plus direct/uncertain controls.

    Enriched feasibility sample, not a prevalence or accuracy sample.
    """
    groups = {}
    for c in components:
        groups.setdefault((c['order'], c['blinded_label']), []).append(c)
    selected = []
    for key in sorted(groups):
        group = sorted((c for c in groups[key] if c['execution_status'] != 'not_executed'),
                       key=lambda c: (c['action_index'], c['component_index']))
        chosen = []
        def choose(candidates):
            pick = next((c for c in candidates if c not in chosen), None)
            if pick is not None:
                chosen.append(pick)
        legacy = [c for c in group if c['contribution_label'] == 'non_direct']
        for role in ['exploration', 'verification']:
            choose(c for c in legacy if c['role'] == role)
        while len(chosen) < 3:
            before = len(chosen); choose(legacy)
            if len(chosen) == before:
                break
        for label in ['direct', 'uncertain']:
            choose(c for c in group if c['contribution_label'] == label)
        for c in chosen:
            selected.append(dict(component_id=c['component_id'], source_command_sha256=command_sha(c),
                assessment_status='pending', contribution_label=None, evidence='',
                supporting_component_ids=[], reviewer_type='', reviewer_name=''))
    return selected


def apply_reviews(components, reviews):
    """Join additive reviews, preserving source labels and all candidates.

    Validate identity and observable dependency references, not semantic truth.
    """
    result = deepcopy(components)
    indexed = {c['component_id']: c for c in result}
    if len(indexed) != len(result):
        raise ValueError('Duplicate component IDs')
    for c in result:
        if c['contribution_label'] not in (*CONTRIBUTION_LABELS, 'non_direct'):
            raise ValueError('Unsupported source contribution label')
        c['archived_contribution_label'] = c['contribution_label']
        c['contribution_review_status'] = 'legacy_unresolved' if c['contribution_label'] == 'non_direct' else 'archived'
    seen, accepted = set(), []
    for review in reviews:
        cid = review['component_id']
        if cid in seen or cid not in indexed:
            raise ValueError('Duplicate or unknown review component ID')
        seen.add(cid); c = indexed[cid]
        if review.get('source_command_sha256') != command_sha(c):
            raise ValueError('Review source command hash mismatch')
        if review.get('assessment_status') == 'pending':
            if review.get('contribution_label') is not None:
                raise ValueError('Pending review cannot supply a label')
            continue
        if review.get('assessment_status') != 'reviewed':
            raise ValueError('Review status must be pending or reviewed')
        if review.get('contribution_label') not in CONTRIBUTION_LABELS:
            raise ValueError('Reviewed labels must use the four-label rubric')
        if (review.get('reviewer_type') not in ('model', 'human')
            or not isinstance(review.get('reviewer_name'), str) or not review['reviewer_name'].strip()
            or not isinstance(review.get('evidence'), str) or not review['evidence'].strip()):
            raise ValueError('A reviewed judgment needs evidence and reviewer provenance')
        c.update(contribution_label=review['contribution_label'], contribution_review_status='reviewed',
                 contribution_review=deepcopy(review))
        accepted.append((c, review))
    for c, review in accepted:
        if c['contribution_label'] != 'indirect':
            continue
        links = review.get('supporting_component_ids')
        if not isinstance(links, list) or not links:
            raise ValueError('Indirect contribution needs a later direct-support link')
        for cid in links:
            target = indexed.get(cid)
            if target is None or (target['order'], target['blinded_label']) != (c['order'], c['blinded_label']):
                raise ValueError('Indirect link must stay within its trajectory')
            if (target['action_index'], target['component_index']) <= (c['action_index'], c['component_index']):
                raise ValueError('Indirect support must point to later work')
            if target['contribution_label'] != 'direct' or target['execution_status'] == 'not_executed':
                raise ValueError('Indirect link must identify later performed direct work')
    return result


def contribution_score(components):
    included = [c for c in components if c['execution_status'] != 'not_executed']
    counts = Counter(c['contribution_label'] for c in included)
    n, d, u = len(included), counts['direct'], counts['uncertain']
    return dict(included=n, direct=d, indirect=counts['indirect'],
                no_demonstrated=counts['no_demonstrated'], uncertain=u,
                legacy_non_direct=counts['non_direct'],
                reviewed=sum(c.get('contribution_review_status') == 'reviewed' for c in included),
                lower=d / n if n else None, upper=(d + u) / n if n else None)
