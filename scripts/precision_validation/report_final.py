"""Final report for two complete blinded component passes, without gold claims."""
import json
import re
from collections import Counter

import pandas as pd

from analyze import OUT, G, L
from report import pct


def load(prefix, name):
    return pd.read_csv(OUT / f'{prefix}{name}.csv')


def figures():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), constrained_layout=True)
    for ax, prefix, title in zip(axes, ['', 'reviewer_c_', 'reconciled_'],
                                ['Blinded pass B', 'Blinded pass C', 'Disagreements retained as uncertainty']):
        R = load(prefix, 'scores_by_run')
        for model, color, offset in [(G, '#2676bd', -.13), (L, '#da7135', .13)]:
            r = R[(R.unit == 'components') & (R.model == model)].sort_values('order')
            y = r.order.values - 3 + offset
            ax.hlines(y, r.P_lower, r.P_upper, color=color, lw=3)
            ax.scatter(r.P_lower, y, color=color, s=18, label=model)
        ax.set(xlim=(-.02, 1.02), yticks=range(8), yticklabels=[f'{x:02d}' for x in range(3,11)],
               title=title, xlabel='Contribution precision bounds', ylabel='Task order')
        ax.grid(axis='x', alpha=.2)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, fontsize=8, loc='outside lower center', ncols=2)
    fig.suptitle('8 matched pairs • same candidate units • two model-coded passes • no human reference', fontsize=11)
    for ext in ('png','pdf'):
        fig.savefig(OUT / f'fig_component_validation.{ext}', dpi=180)
    plt.close(fig)


def main():
    s = json.loads((OUT / 'component_review_status.json').read_text())
    assert s['status'] == 'two complete blinded component passes compared'
    agreement = json.loads((OUT / 'component_agreement.json').read_text())
    legacy = json.loads((OUT / 'agreement.json').read_text())
    b = {r['component_id']: r for r in map(json.loads, (OUT / 'component_annotations.jsonl').read_text().splitlines())}
    c = {r['component_id']: r for r in map(json.loads, (OUT / 'reviewer_c_component_annotations.jsonl').read_text().splitlines())}
    combined = list(map(json.loads, (OUT / 'reconciled_component_annotations.jsonl').read_text().splitlines()))
    units = load('', 'corrected_units').set_index('model')
    statuses = Counter(r['execution_status'] for r in combined)
    primary = next(r for r in json.loads((OUT / 'reconciled_paired_summary.json').read_text()) if r['unit']=='components')
    tests = re.search(r'(\d+) passed', (OUT / 'test_results.txt').read_text()).group(1)
    label_counts = Counter(r['contribution_label'] for r in combined if r['execution_status']!='not_executed')
    text = ['# Eight-pair contribution measurement validation', '',
        '**The original model ranking is not established by this validation.** Correcting the action unit materially '
        'changes the comparison, and independent component judgments still disagree. The outputs now expose both '
        'sources of uncertainty rather than presenting a single precision ranking.', '',
        '## Work completed', '',
        '- Reused the same eight evaluation tasks (orders 03–10), 16 recorded-success trajectories. No larger dataset '
        'or new graph design was added.',
        '- Corrected command counting and decomposed compound calls without spreading whole-call credit to every part.',
        '- Reviewed requirements, alternative implementations, existing behavior to preserve, and conflicting references.',
        '- Completed two blinded component annotation passes, B and C, on the same canonical inventory. Each pass '
        'used two Codex workers covering disjoint task groups. C used the frozen reviewed requirement sheets; neither '
        'pass saw the other contribution labels or the model key. Original Claude call labels remain preserved.',
        '- Recomputed component/native sensitivities, contribution and verification precision, paired differences, '
        'reviewer agreement and baseline diagnoses. All roles use `direct / non_direct / uncertain`; reasons are separate.',
        f'- Fixed the seven audit regressions. **{tests} project/study/validation tests and all 7 audit probes pass.** '
        'Rebuilt only the 16 pilot default graphs/facts into a separate directory.', '',
        'All annotation is model-coded. These are independently blinded worker passes, not independent human or '
        'independent model-family validation. No task environment or patch test suite was re-executed.', '',
        '## Units and counting', '',
        '| System | Native calls | Candidate components | Mean components/call | Multi-component calls |',
        '|---|---:|---:|---:|---:|']
    for model in (G,L):
        r=units.loc[model]
        text.append(f'| {model} | {int(r.native_calls)} | {int(r.components)} | {r.mean_components_per_call:.2f} | {pct(r.share_multicomponent_calls)} |')
    text += ['',
        'The original regex counted separators inside quoted programs. The new decomposition respects quotes, heredocs '
        'and substitutions, groups pipelines/control flow, attaches directory context, and keeps malformed shell as one '
        'opaque attempted action. `bash -n` checks syntax only and does not execute commands. Inline programs/test suites '
        'can still contain several activities; these units are pragmatic, not fully packaging invariant.', '',
        f'Each pass covers **{len(b)} candidate components**, from 449 native calls. Reviewers separately judge execution. '
        f'Conservative reconciliation excludes a candidate only when both mark it not executed: '
        f'{statuses["not_executed"]} excluded, {statuses["executed"]} established executions, '
        f'{statuses["uncertain"]} uncertain executions. Unknown execution retains contribution uncertainty; it is not '
        'silently counted as certainly productive or omitted.', '',
        '## Contribution precision', '',
        'For each run, lower = D/N and upper = (D+U)/N. The table averages run bounds over the eight matched tasks. '
        'These bounds concern unresolved labels/execution, not errors in apparently certain judgments.', '',
        '| Annotation version | Gemini mean bounds | Luna mean bounds |', '|---|---:|---:|']
    for prefix,name in [('', 'Pass B'), ('reviewer_c_', 'Pass C'), ('reconciled_', 'Conservative cross-review bounds')]:
        r=load(prefix,'precision_summary');r=r[r.unit=='components'].set_index('model')
        x,y=r.loc[G],r.loc[L]
        text.append(f'| {name} | {pct(x.P_lower_mean)}–{pct(x.P_upper_mean)} | {pct(y.P_lower_mean)}–{pct(y.P_upper_mean)} |')
    text += ['',
        f'The conservative mean paired Gemini-minus-Luna difference ranges from '
        f'**{100*primary["mean_difference_min"]:+.1f} to {100*primary["mean_difference_max"]:+.1f} percentage points** '
        f'under unresolved judgments. Its exploratory task-bootstrap envelope is '
        f'[{100*primary["task_bootstrap_envelope95"][0]:+.1f}, {100*primary["task_bootstrap_envelope95"][1]:+.1f}] points '
        '(5,000 task resamples; seed 20261026). Eight-task sampling and annotation accuracy remain separate limitations.', '',
        'Reconciliation preserves equal judgments; conflicting contribution/execution judgments become uncertain. '
        'Verification-role disagreement also becomes uncertain and is included in the candidate verification denominator. '
        'Certain direct agreement requires at least one shared requirement ID. This is a conservative sensitivity, '
        '**not semantic consensus or a gold reference**. Individual passes and every disagreement remain available.', '',
        f'The reconciled included labels are {label_counts["direct"]} direct, '
        f'{label_counts["non_direct"]} non_direct and {label_counts["uncertain"]} uncertain.', '',
        'Unit choice can be isolated within pass B, holding its component judgments fixed:', '',
        '| Unit | Gemini mean bounds | Luna mean bounds | Pairs |', '|---|---:|---:|---:|']
    r=load('', 'precision_summary')
    for unit in ('native_strongest_component_sensitivity','components','components_excluding_submission_calls','single_component_calls'):
        g=r[r.unit==unit].set_index('model');x,y=g.loc[G],g.loc[L]
        text.append(f'| {unit} | {pct(x.P_lower_mean)}–{pct(x.P_upper_mean)} | {pct(y.P_lower_mean)}–{pct(y.P_upper_mean)} | {int(x.runs)} |')
    text += ['',
        'The native strongest-component rule favors bundling. It is retained only as a sensitivity, not used to assign '
        'component labels. The single-component analysis has only six complete pairs and 16 Luna calls, so it is '
        'selective and imprecise. Neither component counts nor precision alone establish time/token savings or '
        'the quality of an internal search heuristic.', '',
        '## Reproducibility', '',
        '| Comparison panel | Components | Label agreement | Cohen κ | Role agreement |', '|---|---:|---:|---:|---:|']
    for key in ('all_candidates','executed_by_both','both_assessable_executed'):
        a=agreement[key]
        text.append(f'| {key} | {a["n"]} | {pct(a["agreement"])} | {a["kappa"]:.3f} | {pct(a["role_agreement"])} |')
    text += ['',
        f'There are {s["contribution_disagreements"]} contribution disagreements, {s["role_disagreements"]} role '
        f'disagreements and {s["execution_disagreements"]} execution disagreements; these categories overlap. '
        '`component_disagreements.csv` includes both requirements/evidence/reasons. No uncertainty is dropped to inflate agreement.', '',
        f'For historical context only, the original Claude call labels and pass B projected to native calls agree '
        f'{pct(legacy["agreement"])} (κ {legacy["kappa"]:.3f}). That comparison mixes guide and unit changes and is '
        'not a clean component reproducibility estimate. The two component passes are the relevant new check, '
        'but shared model/requirement/parser biases can still survive their agreement.', '',
        '## Verification precision', '',
        'Verification has exactly the same contribution labels. The following table pools verification candidates; '
        'per-run means are also exported. Reasons distinguish repeated support, missing/no-result checks, unrelated '
        'properties, defects used in repair and justified additional confidence.', '',
        '| Version/system | N | Direct | Non-direct | Uncertain | Precision bounds |', '|---|---:|---:|---:|---:|---:|']
    for prefix,name in [('', 'B'),('reviewer_c_','C'),('reconciled_','Cross-review')]:
        v=load(prefix,'verification_summary').set_index('model')
        for model in (G,L):
            x=v.loc[model]
            text.append(f'| {name}: {model} | {int(x.N)} | {int(x.D)} ({pct(x.P_lower)}) | '
                        f'{int(x.ND)} ({pct(x.non_direct_share)}) | {int(x.U)} ({pct(x.uncertain_share)}) | '
                        f'{pct(x.P_lower)}–{pct(x.P_upper)} |')
    text += ['',
        'Passing or issuing a different command never automatically establishes direct contribution. Role disputes are '
        'retained, because distinguishing task verification from administration affects this denominator. '
        'These rates do not show that suppressing checks preserves correctness; no stopping intervention was performed.', '',
        '## Requirements and alternative fixes', '',
        '- **03:** cancellation/deadline/auth propagation are repairs; unrelated behavior is preservation. '
        'Context fallback and pre-existing status handling require scoped evidence, not blanket accepted-outcome credit.',
        '- **04:** explicit configuration-key loading is clear. The absent-update-key false requirement conflicts with '
        'preserving Default() true in the issue/reference. Both branches remain explicit and disputed.',
        '- **05:** lifecycle-to-liveness mapping and its single update path are repairs; existing initialization and '
        'change-only emissions are preservation. Missing or failed test execution is not proof of that behavior.',
        '- **06:** distinguish enum/schema changes from each evaluation outcome. Broad ErrNotFound handling can '
        'misclassify later store errors; generated-file changes alone do not prove outcome semantics.',
        '- **07:** filesystem/zip behavior and cache keys matter, not one exact implementation. Python compatibility '
        'and the missing-directory assertion-message failure are separately recorded.',
        '- **08:** tab command/provider/docs migration is repair; tab selection/count/window logic already exists. '
        'Source-boundary instructions and an unchanged configuration binding leave a scope conflict.',
        '- **09:** require the pure `_sort_values` helper, not the broad unrelated observations migration in the reference.',
        '- **10:** per-server settings/direct map use are repairs; Status filtering and presence signaling already exist. '
        'Global override precedence and legacy pointer compatibility require separate treatment.', '',
        'These are reviewed model-coded requirements. Conflicts unsupported by available sources are not invented away. '
        'Recorded benchmark success is not independent verification that every listed requirement is satisfied.', '',
        '## Baseline diagnoses and inspected examples', '',
        'Exact-repeat, target-revisit and saved novelty labels are compared at the shared native unit. '
        '`reconciled_baseline_comparison.csv` reports coverage and uncertain cases separately; the novelty baseline '
        'covers only the 333 Gemini calls here. Common-coverage results are separate. Apparent precision/recall is '
        'agreement with model-coded contribution, not accuracy against human truth.', '',
        'Concrete inspected cases (B/C judgments are shown so disagreement is visible):', '',
        '| Component | Diagnosis from trace | B | C |', '|---|---|---|---|']
    cases=[('04:Y000.c3','Configuration grep supplies missing-field/key observation; markers/file inventory in same call do not.'),
           ('04:X027.c0','Cached config suite repeats X019 after binary cleanup, with no new relevant code/property.'),
           ('07:Y021.c0','Zip missing-directory check exposes assertion-message TypeError and motivates Y022 repair.'),
           ('09:X009.c0','Passing ratings test predates the sorting helper and does not check required ordering.')]
    for cid,why in cases:
        text.append(f'| {cid} | {why} | {b[cid]["contribution_label"]} | {c[cid]["contribution_label"]} |')
    text += ['',
        'The four examples illustrate attribution/property/state diagnoses unavailable from count totals alone; they '
        'are not a population-level claim of framework accuracy. Every baseline counterexample is exported. '
        'Different commands and revisits can contribute; passing novelty can still be unrelated.', '',
        '## State repairs and evidence links', '',
        'Repairs preserve unknown effects alongside known paths, invalidate state on branch changes, track multiple '
        'parsed mutation targets, reject failed/ambiguous restores, retain unknown dirt after partial restores, and '
        'retain stash dirty paths. Status and plain diff text cannot prove complete repository identity, including '
        'staged/untracked/truncated content, so text-based reanchoring/merging was removed.', '',
        'Among the 16 rebuilt default pilot graphs, two version counts change and one old apparent backtrack disappears. '
        'Ten compact fields differ; this is not a count of all changed state facts. The remaining historical corpus '
        'and old labels retain pre-repair facts. Graphs remain heuristic reconstructions even after the seven probes pass.', '',
        '`scoped_links.json` records three manually inspected restore/defect/repair relationships with specific scope. '
        '`evidence_links.jsonl` preserves reviewer references without inventing their causal direction. '
        'No new progress curve or claim about safely removable actions is asserted.', '',
        '## What the paper can say now', '',
        'The existing pilot is now a reproducible validation attempt with corrected units, reviewed requirements, '
        'two blinded component passes, disagreement bounds and baseline examples. The useful result is that unit choice '
        'and attribution reliability materially affect a system comparison. Do not reuse the original precision ranking '
        'as a validated measure of heuristic quality.', '',
        'Before scaling or claiming two substantive model/harness findings, resolve the most consequential disputed '
        'requirements/labels with an independent expert and acceptance evidence. Human validation is still missing. '
        'Failed-run recall is deferred until requirements and assessable final states pass that gate; no dataset-wide '
        'recall or safe-stopping result is promised.', '',
        'Suggested manuscript paragraph:', '',
        f'> We re-examined eight matched successful task pairs using 769 candidate work components from 449 native calls. '
        f'Two blinded model-coded annotation passes agreed on {pct(agreement["all_candidates"]["agreement"])} of '
        f'component contribution labels (Cohen κ={agreement["all_candidates"]["kappa"]:.3f}). '
        'Holding one pass\'s judgments fixed, replacing strongest-component call credit with separate component credit '
        'changed the model comparison. Conservative cross-review bounds did not establish a model ranking. '
        'The results support treating action granularity and attribution reliability as measurement requirements; '
        'they do not establish human-validated efficiency or safely removable verification.', '',
        '## Reproduce', '', '```bash', 'bash scripts/precision_validation/run_all.sh', '```', '',
        'Uses local raw shards and saved reviewer files. No downloads, labeling API jobs or task-command execution '
        'are hidden in the command. Historical results and manuscript are preserved. See `manifest.json`, `run.log`, '
        '`status.json`, `component_review_status.json`, `audit_checks.txt` and `test_results.txt`.', '']
    (OUT/'RESULTS.md').write_text('\n'.join(text))
    (OUT/'diagnostics.md').write_text('\n'.join([
        '# Validation diagnostics', '',
        '- Complete duplicate-free canonical coverage validated independently for both component passes.',
        '- Known skipped components excluded; unproven execution becomes uncertain, not silently omitted.',
        '- All roles share one contribution-label enum. Verification property/state/reason fields are retained.',
        '- C saw frozen requirements but no B/legacy component judgments; no model key was supplied to either pass.',
        '- Role audit snapshots and five root role-only adjudications preserve original B contribution labels.',
        '- No majority-vote adjudication: all disagreements are exported; conservative bounds retain uncertainty.',
        '- Verification-role disputes enter the verification candidate union as uncertain; denominator effects are explicit.',
        '- Empty single-component sensitivities are null; paired summaries keep only complete matched task pairs.',
        '- No contribution labels are generated automatically from command novelty, revisit flags, success or patch overlap.',
        '- Graph fixes do not reconstruct complete file states or independently verify final task patches.',
        '- Requirement conflicts, two same-model passes, residual opaque units and eight-task selection limit validity.',
        '- No new task execution, benchmark scaling, failure recall or stopping experiment was performed.', '']))
    figures()
    print('Wrote final two-pass RESULTS.md, diagnostics.md and scientific figures')


if __name__=='__main__':
    main()
