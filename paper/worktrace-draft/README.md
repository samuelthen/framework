# WorkTrace: revised annotated paper

The current draft uses simpler research prose and follows TRACE's main sequence. It includes 16 short red revision notes. The earlier draft is preserved under `revisions/`.

## Read or edit

- `main.tex`: editable two-column paper.
- `../../output/pdf/worktrace_annotated_draft.pdf`: current exported PDF.
- `analyze_saved_data.py`: new local analyses of saved data.
- `build_figures.py`: rebuilds the result figures.
- `check_writing.py`: checks sentence lengths in the abstract and main prose.
- `writing_check.json`: results and limits of the writing check.
- `artifact_manifest.json`: source files, revisions, and hashes.
- `../../results/paper_revision_20261026/`: new analysis tables and their manifest.

## Writing approach

The request for approximately 75% ASD-STE100 is treated as a style adaptation. The draft uses short sentences, direct verbs, one main point per sentence, and consistent terms. It retains research terms, citations, and equations where needed. This is not a certified compliance percentage or a complete approved-word dictionary check.

The official [ASD-STE100 FAQ](https://www.asd-ste100.org/STE_faq.html) supports applying these principles in other writing contexts. The [Issue 9 specification](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf) is the reference for the writing rules. The automated check is a limited aid. It does not assess every rule or guarantee clarity.

## Structure compared with TRACE

The reference is [Zhang et al., ACL 2026](https://aclanthology.org/2026.acl-long.773/). The supplied paper and its main findings were read, including Sections 3–5.3.

| TRACE's sequence | Revised WorkTrace sequence |
| --- | --- |
| 1. Introduction | 1. Introduction: question, framework, two findings |
| 2. Related Work | 2. Related Work |
| 3. Benchmark LLM Overthinking | 3. Benchmark Agent Work: across models and harnesses |
| 4. Analysis Framework of Inner Workings | 4. Framework for Work Progression: four stages |
| 5.1 Thought Progression Patterns | 5.1 Work Progression Patterns: final-version checking and target revisits |
| 5.2 Utility Tracing | 5.2 Trace the Evidence: what checks and revisits establish |
| 5.3 Towards Overthinking Management | 5.3 Proposed Evidence Assessment: records and assessment rules |
| 6. Conclusion | 6. Conclusion |

TRACE's Explorer and Late Landing findings use intermediate answer correctness. The current data does not include intermediate patch correctness. The draft therefore presents work patterns and keeps utility tests prospective. It does not copy those findings into a different domain without evidence.

## New analyses completed

1. **Verification placement:** paired contrasts on the same 892 task–repeat pairs from 418 tasks, under all three saved version rules. Final-root runs are excluded. Resolved/unresolved strata and version-count strata are also exported.
2. **Harness revisits:** matched comparisons on 2,000 tasks. All rates now use means of per-run rates. The analysis includes source-dataset strata and removes the outlier task in a sensitivity check.
3. **Later final-version checks:** removes the first check from each nonempty run before measuring command variety. This avoids counting an automatically new first command as evidence about later checks.

Every new interval uses 5,000 task-bootstrap samples and seed 20261026. These analyses are exploratory and use pre-repair measurements. There were no new agent runs, labels, model calls, or parser fixes.

## Reproduce

For analysis, install `numpy`, `pandas`, and `pyarrow` in a suitable Python environment. Exact package versions appear in the analysis manifest. From this directory:

```bash
python3 analyze_saved_data.py
python3 build_figures.py
python3 check_writing.py
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

Figure generation also needs matplotlib. The writing check needs Pandoc. The TeX project opens and compiles in the Codex LaTeX editor. It uses an academic two-column `article` layout. Move it to the official ACL template after the scientific revision.

The authoring environment used Python 3.12 with numpy 2.3.5, pandas 2.2.3, and pyarrow 26.0.0 for analysis. It used Python 3.13 with matplotlib 3.11.2 for figures, and TeX Live 2026 for local compilation. Additional dependencies were installed only in temporary directories.

## Red comment index

01. Pass audit regressions, rebuild summaries, and compare changed measurements.
02. Register primary paired contrasts and freeze confirmation splits.
03. Compare evidence records with simple baselines and a state-blind ablation.
04. Classify missing results and report inclusion counts and source settings.
05. Measure retrieval recall against unrestricted independent evidence matches.
06. Repair state identity, restores, changed paths, and unknown side effects.
07. Check presence thresholds 0.1, 0.3, and 0.5 with unpruned rates.
08. Label verification property scope, state, and confidence rationale.
09. Normalize target access and test evidence reacquisition.
10. Recover full test commands; mark missing scope uncertain.
11. Build the reference from trace prefixes, without model labels or rule facts.
12. Export the evidence pilot and compare diagnoses with the current graph view.
13. Test action removal and history compression as separate interventions.
14. Update abstract interpretations only after independent evidence assessment.
15. Archive complete inputs and hashes with operation-level provenance.
16. Deliver repaired summaries, adjudication, and baseline-error tables.

## Restored figures and the assessment of excessive work

The patch-size profiles are restored in Section 3.3. The supporting return plot is restored in Appendix A using v2 labels. [FIGURE_INDEX.md](FIGURE_INDEX.md) maps the previous figures to their original locations and current paper sections.

Section 5.3 now specifies a proposed evidence assessment with four fields: work unit, state basis, evidence gain, and task justification. A separate retrospective pass records support and invalidation links. Prefix-only judgments cannot use the final patch or outcome. The proposed metrics are the no-new-property fraction among assessable later checks and the evidence-reacquisition fraction among assessable normalized returns. Unknown scope and support are reported separately.

Appendix D specifies a 30-episode feasibility pilot: six development episodes and 24 task-separated evaluation episodes, balanced across the six system conditions. It defines independent reference annotation, controlled contrasts, baseline comparisons, a state-blind ablation, and required outputs. These are plans, not completed experiments. CoTJudger and CAID/PACE are cited in the paper. The broad assessment discussion was shortened. All five figure blocks and the numerical finding text are preserved.
