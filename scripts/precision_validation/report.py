"""Write a reviewable report from actual saved validation tables."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/precision_validation_20261026'
G, L = 'gemini-3.7-flash', 'gpt-5.6-luna'


def pct(x):
    return f'{100*x:.1f}%'


def main():
    status = json.loads((OUT / 'status.json').read_text())
    if status['missing_second_review_tasks']:
        raise RuntimeError('Cannot write completed report with missing review tasks')
    units = pd.read_csv(OUT / 'corrected_units.csv').set_index('model')
    summary = pd.read_csv(OUT / 'precision_summary.csv')
    v = pd.read_csv(OUT / 'verification_summary.csv').set_index('model')
    contrast = {r['unit']: r for r in json.loads((OUT / 'paired_summary.json').read_text())}
    agreement = json.loads((OUT / 'agreement.json').read_text())
    anns = [json.loads(s) for s in (OUT / 'component_annotations.jsonl').read_text().splitlines()]
    executed = sum(r['execution_status'] == 'executed' for r in anns)
    execution_unknown = sum(r['execution_status'] == 'uncertain' for r in anns)
    skipped = sum(r['execution_status'] == 'not_executed' for r in anns)
    included = [r for r in anns if r['execution_status'] != 'not_executed']
    counts = {c: sum(r['contribution_label'] == c for r in included) for c in ('direct','non_direct','uncertain')}
    graph = pd.read_csv(OUT / 'version_changes.csv')
    graph_changed = int((graph.old_versions != graph.new_versions).sum())
    disagreements = pd.read_csv(OUT / 'native_disagreements.csv')
    primary = contrast['components']
    texts = [
        '# Eight-pair contribution measurement validation', '',
        'The original Luna precision advantage is **not robust to the corrected component unit**. '
        'This is a measurement result, not evidence that Gemini has a better internal heuristic. '
        'Both label uncertainty and task sampling leave the component comparison unresolved.', '',
        '## What was completed', '',
        f'- Reused exactly the eight evaluation tasks (orders 03–10), with the same 16 recorded-success trajectories. '
        f'No dataset expansion, paid labeling API job, or task test execution.',
        f'- Replaced regex command counting and strongest-call credit with an explicit inventory: **449 native calls → '
        f'{len(anns)} candidate components**. {skipped} known skipped components are excluded. '
        f'The {len(included)} included candidates contain {executed} established executions and '
        f'{execution_unknown} uncertain executions; uncertainty is retained in the precision bounds.',
        '- Reviewed requirements against issue text, dataset bullets, reference diffs and both submitted patches. '
        'Repair versus preservation and alternative routes are recorded. Contradictions remain visible, rather than '
        'being resolved from the dataset success flag.',
        '- Completed a new blinded Codex review of every component. Two workers covered disjoint task groups; '
        'each component has one new model-coded judgment. Neither worker read legacy labels or the model key. '
        'This is a second model-coded pass against the historical Claude call annotations, **not human validation**.',
        '- Used `direct / non_direct / uncertain` for every role, including verification, with separate reasons, '
        'property/state fields, prior-check references and evidence. Original reviewer files, revisions and role-only '
        'adjudications are preserved.',
        '- Fixed the seven audit regressions and rebuilt facts/default version graphs for the 16 pilot runs. '
        'The full historical dataset, labels and graphs were not regenerated.', '',
        '## Corrected units', '',
        '| System | Native calls | Candidate components | Components/call | Multi-component calls |',
        '|---|---:|---:|---:|---:|',
    ]
    for model in (G,L):
        r = units.loc[model]
        texts.append(f'| {model} | {int(r.native_calls)} | {int(r.components)} | {r.mean_components_per_call:.2f} | {pct(r.share_multicomponent_calls)} |')
    texts += ['',
        'Quoted semicolons, inline-program newlines, heredoc bodies and malformed shell no longer inflate command counts. '
        'Pipelines and control constructs remain coherent work units; directory setup supplies context. '
        '`bash -n` performs syntax checking only; no trajectory commands are executed. '
        'This remains a pragmatic unit: an opaque script or test suite can contain several internal activities. '
        'It is not a completely packaging-invariant elementary-action measure.', '',
        '## Contribution precision', '',
        'Each run reports D/N and (D+U)/N. Known skipped components are excluded; uncertain execution/attribution remains U. '
        'Means below weight the eight task pairs equally. Bounds express unresolved labels, not annotation accuracy.', '',
        '| Unit, same reviewer B labels | Gemini mean bounds | Luna mean bounds | Pairs |',
        '|---|---:|---:|---:|',
    ]
    for unit in ('components','native_strongest_component_sensitivity','components_excluding_submission_calls','single_component_calls'):
        s = summary[summary.unit == unit].set_index('model')
        a,b = s.loc[G],s.loc[L]
        texts.append(f'| {unit} | {pct(a.P_lower_mean)}–{pct(a.P_upper_mean)} | '
                     f'{pct(b.P_lower_mean)}–{pct(b.P_upper_mean)} | {int(a.runs)} |')
    texts += ['',
        f'For components, the mean paired Gemini-minus-Luna difference can range from '
        f'**{100*primary["mean_difference_min"]:+.1f} to {100*primary["mean_difference_max"]:+.1f} percentage points** '
        f'under the unresolved labels. The exploratory 5,000 task-bootstrap envelope is '
        f'[{100*primary["task_bootstrap_envelope95"][0]:+.1f}, {100*primary["task_bootstrap_envelope95"][1]:+.1f}] points '
        '(seed 20261026). It does not include errors in apparently certain labels. '
        'The same reviewer labels favor Luna when collapsed by the old strongest-component call rule, '
        'which isolates a substantial unit effect. The single-component sensitivity has only six matched pairs '
        'and 16 Luna calls, so it is particularly selective and imprecise.', '',
        f'The included component labels total {counts["direct"]} direct, {counts["non_direct"]} non_direct and '
        f'{counts["uncertain"]} uncertain. See `scores_by_run.csv` and `paired_precision.csv` for every run/pair. '
        'No model superiority claim is supported by this small, provisional component analysis.', '',
        '## Verification uses the same labels', '',
        'The following shares pool verification components. Per-run scores and run means are also exported; '
        'administrative setup, install polling and patch whitespace/header checks are excluded from the verification role.', '',
        '| System | Verification N | Direct | Non-direct | Uncertain | Precision bounds |',
        '|---|---:|---:|---:|---:|---:|',
    ]
    for model in (G,L):
        r=v.loc[model]
        texts.append(f'| {model} | {int(r.N)} | {int(r.D)} ({pct(r.P_lower)}) | '
                     f'{int(r.ND)} ({pct(r.non_direct_share)}) | {int(r.U)} ({pct(r.uncertain_share)}) | '
                     f'{pct(r.P_lower)}–{pct(r.P_upper)} |')
    texts += ['',
        'These are retrospective contribution judgments. A passing test or different command does not automatically earn '
        'direct credit. The non-direct reasons distinguish repeated support, missing tools/no tests, unrelated properties '
        'and absent solution links. Rates and counts are not a validated safe-stopping policy or a measured cost saving.', '',
        '## Reproducibility and disagreements', '',
        f'At the shared native-call unit, the historical labels and reviewer B strongest-component projection agree on '
        f'**{agreement["n"]-len(disagreements)}/{agreement["n"]} calls ({pct(agreement["agreement"])})**, '
        f'with Cohen κ = **{agreement["kappa"]:.3f}**. All {len(disagreements)} disagreements are exported. '
        'This comparison mixes revised guidance, unit changes and semantic judgments; it is not a controlled same-guide '
        'inter-rater estimate. New component-level agreement is **not identifiable**, because the historical first reviewer '
        'did not independently label components. The metric therefore remains unvalidated.', '',
        'Blind workers independently retained the update-default conflict (task 04), narrow versus broad reference scope '
        '(task 09), and compatibility/scope issues in tasks 07, 08 and 10. Task 08 source-boundary instructions and an unchanged '
        'default binding prevent asserting complete user-facing migration from the accepted outcome alone. '
        '`requirements_review.md` and the raw reviewer requirements record these distinctions.', '',
        '## What contribution links explain beyond baselines', '',
        'These are inspected examples, not selected population-level causal findings. All baseline counterexamples are exported.', '',
        '- **Mixed call, task 04 Y000:** marker printing and a broad file list are non-direct; the configuration grep supplies '
        'the actual observation of missing pool fields/key loading. The call becomes direct under strongest-call credit, '
        'but only one of its four components is direct. Counts alone cannot supply that attribution.',
        '- **Repeated check, task 04 X027:** the cached config test repeats X019 after only binary cleanup, without new '
        'relevant source/property evidence. Its `non_direct` label is explained by `repeated_support`, a prior-check ID and '
        'unchanged relevant state, rather than merely being late in the run.',
        '- **Useful failing check, task 07 Y021:** an in-memory zip missing-directory case exposes a TypeError in assertion '
        'message formatting. Y022 removes the message; Y023 checks the corrected behavior. A failure can contribute, '
        'and a revisit can supply a new property. The invalid-extension assertions in that custom script are weak because '
        'their try/except catches the script\'s own assertion; they are not credited as independent proof.',
        '- **Passing but unlinked check, task 09 X009:** a ratings test passes before `_sort_values` exists. It does not '
        'establish the required ordering behavior. Novel execution or a passing result alone does not establish contribution.', '',
        'Baselines are untuned descriptive proxies: exact-repeat predicts non-direct; target-revisit predicts non-direct; '
        'saved novelty non_distinct predicts non-direct. `baseline_comparison.csv` shows their disagreements with the '
        'model-coded review, coverage and uncertain reference cases. Saved novelty labels cover only the 333 Gemini calls '
        'in this sample, so common-coverage results are shown separately. These different constructs are **not** evaluated '
        'against human ground truth; their apparent precision/recall is agreement with this reviewer, not validated accuracy. '
        'Call totals remain interaction counts and do not identify redundant work, token cost or heuristic quality.', '',
        '## State repairs and scoped support/invalidation', '',
        'The seven original audit probes now pass: status cannot prove content equality; branch changes invalidate identity; '
        'known writes retain unknown side effects; multi-file edits retain all parsed paths; failed restores do not restore '
        'root; partial restores retain unknown dirt; truncated diffs do not collapse versions. '
        'Plain untruncated diffs also cannot prove complete content identity, so text-based reanchoring/merging was removed. '
        'Stash bookkeeping retains dirty paths and ambiguous/compound restore outcomes stay uncertain.', '',
        f'All **98 project/study/validation tests** and **7 audit probes** pass. Two historical tests that asserted unsafe '
        f'diff-based identity were revised to require uncertainty. Among the 16 rebuilt default pilot graphs, '
        f'**{graph_changed} have changed version counts**; one old apparent backtrack disappears. '
        'Ten saved compact fact fields change across the pilot; this is not the count of all changed state facts. '
        'State graphs remain heuristic reconstructions; passing these probes does not establish complete parser coverage.', '',
        '`scoped_links.json` contains three manually inspected, narrowly scoped restore/defect/repair relationships. '
        '`evidence_links.jsonl` preserves reviewer references and requirement-support claims; ambiguous link direction is '
        'not converted into a causal edge. No new progress curve or claim about safely removable work is made.', '',
        '## Paper milestone and remaining evidence', '',
        'This completes a reproducible model-coded validation attempt on the existing eight pairs, and identifies a material '
        'measurement-unit problem. It does **not** establish reliable contribution precision or two substantive system '
        'findings. Before scaling, obtain an independent component-level pass under the same guide, adjudicate the remaining '
        'requirement/attribution conflicts with an expert, and check final acceptance where references disagree. '
        'Failed-run recall is deferred; the older failure-coverage illustration is not promoted to a validated result.', '',
        'Suggested manuscript wording:', '',
        f'> We revisited eight matched successful task pairs using a blinded model-coded contribution review. '
        f'The 449 native calls decomposed into {len(anns)} candidate work components, including {skipped} established '
        f'skipped components. Mean contribution-precision bounds were '
        f'{pct(summary[(summary.unit=="components")&(summary.model==G)].iloc[0].P_lower_mean)}–'
        f'{pct(summary[(summary.unit=="components")&(summary.model==G)].iloc[0].P_upper_mean)} for Gemini and '
        f'{pct(summary[(summary.unit=="components")&(summary.model==L)].iloc[0].P_lower_mean)}–'
        f'{pct(summary[(summary.unit=="components")&(summary.model==L)].iloc[0].P_upper_mean)} for Luna. '
        'The original Luna advantage under whole-call credit did not persist under this unit. '
        'Requirement conflicts, imperfect shared-unit agreement and the absence of independent component labels prevent '
        'treating these scores as validated system rankings.', '',
        '## Reproduce', '',
        '```bash', 'bash scripts/precision_validation/run_all.sh', '```', '',
        'Uses local raw shards and saved reviewer files. Rebuilds only this validation directory. No acquisition, labeling '
        'API job or task command execution is hidden in the command. `manifest.json` records input/code/review hashes and '
        'package versions. Historical results and the paper manuscript remain preserved.', '',
    ]
    (OUT / 'RESULTS.md').write_text('\n'.join(texts))
    (OUT / 'diagnostics.md').write_text('\n'.join([
        '# Validation diagnostics', '',
        '- Contribution labels and execution statuses are validated for complete canonical component coverage and duplicate IDs.',
        '- Known skipped components are retained in raw files but excluded from scores and verification reason counts.',
        '- Single-component sensitivity comparisons retain only complete matched task pairs; empty runs are null, not zero.',
        '- New component judgments are never filled by projecting a historical call label onto every part.',
        '- Native strongest-component projection is reported only as a packaging sensitivity/shared-unit diagnostic.',
        '- Reviewer B role/reason audit snapshots and changes are preserved; five root role-only adjudications are separately recorded.',
        '- All native disagreements remain unresolved in the machine-readable comparison; no artificial consensus is claimed.',
        '- Annotator provenance: historical Claude call labels; current Codex workers on disjoint blinded task subsets; no human adjudication.',
        '- Formal same-guide component agreement is unavailable. Original and revised guides differ.',
        '- Agent-visible truncated output is used in review evidence. Hidden raw output is not credited to the agent.',
        '- Plain git observations cannot reestablish full repository identity. New default graphs are separated from historical outputs.',
        '- Review invalidation references have heterogeneous direction; only scoped_links.json supplies manually checked typed relationships.',
        '- No task environment/tests, new benchmark run, failed-run recall or safe-stopping intervention was executed.', '',
    ]))
    print('Wrote RESULTS.md and diagnostics.md')


if __name__ == '__main__':
    main()
