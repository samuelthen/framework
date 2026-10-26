# Figure locations and paper placement

The earlier figures were not deleted. The previous rewrite omitted the patch-size benchmark from the paper. The current revision restores it and also restores a supporting return plot.

| Earlier figure or analysis | Original location | Current paper placement |
| --- | --- | --- |
| Difficulty / reference-patch size | [Original figure](../../figures/difficulty.png) | Section 3.3, redrawn as `images/patch_size_profiles.pdf` |
| Across-model amount and success | [Original figure](../../figures/benchmark_by_model.png) | Section 3.1 and model benchmark table |
| Across-harness patch-size results | [Saved table](../../results/v2/task5/table2_gold_patch_bins.csv) | Section 3.3, second row of the restored patch-size figure |
| Version progression patterns | [Saved figures](../../figures/v2/) | Section 5.1, four-version examples and paired verification comparison |
| Return after intervening targets | [Original figure](../../figures/return_after_k.png) | Appendix A, rebuilt from the saved v2 return table |
| Signature contribution mix | [Original figure](../../figures/signatures.png) | Original retained. No main finding depends on the older image. |
| Repetition and semantic labels | [Original figure](../../figures/repeats_vs_labels.png) | Pilot label evidence summarized in Section 5.2 and Appendix A |
| Individual operation timelines | [Original figures](../../figures/traces/) | Original retained for case inspection. |

The new harness patch-size figure averages per-run rates, consistent with the current paper. The older saved harness quartile table used pooled operation rates. These denominators can give different values.

Reference-patch size is a proxy for task demands. The saved success-defined difficulty bins remain available in `results/v2/benchmark/table2_difficulty.csv`. Their success trends follow from the grouping rule, so they should not be presented as independent evidence that difficulty causes lower success.

The return plot uses v2 labels and shows the saved uncertainty intervals. Small group sizes and an unestimable interval remain visible limitations. Restoring the graph does not promote it to a main phenomenon.
