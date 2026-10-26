"""Response usage, explicit component allocation and non-overlapping regions.

Standard library only. Missing usage stays unknown. No price lookup, token
estimation from characters, semantic annotation, or trajectory execution.
"""
from collections import defaultdict
import math

METRICS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens", "cost_usd")
GROUP_FIELDS = ("role", "version_region", "target_region", "contribution_label")
ROLE_COLORS = {"exploration": "#2878B5", "edit": "#8058AF", "verification": "#168577",
               "administration": "#737D8C", "unknown": "#A0A0A0", "unassigned": "#A0A0A0"}
ROLE_MARKERS = {"exploration": "o", "edit": "D", "verification": "s",
                "administration": "^", "unknown": "X", "unassigned": "X"}
CONTRIBUTION_COLORS = {"direct": "#237A3B", "non_direct": "#C35E18", "uncertain": "#777777"}


def _number(value, field):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric or null")
    if not math.isfinite(value) or value < 0 or (field != "cost_usd" and value != int(value)):
        raise ValueError(f"{field} must be finite, nonnegative and an integer for tokens")
    return value if field == "cost_usd" else int(value)


def _consistent(*values):
    values = [v for v in values if v is not None]
    if values and any(v != values[0] for v in values[1:]):
        raise ValueError("Conflicting usage aliases; supply an explicit provider mapping")
    return values[0] if values else None


def _region(value, default="unknown"):
    if value is None or value == "":
        return default
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("A region must be a single string/integer ID; use mixed for multiple targets")
    return str(value)


def normalize_usage(usage):
    """Explicit input/output or prompt/completion usage fields only.

    Reasoning is preserved as reported, never added to output. Provider-specific
    usage_metadata needs a documented adapter; raw source is kept by callers.
    """
    if usage is None:
        usage = {}
    if not isinstance(usage, dict):
        raise ValueError("usage must be an object or null")
    inp = usage.get("input_tokens_details") or usage.get("prompt_tokens_details") or {}
    out = usage.get("output_tokens_details") or usage.get("completion_tokens_details") or {}
    if not isinstance(inp, dict) or not isinstance(out, dict):
        raise ValueError("usage detail fields must be objects")
    raw = dict(
        input_tokens=_consistent(usage.get("input_tokens"), usage.get("prompt_tokens")),
        cached_input_tokens=_consistent(usage.get("cached_input_tokens"), inp.get("cached_tokens")),
        output_tokens=_consistent(usage.get("output_tokens"), usage.get("completion_tokens")),
        reasoning_tokens=_consistent(usage.get("reasoning_tokens"), out.get("reasoning_tokens")),
        cost_usd=usage.get("cost_usd"),
    )
    return {k: _number(v, k) for k, v in raw.items()}


def response_ledger(messages, run_id):
    """Collect every stored Responses-format response, including no-tool turns.

    Canonical response_id equals the loader's turn_id. Source IDs and raw usage
    remain available for request-level duplicate/retry reconciliation. This does
    not infer missing requests or usage from run-level totals.
    """
    records = []
    for message in messages:
        if message.get("object") != "response":
            continue
        index = len(records)
        usage = normalize_usage(message.get("usage"))
        records.append(dict(
            response_id=f"{run_id}:t{index}", turn_id=f"{run_id}:t{index}", run_id=run_id,
            turn_index=index, source_response_id=message.get("id"),
            usage=usage, raw_usage=message.get("usage"),
            source_status=message.get("status"), usage_provenance="stored response usage",
            reasoning_accounting="reported detail; inclusion in output must be checked at source",
            tool_call_count=sum(x.get("type") == "function_call" for x in message.get("output") or []),
        ))
    return records


def allocate_usage(responses, components):
    """Allocate equally over all emitted candidate components per response.

    Emission expenditure is retained for failed/not-executed commands. This
    denominator differs deliberately from performed-component precision. Calls
    without components enter an unassigned-response bucket. A known singleton
    is response-associated expenditure, not measured causal reasoning cost.
    """
    ledger, by_response, component_ids = {}, defaultdict(list), set()
    for response in responses:
        rid = response["response_id"]
        if not isinstance(rid, str) or not rid or not response.get("run_id"):
            raise ValueError("Every response needs nonempty response_id and run_id")
        if rid in ledger:
            raise ValueError(f"Duplicate response_id: {rid}")
        usage = response.get("usage") or {}
        ledger[rid] = dict(response, usage={m: _number(usage.get(m), m) for m in METRICS})
    source_ids = [(r.get("run_id"), r.get("source_response_id")) for r in ledger.values()
                  if r.get("source_response_id") is not None]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("Repeated source response IDs: reconcile duplicate/retry records before allocation")
    for component in components:
        cid, rid = component["component_id"], component["response_id"]
        if not isinstance(cid, str) or not cid:
            raise ValueError("Every component needs a nonempty string component_id")
        if cid in component_ids:
            raise ValueError(f"Duplicate component_id: {cid}")
        if rid not in ledger:
            raise ValueError(f"Unknown response_id: {rid}")
        if component.get("run_id") is not None and component["run_id"] != ledger[rid]["run_id"]:
            raise ValueError("Component and response refer to different runs")
        if component.get("contribution_label") not in (None, "direct", "non_direct", "uncertain"):
            raise ValueError("Unsupported contribution label")
        component_ids.add(cid)
        by_response[rid].append(component)
    result = []
    for rid, response in ledger.items():
        group = by_response[rid]
        weight = 1 / len(group) if group else 1.0
        for c in group or [{}]:
            kind = ("unassigned_response" if not group else
                    "single_component_response_association" if len(group) == 1 else "equal_share_response_allocation")
            values = {m: None if response["usage"][m] is None else response["usage"][m] * weight
                      for m in METRICS}
            row = dict(
                response_id=rid, run_id=response.get("run_id"), component_id=c.get("component_id"),
                parent_op_id=c.get("parent_op_id"), allocation_weight=weight, allocation_method=kind,
                allocation_basis="all_emitted_candidate_components; not performed-action denominator",
                response_component_count=len(group), usage=values, response_usage=dict(response["usage"]),
                execution_status=c.get("execution_status", "not_applicable"),
                role=c.get("role") or ("unknown" if group else "unassigned"),
                contribution_label=c.get("contribution_label") or "uncertain",
                # No post-edit state is silently substituted for generation context.
                version_region=_region(c.get("version_region") if c.get("version_region") is not None
                                       else response.get("generation_version")),
                target_region=_region(c.get("target_region"), "unknown" if group else "unassigned"),
            )
            row["visual"] = dict(role_marker=ROLE_MARKERS.get(row["role"], ROLE_MARKERS["unknown"]),
                contribution_color=CONTRIBUTION_COLORS[row["contribution_label"]],
                size_value=values["output_tokens"], size_metric="allocated output_tokens; null means unavailable",
                allocation_method=kind)
            result.append(row)
    assert_conservation(responses, result)
    return result


def assert_conservation(responses, allocations):
    ledger = {r["response_id"]: r for r in responses}
    if len(ledger) != len(responses):
        raise ValueError("Duplicate response_id")
    grouped = defaultdict(list)
    seen = set()
    for row in allocations:
        key = (row["response_id"], row["component_id"])
        if key in seen or row["response_id"] not in ledger:
            raise ValueError("Duplicate allocation or unknown response")
        seen.add(key)
        grouped[row["response_id"]].append(row)
    if grouped.keys() != ledger.keys():
        raise ValueError("Every response must have an allocation or unassigned record")
    for rid, rows in grouped.items():
        if any(not math.isfinite(r["allocation_weight"]) or r["allocation_weight"] <= 0 for r in rows):
            raise ValueError("Allocation weights must be finite and positive")
        if not math.isclose(math.fsum(r["allocation_weight"] for r in rows), 1, abs_tol=1e-9):
            raise ValueError("Response weights do not sum to one")
        for metric in METRICS:
            expected = _number((ledger[rid].get("usage") or {}).get(metric), metric)
            values = [r["usage"].get(metric) for r in rows]
            if expected is None:
                if any(v is not None for v in values):
                    raise ValueError("Missing usage cannot become a measured value")
            elif any(v is None for v in values) or not math.isclose(math.fsum(values), expected, abs_tol=1e-8):
                raise ValueError(f"{rid} {metric} was lost or double-counted")


def region_totals(allocations, group_by=("role",), mixed_response_bucket=False):
    """Aggregate a partition; alternative graph views must not be added together.

    Full response usage within one region is recorded-associated. A response
    crossing regions contributes only allocated shares. The optional mixed view
    pools heterogeneous responses instead of asserting within-response purpose.
    """
    if not group_by or any(f not in GROUP_FIELDS for f in group_by) or len(set(group_by)) != len(group_by):
        raise ValueError("Use distinct supported categorical region fields")
    by_response = defaultdict(list)
    for r in allocations:
        by_response[r["response_id"]].append(r)
    groups = defaultdict(list)
    for rows in by_response.values():
        keys = [tuple(_region(r.get(f)) for f in group_by) for r in rows]
        if mixed_response_bucket and len(set(keys)) > 1:
            key = tuple("mixed_response" for _ in group_by)
            groups[key].extend(rows)
        else:
            for key, r in zip(keys, rows):
                groups[key].append(r)
    totals = []
    for key, rows in sorted(groups.items()):
        responses = defaultdict(list)
        for r in rows:
            responses[r["response_id"]].append(r)
        n = sum(r["component_id"] is not None for r in rows)
        total_weight = math.fsum(r["allocation_weight"] for r in rows)
        out = dict(zip(group_by, key))
        out.update(components=n, responses_touched=len(responses), response_equivalent_weight=total_weight,
                   region_method="mixed_response_bucket" if mixed_response_bucket else "equal_component_allocation")
        for metric in METRICS:
            known = [r for r in rows if r["usage"][metric] is not None]
            full, shared = [], []
            for rs in responses.values():
                if rs[0]["response_usage"][metric] is None:
                    continue
                value = math.fsum(r["usage"][metric] for r in rs)
                (full if math.isclose(math.fsum(r["allocation_weight"] for r in rs), 1, abs_tol=1e-9) else shared).append(value)
            value = math.fsum(full + shared) if known else None
            out[metric] = dict(
                known_total=value,
                whole_response_associated_total=math.fsum(full) if full else None,
                shared_response_allocated_total=math.fsum(shared) if shared else None,
                mean_allocated_per_component=value/n if len(known) == len(rows) and n and value is not None else None,
                usage_coverage_response_weight=math.fsum(r["allocation_weight"] for r in known)/total_weight,
                unknown_usage_responses=sum(rs[0]["response_usage"][metric] is None for rs in responses.values()),
            )
        totals.append(out)
    return totals


def contribution_resource_bounds(allocations):
    """Per-run expenditure share attached to direct/uncertain labels.

    This is allocation-dependent, not causal necessity or measured savings.
    Unassigned no-tool responses remain uncertain. Partial usage suppresses the
    ratio rather than silently computing it on whichever responses had usage.
    """
    groups = defaultdict(list)
    for row in allocations:
        groups[row.get("run_id")].append(row)
    results = []
    for run_id, rows in groups.items():
        out = dict(run_id=run_id, interpretation="response-associated/equally allocated expenditure share")
        for metric in METRICS:
            values = [r["usage"][metric] for r in rows]
            known = [v for v in values if v is not None]
            total = math.fsum(known) if known else None
            complete = len(known) == len(rows)
            direct = math.fsum(r["usage"][metric] for r in rows
                              if r["contribution_label"] == "direct" and r["usage"][metric] is not None)
            uncertain = math.fsum(r["usage"][metric] for r in rows
                                 if r["contribution_label"] not in ("direct", "non_direct")
                                 and r["usage"][metric] is not None)
            valid = complete and total is not None and total > 0
            out[metric] = dict(known_total=total, usage_complete=complete,
                lower=direct/total if valid else None,
                upper=(direct+uncertain)/total if valid else None,
                status="computed_under_allocation" if valid else "missing_usage" if not complete else "zero_total")
        results.append(out)
    return results
