# B.10 go / no-go: status after v2

Criteria 1–2 are **replaced by proxies for now. Human validation (B.8) is still pending.** No result in `results/v2/` is human-validated.

| Criterion | Status | Evidence |
|---|---|---|
| 1. Human–human κ ≥ 0.6 | **Replaced by proxies; human validation still pending.** The 200-item blind sample is in `annotation/pilot.csv`. | Proxy, model–model: primary vs MODEL_2 (glm-5.3-flash), contribution on matched ops κ = 0.70 (candidate-redundant κ = 0.83). Primary self-consistency at T = 0.7: κ = 0.88–0.90. See `task4/SUMMARY.md`. |
| 2. Model–human macro-F1 ≥ 0.7, precision ≥ 0.8 | **Replaced by proxies; human validation still pending.** | Proxy, external labels with a different construct: on CodeTraceBench, candidate-redundant vs `unuseful` gives P 3.5%, R 27.5%. Exact repeat gives P 5.6%, R 33.3%. CodeTraceBench's labels mark mostly planning repeats and empty actions. See `task4/SUMMARY.md` §3. |
| 3. Uncertain share of matched ops ≤ 20% | Pass | 2.2% (v2 labels, `task2/SUMMARY.md`); v1: 4.9% |
| 4. A signature ≥ 10 pts away from exact repeats | Pass | v2: `reread_unchanged` +75 pts [+17, +95]; `self_repeat` +13 pts (`task2/signatures_ci.csv`) |

Model–model agreement and agreement with external labels are not substitutes for the human criteria. The B.10 decision should be revisited once `annotation/pilot.csv` is labelled (`scripts/m5_annotation.py agree`).
