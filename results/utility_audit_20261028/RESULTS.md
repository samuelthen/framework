# Local trajectory and utility audit — 28 October 2026

The trajectories are downloaded and verified locally. Seven successive critique-and-revision rounds exposed concrete failures in the earlier measurement rules. The resulting framework separates **what an action does, what it establishes, what it changes, and what it costs**.

This is a measurement pilot. It does not yet establish causal action utility, excessive exploration, safe early stopping, cross-harness differences, or a model ranking.

## Data and actual work

- Downloaded the two pinned JetBrains trajectory shards and the pinned SWE-bench Pro reference shard; all three match the archived SHA-256 values. See [download manifest](download_manifest.json).
- Recovered the frozen eight-task selection: **16 runs, 449 native calls, 769 candidate components**. All runs have recorded successful outcomes. This selection cannot explain failure behavior or estimate a population solve rate.
- Recovered all **413 stored response usage records** and linked them to the candidate inventory. Shared-response component expenditure remains an allocation estimate.
- Reconstructed two Luna cases from exact base commits, using a restricted literal-edit interpreter and exact-context patch application. No arbitrary recorded shell program was executed.
- Ran three formatter file checks, eight scoped patched-test executions, four authored requirement-probe executions, and three additional fixed-snapshot Go reruns. Dependencies were prepared separately; the first task-03 setup attempt failed and its log is retained.
- Used a pinned Go 1.20 container, CGO disabled, read-only source mounts and disposable work copies. Test executions had network disabled. This differs from the original benchmark environment.
- Made **zero model API calls, zero agent continuations, and zero original full-benchmark evaluations**.
- Validation: **148 repository tests pass**, including adversarial cache invalidation and restricted reconstruction checks. These software tests do not count as benchmark evidence.

## Seven iterations

| Round | Criticism of the preceding rule | Tested correction | Observed result |
|---|---|---|---|
| 1. Directness | Direct = 1 and Indirect = 0 would rename an annotation as utility. | Audit labels and denominators before scoring. | 756 performed candidates: 233 Direct, 320 legacy non-direct, 203 Uncertain. These are archived model judgments, not causal rewards. |
| 2. Result validity | A verification request can be mistaken for a completed check; compound calls share output. | Inspect native results and observation scope. | Of 159 verification candidates, 27 have a timeout/interruption screen and 75 share a parent output. These are parent-level screens, not 159 separately established outcomes. |
| 3. State identity | An identical command can check a changed implementation. | Compare recurrence against inferred states and prior result completeness. | 22 exact-repeat verification pairs; 18 cross inferred states, 4 share a state. Five follow timeout/missing/empty observations. **Zero historical reuse opportunities are certified.** |
| 4. Executable progress | A command name and a whole-call version hide intermediate states and formatting no-ops. | Reconstruct edit/formatter boundaries; run independent targeted checks. | Task 03 passes the selected test before formatting. Formatting changes one of three checked files; task 04’s formatter changes no bytes. Byte effect and behavior are separate. |
| 5. Evaluation context | A single pass/fail reward can conceal disagreement between tests and written requirements. | Run written-requirement diagnostics separately from patched tests. | Task 04’s submitted patch passes the five authored diagnostics but fails patched `TestLoad/configured`. The reference passes the selected patched tests but fails the absent-flag diagnostic. |
| 6. Reuse overhead | Even valid reuse may cost more than a fresh check. | Measure hashing, key construction and lookup against actual checks. | Patch-artifact check: **0.025 ms fresh / 0.038 ms reuse**. Scoped Go check: **1.471 s fresh / 0.039 s reuse**. These are tool timings, not model-token savings. |
| 7. Cost completeness | Response-level conservation does not guarantee agreement with recorded run totals. | Reconcile each metric and retain unlocalized residuals. | All three token metrics reconcile on 13/16 runs. Three Gemini runs have gaps. Luna response USD reconciles on 8/8 runs; Gemini response USD is unavailable. |

Round 1's pooled directness bounds are 30.8–57.7%, conditional on this selected candidate inventory and the archived judgments. They are neither a redundancy estimate nor an equal-task model comparison. Known unexecuted candidates are excluded from that denominator, but their response-generation expenditure is retained in the cost ledger.

## Executable examples

### Task 03: a second edit can change formatting without improving the tested behavior

Case: `instance_flipt-io__flipt-c12967bc73fdf02054cf3ef8498c05e25f0a18c0`.

| Snapshot | Independent patched `TestErrorUnaryInterceptor` |
|---|---|
| Base | Fail |
| After literal code edit, before formatter | Pass |
| Submitted patch | Pass |
| Reference patch | Pass |

The formatter reorders an import in the gRPC middleware file and leaves the authentication middleware file unchanged. The tested behavior already passes before that formatting step. The graph can mark **first pass of this named scoped check** at the intermediate snapshot; it cannot mark full task completion.

The two original repeated `go test` requests timed out. Our later local pass does not mean that the original agent received passing evidence. Formatting and verification can have operational or evidential value even when this targeted behavior does not change. The measured behavior delta alone cannot justify deleting them.

### Task 04: utility depends on the correctness context

Case: `instance_flipt-io__flipt-5ffba3406a7993d97ced4cc13658bee66150fcca`.

The written requirement says an absent `meta.check_for_updates` key should yield `false`. The reference retains `Default().Meta.CheckForUpdates = true` and only overrides it when the key is set. The submitted patch changes the default to false. Our authored diagnostic checks precisely the absent-key behavior, plus explicit pool values, an explicit false flag, and default/deprecated fixture equality.

| Snapshot | Selected patched tests | Five authored requirement diagnostics |
|---|---|---|
| Base | Build failure: test refers to new fields | 2 pass / 3 fail |
| Before formatter | Fail: `TestLoad/configured` | 5 pass / 0 fail |
| Submitted | Fail: `TestLoad/configured` | 5 pass / 0 fail |
| Reference | Pass | 4 pass / 1 fail: absent flag |

These diagnostic counts describe this probe set; they are not calibrated utility scores. The submitted patch leaves the advanced fixture unchanged, explaining the configured-case mismatch. The reference updates that fixture. The dataset's recorded fail-to-pass list names only `TestValidate`, while its selected test list also names `TestLoad`, `TestServeHTTP` and `TestScheme`. We have not established the original evaluator's exact selection behavior. Do not reinterpret the archived successful status as wrong solely from this broader local check.

The framework should expose the conflict, attach each outcome to its checker and context, and leave a universal correctness score unresolved.

## Reuse experiment: what it measures

The artifact experiment uses the real submitted patch, but exact equality to an intended patch is an authored delivery-integrity check. It does not assess repair correctness. Seven authored perturbation cases test reuse/invalidation; they are not seven observed trajectory events.

The Go experiment repeats one fixed, scoped task-03 check three times and observes the same normalized test outcome set. The reuse path hashes 641 source-tree files and returns the stored, explicitly marked outcome. Timestamps and execution durations are not reproduced. Dependency completeness and the fixed external Go module/build caches remain controlled assumptions; three stable executions do not prove universal determinism.

The median tool-time difference is about **1.432 seconds** for this Go workload and **−0.013 milliseconds** for the cheap artifact workload. Go build caching is enabled; `-count=1` bypasses Go's test-result cache in the fresh path. This is not evidence that a new cache outperforms default Go test-result caching. Agent behavior, downstream context, token spending, production storage and network transfer were not measured. The prototype does not certify any cache hit in the original trajectories.

## Resource correction

The three Gemini response-ledger gaps are:

| Run suffix | Input residual | Cached-input residual | Output residual |
|---|---:|---:|---:|
| `dfe1b31-vnan` | 27,606 | 20,025 | 615 |
| `080478b1d39f` | 93,296 | 88,937 | 31 |
| `1dc8f1b3c171` | 44,976 | 39,599 | 776 |

These are differences between recorded run totals and stored response sums. Their cause is unknown. Cached input is a separate reported metric; do not add these columns into a token total. Do not allocate residuals proportionally to observed actions or call them zero. Role percentages in [round_7/role_expenditure.json](round_7/role_expenditure.json) use **stored response usage** as their named denominator. They do not silently imply 100% coverage of the entire run.

## What the study supports

The pilot supports a more precise measurement procedure: validate execution and observation, reconstruct relevant states, name the property being checked, expose reference conflicts, and include reuse overhead and resource coverage. It also supplies two concrete examples where a naive action score would be misleading.

It does **not** yet show that one model explores more efficiently, that repeated checks are causally unnecessary, or that a proposed suppression policy preserves solve rate. The next decisive experiment is a small paired continuation study at eligible checkpoints: execute fresh versus return valid cached evidence, with a separate bypass arm only when needed. Evaluate all arms independently under a declared correctness context. Report quality changes alongside full model and tool costs. The counterfactual utility fields remain null until that experiment exists.

## Files

- [Revised framework](../../paper/worktrace-draft/FRAMEWORK_UTILITY_REVISION_20261028.md)
- [Machine-readable seven-round summary](summary.json)
- [Outcome and overhead figure](figures/utility_audit.png)
- [Reproduction instructions](REPRODUCE.md)
- Detailed scoped outcomes: [round 4](round_4/summary.json), [round 5](round_5/summary.json), [round 6](round_6/summary.json), [round 7](round_7/summary.json).
