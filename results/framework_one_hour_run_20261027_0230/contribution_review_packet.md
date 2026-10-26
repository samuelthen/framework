# Four-label review packet

Up to 20 enriched cases: three legacy non-direct cases plus direct/uncertain controls per run.
Read full requirements, final patch and trajectory first. Do not copy the old judgment as evidence.
Complete a COPY of contribution_review_template.jsonl; preserve the pending template.

Allowed labels: direct, indirect, no_demonstrated, uncertain. Indirect requires evidence that the result guided a later performed direct component, with its ID.
No demonstrated means no supported observed contribution, not proof of zero causal effect. Missing context stays uncertain.

## 03:X022.c0 — exploration / archived non_direct

Read full source: results/one_day_precision_20261026/packets/03_instance_flipt-io__flipt-c12967bc73fdf02054cf3ef8498c05e25f0a18c0.md

```bash
cat internal/server/auth/http.go
```

## 03:X020.c0 — verification / archived non_direct

Read full source: results/one_day_precision_20261026/packets/03_instance_flipt-io__flipt-c12967bc73fdf02054cf3ef8498c05e25f0a18c0.md

```bash
go test ./internal/server ./internal/server/audit/... ./internal/server/cache/... ./internal/server/metadata/... ./internal/server/metrics/... ./internal/server/otel/...
```

## 03:X000.c0 — administration / archived non_direct

Read full source: results/one_day_precision_20261026/packets/03_instance_flipt-io__flipt-c12967bc73fdf02054cf3ef8498c05e25f0a18c0.md

```bash
git status
```

## 03:X001.c0 — exploration / archived direct

Read full source: results/one_day_precision_20261026/packets/03_instance_flipt-io__flipt-c12967bc73fdf02054cf3ef8498c05e25f0a18c0.md

```bash
grep -rn "codes.Internal" . | head -50
```

## 03:X011.c0 — exploration / archived uncertain

Read full source: results/one_day_precision_20261026/packets/03_instance_flipt-io__flipt-c12967bc73fdf02054cf3ef8498c05e25f0a18c0.md

```bash
grep -rn "context.Canceled\|context.DeadlineExceeded" .
```

## 03:Y000.c1 — exploration / archived non_direct

Read full source: results/one_day_precision_20261026/packets/03_instance_flipt-io__flipt-c12967bc73fdf02054cf3ef8498c05e25f0a18c0.md

```bash
find . -maxdepth 3 -type f | head -80
```

## 03:Y008.c0 — verification / archived non_direct

Read full source: results/one_day_precision_20261026/packets/03_instance_flipt-io__flipt-c12967bc73fdf02054cf3ef8498c05e25f0a18c0.md

```bash
cat patch.txt
```

## 03:Y000.c0 — administration / archived non_direct

Read full source: results/one_day_precision_20261026/packets/03_instance_flipt-io__flipt-c12967bc73fdf02054cf3ef8498c05e25f0a18c0.md

```bash
printf '%s\n' '--- files ---'
```

## 03:Y000.c3 — exploration / archived direct

Read full source: results/one_day_precision_20261026/packets/03_instance_flipt-io__flipt-c12967bc73fdf02054cf3ef8498c05e25f0a18c0.md

```bash
grep -RInE 'Unauthenticated|DeadlineExceeded|context\.Canceled|status\.Code|ToStatus|FromError' --include='*.go' . | head -240
```

## 03:Y004.c1 — edit / archived uncertain

Read full source: results/one_day_precision_20261026/packets/03_instance_flipt-io__flipt-c12967bc73fdf02054cf3ef8498c05e25f0a18c0.md

```bash
gofmt -w internal/server/middleware/grpc/middleware.go internal/server/auth/middleware.go
```

## 04:X000.c0 — exploration / archived non_direct

Read full source: results/one_day_precision_20261026/packets/04_instance_flipt-io__flipt-5ffba3406a7993d97ced4cc13658bee66150fcca.md

```bash
find . -maxdepth 3 -not -path '*/.*'
```

## 04:X013.c0 — verification / archived non_direct

Read full source: results/one_day_precision_20261026/packets/04_instance_flipt-io__flipt-5ffba3406a7993d97ced4cc13658bee66150fcca.md

```bash
go test ./server/... ./errors/... ./rpc/... ./storage/cache/...
```

## 04:X003.c0 — exploration / archived non_direct

Read full source: results/one_day_precision_20261026/packets/04_instance_flipt-io__flipt-5ffba3406a7993d97ced4cc13658bee66150fcca.md

```bash
ls -la config/ config/testdata/config/
```

## 04:X001.c0 — exploration / archived direct

Read full source: results/one_day_precision_20261026/packets/04_instance_flipt-io__flipt-5ffba3406a7993d97ced4cc13658bee66150fcca.md

```bash
cat config/config.go
```

## 04:X003.c3 — exploration / archived uncertain

Read full source: results/one_day_precision_20261026/packets/04_instance_flipt-io__flipt-5ffba3406a7993d97ced4cc13658bee66150fcca.md

```bash
cat config/local.yml
```

## 04:Y000.c1 — exploration / archived non_direct

Read full source: results/one_day_precision_20261026/packets/04_instance_flipt-io__flipt-5ffba3406a7993d97ced4cc13658bee66150fcca.md

```bash
find . -maxdepth 3 -type f | sort | head -200
```

## 04:Y012.c0 — verification / archived non_direct

Read full source: results/one_day_precision_20261026/packets/04_instance_flipt-io__flipt-5ffba3406a7993d97ced4cc13658bee66150fcca.md

```bash
sed -n '1,220p' patch.txt
```

## 04:Y000.c0 — administration / archived non_direct

Read full source: results/one_day_precision_20261026/packets/04_instance_flipt-io__flipt-5ffba3406a7993d97ced4cc13658bee66150fcca.md

```bash
printf '%s\n' '--- files ---'
```

## 04:Y000.c3 — exploration / archived direct

Read full source: results/one_day_precision_20261026/packets/04_instance_flipt-io__flipt-5ffba3406a7993d97ced4cc13658bee66150fcca.md

```bash
grep -RIn --exclude='*_test.go' -E 'type databaseConfig|databaseConfig|CheckForUpdates|func Load|Default\(\)|max_idle|max_open|conn_max' . | head -240
```

## 04:Y006.c1 — edit / archived uncertain

Read full source: results/one_day_precision_20261026/packets/04_instance_flipt-io__flipt-5ffba3406a7993d97ced4cc13658bee66150fcca.md

```bash
gofmt -w config/config.go
```
