# One-hour framework smoke study

Real archived examples and an executable reduced sample. This is development evidence, not a model ranking.

Selection: first two frozen evaluation orders [3, 4]; four runs. No selection by observed redundancy.

| Task order | Model | Components | Native calls | Run input | Cached input | Run output |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 3 | gemini-3.7-flash | 54 | 53 | 3,448,740 | 3,200,762 | 51,678 |
| 3 | gpt-5.6-luna | 30 | 10 | 100,650 | 87,377 | 2,069 |
| 4 | gemini-3.7-flash | 48 | 31 | 951,973 | 760,343 | 18,961 |
| 4 | gpt-5.6-luna | 43 | 15 | 137,056 | 124,650 | 3,025 |

Input/cache/output are separate archived run fields. These amounts do not attribute cost to roles or components.

## Role contribution bounds

Known unexecuted candidates are excluded; uncertain execution remains as in the archived convention. Bounds reflect uncertain labels, not confidence intervals.

Legacy non-direct remains unsplit between indirect and no demonstrated contribution. Unreviewed labels retain archived provenance; these are partial-review bounds, not a fully validated four-label result.

| Task | Model | Role | Included | Direct | Indirect | No demonstrated | Uncertain | Legacy unsplit | Reviewed | Direct precision bounds |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 3 | gemini-3.7-flash | exploration | 26 | 16 | 0 | 1 | 6 | 3 | 3 | 61.5%–84.6% |
| 3 | gemini-3.7-flash | verification | 14 | 6 | 0 | 0 | 5 | 3 | 1 | 42.9%–78.6% |
| 3 | gpt-5.6-luna | exploration | 8 | 6 | 0 | 1 | 0 | 1 | 2 | 75.0%–75.0% |
| 3 | gpt-5.6-luna | verification | 4 | 2 | 0 | 0 | 2 | 0 | 1 | 50.0%–100.0% |
| 4 | gemini-3.7-flash | exploration | 19 | 7 | 1 | 2 | 1 | 8 | 4 | 36.8%–42.1% |
| 4 | gemini-3.7-flash | verification | 12 | 3 | 0 | 1 | 5 | 3 | 1 | 25.0%–66.7% |
| 4 | gpt-5.6-luna | exploration | 12 | 7 | 0 | 1 | 0 | 4 | 2 | 58.3%–58.3% |
| 4 | gpt-5.6-luna | verification | 6 | 5 | 0 | 0 | 1 | 0 | 1 | 83.3%–100.0% |

Review packet: 20 cases prepared; 20 judgments completed.
The enriched reviewed subset is reported separately in reviewed_subset_by_run.csv. It is not a population estimate.

## Trajectory examples

![Task 3 inferred progression](task_03_progression.png)

![Task 4 inferred progression](task_04_progression.png)

## Component examples

Executed examples per available label/run, preferring bounded reviewed cases and then verification. Labels not observed are not fabricated. Legacy non-direct is explicitly unsplit. Qualitative illustrations, not prevalence estimates. Model reviews are not human ground truth.

### 03:X001.c0 — gemini-3.7-flash, direct

```bash
grep -rn "codes.Internal" . | head -50
```

Archived reason: used_specific_observation

Archived evidence: 03:X001.c0 `grep -rn "codes.Internal" . | head -50`. Search identifies codes.Internal default in grpc/middleware.go and errUnauthenticated conversion in auth/middleware.go; these are the two paths changed in the final patch.

Component usage: input=2274.0, cache=0.0, output=52.0; attribution=single_component_response_association.

Original label: direct. Reviewed label: direct.

Review evidence: X001's visible output identifies middleware.go:57 `code := codes.Internal` and the existing Internal test case. X003/X029 then inspect this mapper; X047's surviving change adds cancellation/deadline cases to that exact switch. The observation identifies the default mapping responsible for incorrectly treating raw context errors as Internal, directly supporting R1/R2. No elided search output is credited.

Supporting components: []. Reviewer: Codex (model identifier unavailable) (model).

### 03:X000.c0 — gemini-3.7-flash, no_demonstrated

```bash
git status
```

Archived reason: administration

Archived evidence: 03:X000.c0 `git status`. Administrative bookkeeping or delivery formatting; no requirement behavior is established or changed.

Component usage: input=1886.0, cache=0.0, output=71.0; attribution=single_component_response_association.

Original label: non_direct. Reviewed label: no_demonstrated.

Review evidence: X000 reports a clean master working tree. It provides repository bookkeeping before X001's source search; the full trajectory and final two-file patch show no repair decision or comparison that uses this initial cleanliness observation. It neither diagnoses context mapping nor verifies the submitted repair. This is no demonstrated task contribution, not a claim that all baseline status checks are useless.

Supporting components: []. Reviewer: Codex (model identifier unavailable) (model).

### 03:X020.c0 — gemini-3.7-flash, uncertain

```bash
go test ./internal/server ./internal/server/audit/... ./internal/server/cache/... ./internal/server/metadata/... ./internal/server/metrics/... ./internal/server/otel/...
```

Archived reason: baseline_no_solution_link

Archived evidence: 03:X020.c0 `go test ./internal/server ./internal/server/audit/... ./internal/server/cache/... ./internal/server/metadata/... ./internal/server/metrics/... ./internal/server/otel/...`. Broad baseline server/storage/cache testing provides no actionable context defect; Redis container failures are environmental and filesystem/auth store passes do not test the new mapping. This is baseline context without a demonstrated regression comparison used by the repair; non-direct is not a claim that an earlier completed check was repeated.

Component usage: input=46099.0, cache=40515.0, output=325.0; attribution=single_component_response_association.

Original label: non_direct. Reviewed label: uncertain.

Review evidence: Before source edits, X020 passes server/audit/memory-cache packages but Redis checks fail because Docker is unavailable. X021's next recorded explanation explicitly uses that diagnosis to select non-Docker tests. That is an observed testing decision, not repeated deterministic verification. However X021 is an unreviewed legacy component, and neither a specific repaired property checked here nor a supported dependency to later directly contributing work is established. Direct versus indirect usefulness remains unresolved; the environment failure is not itself proof of no contribution.

Supporting components: []. Reviewer: Codex (model identifier unavailable) (model).

### 03:X021.c0 — gemini-3.7-flash, non_direct

```bash
go test ./internal/server/auth/method/token ./internal/server/auth/public ./internal/storage/auth/memory ./internal/storage/fs/...
```

Archived reason: baseline_no_solution_link

Archived evidence: 03:X021.c0 `go test ./internal/server/auth/method/token ./internal/server/auth/public ./internal/storage/auth/memory ./internal/storage/fs/...`. Broad baseline server/storage/cache testing provides no actionable context defect; Redis container failures are environmental and filesystem/auth store passes do not test the new mapping. This is baseline context without a demonstrated regression comparison used by the repair; non-direct is not a claim that an earlier completed check was repeated.

Component usage: input=47306.0, cache=44558.0, output=353.0; attribution=single_component_response_association.

### 03:Y008.c0 — gpt-5.6-luna, direct

```bash
cat patch.txt
```

Archived reason: repeated_support

Archived evidence: 03:Y008.c0 `cat patch.txt`. Patch content duplicates Y4 diff with no intervening source edit; confirms serialization but adds no behavioral coverage.

Component usage: input=2608.0, cache=2574.5, output=17.333333333333332; attribution=equal_share_response_allocation.

Original label: non_direct. Reviewed label: direct.

Review evidence: The actual user message requires creating patch.txt, inspecting that file in a separate call, and confirming only intended source changes before submission. Y007 first serializes the worktree diff; Y008.c0 is the first read of that artifact and visibly contains the two source-file headers and context-mapping/auth edits matching the final submission. Y004.c2 inspected a live worktree diff, not the saved submission artifact. This narrow artifact-integrity contribution is direct under H2; it is not additional behavioral coverage and should not be called repeated-support over-verification. Separate header-check components receive no extra credit from this review.

Supporting components: []. Reviewer: Codex (model identifier unavailable) (model).

### 03:Y000.c0 — gpt-5.6-luna, no_demonstrated

```bash
printf '%s\n' '--- files ---'
```

Archived reason: administration

Archived evidence: 03:Y000.c0 `printf '%s\n' '--- files ---'`. Administrative bookkeeping or delivery formatting; no requirement behavior is established or changed.

Component usage: input=963.25, cache=768.5, output=43.75; attribution=equal_share_response_allocation.

Original label: non_direct. Reviewed label: no_demonstrated.

Review evidence: This component prints only `--- files ---` in Y000. It has no repository observation, edit or verification content. Adjacent find and grep components are judged separately; their results do not give the separator contribution credit.

Supporting components: []. Reviewer: Codex (model identifier unavailable) (model).

### 03:Y005.c0 — gpt-5.6-luna, uncertain

```bash
go test ./internal/server/middleware/grpc ./internal/server/auth
```

Archived reason: attribution_or_property_unestablished

Archived evidence: 03:Y005.c0 `go test ./internal/server/middleware/grpc ./internal/server/auth`. Shared call output is empty and execution ended without observable test/check result; downstream chained check execution and tested properties cannot be established.

Component usage: input=5022.333333333333, cache=4441.333333333333, output=41.0; attribution=equal_share_response_allocation.

### 03:Y000.c2 — gpt-5.6-luna, non_direct

```bash
printf '%s\n' '--- context/status references ---'
```

Archived reason: administration

Archived evidence: 03:Y000.c2 `printf '%s\n' '--- context/status references ---'`. Administrative bookkeeping or delivery formatting; no requirement behavior is established or changed.

Component usage: input=963.25, cache=768.5, output=43.75; attribution=equal_share_response_allocation.

### 04:X001.c0 — gemini-3.7-flash, direct

```bash
cat config/config.go
```

Archived reason: used_specific_observation

Archived evidence: 04:X001.c0 `cat config/config.go`. databaseConfig contains only URL/MigrationsPath; Load starts from Default and guards assignments with viper.IsSet; Default.Meta.CheckForUpdates is true. These observations support field additions and expose the explicit absent-false requirement tension.

Component usage: input=3292.0, cache=0.0, output=214.0; attribution=single_component_response_association.

Original label: direct. Reviewed label: direct.

Review evidence: X001 returns the full config.go: databaseConfig has only URL/MigrationsPath; Load starts from Default and reads no pool or meta key; Meta defaults to true. X018 adds the three fields, constants and IsSet-guarded typed getters at those observed locations. This read establishes both repair sites and the existing preservation mechanism. The final Gemini patch still retains true for absent meta: that requirement conflict limits final quality, but does not negate the read's diagnostic content.

Supporting components: []. Reviewer: Codex (model identifier unavailable) (model).

### 04:X003.c0 — gemini-3.7-flash, indirect

```bash
ls -la config/ config/testdata/config/
```

Archived reason: unused_or_repeated_context

Archived evidence: 04:X003.c0 `ls -la config/ config/testdata/config/`. Broad file inventory/directory metadata adds no configuration semantics; focused config reads provide the actual observations.

Component usage: input=1295.1666666666665, cache=0.0, output=54.83333333333333; attribution=equal_share_response_allocation.

Original label: non_direct. Reviewed label: indirect.

Review evidence: The ls component of X003 identifies advanced.yml, default.yml and deprecated.yml in config/testdata/config. In the next actual response, X004 explicitly says `Now that I have a map of the configuration files, my next logical step is to delve into the specific details of the test data` and reads exactly those three fixtures. Those later performed direct components establish configured/default/deprecated inputs relevant to R4. The directory metadata alone does not establish configuration semantics, so the observed navigation dependency earns indirect rather than direct credit. Links retain their archived direct status and are not additional new reviews.

Supporting components: ['04:X004.c0', '04:X004.c2', '04:X004.c4']. Reviewer: Codex (model identifier unavailable) (model).

### 04:X013.c0 — gemini-3.7-flash, no_demonstrated

```bash
go test ./server/... ./errors/... ./rpc/... ./storage/cache/...
```

Archived reason: baseline_no_solution_link

Archived evidence: 04:X013.c0 `go test ./server/... ./errors/... ./rpc/... ./storage/cache/...`. Baseline tests pass existing config/server/RPC/cache behavior; pool/meta missing-key assertions are not present and no baseline defect drives the edit. This is baseline context without a demonstrated regression comparison used by the repair; non-direct is not a claim that an earlier completed check was repeated.

Component usage: input=31587.0, cache=28356.0, output=91.0; attribution=single_component_response_association.

Original label: non_direct. Reviewed label: no_demonstrated.

Review evidence: X013 passes existing server/RPC/cache tests before X018's sole config edit. These results do not exercise the new database fields, optional-key mapping or absent update flag, and the later trace does not use this baseline in a repair decision or an observed before/after preservation comparison for those packages. X019 checks config and X021 builds the executable separately. This is an assessed baseline without demonstrated solution contribution, not repeated support or an environment failure.

Supporting components: []. Reviewer: Codex (model identifier unavailable) (model).

### 04:X011.c0 — gemini-3.7-flash, uncertain

```bash
go test ./...
```

Archived reason: attribution_or_property_unestablished

Archived evidence: 04:X011.c0 `go test ./...`. Broad/database test attempt ends interrupted with no output; no completion, asserted property or actionable defect can be established.

Component usage: input=30549.0, cache=20275.0, output=82.0; attribution=single_component_response_association.

### 04:X022.c1 — gemini-3.7-flash, non_direct

```bash
go run /tmp/verify_test.go
```

Archived reason: unrelated_or_nonbehavioral_check

Archived evidence: 04:X022.c1 `go run /tmp/verify_test.go`. go run rejects *_test.go before executing assertions; this diagnoses a probe invocation issue but supplies no configuration behavior evidence.

Component usage: input=14176.666666666666, cache=13479.0, output=493.66666666666663; attribution=equal_share_response_allocation.

### 04:Y012.c0 — gpt-5.6-luna, direct

```bash
sed -n '1,220p' patch.txt
```

Archived reason: repeated_support

Archived evidence: 04:Y012.c0 `sed -n '1,220p' patch.txt`. Patch text repeats already inspected config diff; no source change since Y6.

Component usage: input=2918.4, cache=2871.6000000000004, output=25.200000000000003; attribution=equal_share_response_allocation.

Original label: non_direct. Reviewed label: direct.

Review evidence: The actual user message explicitly requires inspecting saved patch.txt in a separate command after creation. Y011 creates that artifact; Y012.c0 is its first content read and visibly verifies the single config/config.go patch contains the new pool fields/getters and false update default, matching the final submission. Y006.c2's earlier diff inspected worktree state rather than the serialized artifact. Direct credit is for this specific submission-integrity requirement, not new execution/behavior evidence or automatic credit for every patch reread.

Supporting components: []. Reviewer: Codex (model identifier unavailable) (model).

### 04:Y000.c0 — gpt-5.6-luna, no_demonstrated

```bash
printf '%s\n' '--- files ---'
```

Archived reason: administration

Archived evidence: 04:Y000.c0 `printf '%s\n' '--- files ---'`. Administrative bookkeeping or delivery formatting; no requirement behavior is established or changed.

Component usage: input=953.25, cache=768.5, output=46.25; attribution=equal_share_response_allocation.

Original label: non_direct. Reviewed label: no_demonstrated.

Review evidence: Y000.c0 prints only `--- files ---`. This output labels the display and establishes no requirement-related observation or change. The actual source references come from a separate grep component and are not credited to this separator.

Supporting components: []. Reviewer: Codex (model identifier unavailable) (model).

### 04:Y000.c2 — gpt-5.6-luna, non_direct

```bash
printf '%s\n' '--- config references ---'
```

Archived reason: administration

Archived evidence: 04:Y000.c2 `printf '%s\n' '--- config references ---'`. Administrative bookkeeping or delivery formatting; no requirement behavior is established or changed.

Component usage: input=953.25, cache=768.5, output=46.25; attribution=equal_share_response_allocation.

## Pipeline coverage

- Real source/component/response identity joins: checked on this subset.
- Existing labels preserved; optional four-label review is additive, with reviewer/evidence provenance. No independent human accuracy established.
- Response resource accounting: exported; inspect reconciliation and usage coverage.
- Intermediate complete snapshots and final-test outcomes: not evaluated by this script.
- Actual post-pass expenditure: unresolved until evaluated checkpoints and response usage are joined.
- Synthetic accounting CLI tests pass separately; they cannot fill the missing empirical stages.

Use CODEX_FRAMEWORK_ONE_HOUR.md to finish bounded raw-resource and checkpoint stages on the data machine.
