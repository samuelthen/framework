"""Conservation, missingness and graph-region attribution regressions."""
from copy import deepcopy

import pytest

from worktrace.resources import (allocate_usage, assert_conservation, normalize_usage,
                                 region_totals, response_ledger, contribution_resource_bounds)


def response(rid="r:t0", **usage):
    return dict(response_id=rid, run_id="r", usage=usage)


def component(cid, rid="r:t0", role="exploration", **fields):
    return dict(component_id=cid, response_id=rid, role=role, **fields)


def test_shared_response_conserves_tokens_and_money_across_regions():
    ledger = [response(input_tokens=900, output_tokens=300, cost_usd=.03)]
    rows = allocate_usage(ledger, [component("a"), component("b"), component("c", role="verification")])
    assert [r["usage"]["output_tokens"] for r in rows] == [100,100,100]
    regions = region_totals(rows)
    assert sum(r["output_tokens"]["known_total"] for r in regions) == 300
    assert sum(r["cost_usd"]["known_total"] for r in regions) == pytest.approx(.03)
    exploration = next(r for r in regions if r["role"] == "exploration")
    assert exploration["output_tokens"]["whole_response_associated_total"] is None
    assert exploration["output_tokens"]["shared_response_allocated_total"] == 200


def test_complete_response_inside_region_has_recorded_total_despite_multiple_components():
    rows = allocate_usage([response(output_tokens=300)], [component("a"), component("b")])
    totals = region_totals(rows)[0]
    assert totals["output_tokens"]["whole_response_associated_total"] == 300
    assert totals["output_tokens"]["shared_response_allocated_total"] is None


def test_single_component_is_response_association_not_invented_reasoning_allocation():
    r = allocate_usage([response(output_tokens=25)], [component("a")])[0]
    assert r["allocation_method"] == "single_component_response_association"
    assert r["usage"]["reasoning_tokens"] is None


def test_missing_usage_is_not_zero_and_regions_report_coverage():
    rows = allocate_usage([response(output_tokens=0), response("r:t1")],
                          [component("a"), component("b", rid="r:t1")])
    total = region_totals(rows)[0]["output_tokens"]
    assert total["known_total"] == 0
    assert total["unknown_usage_responses"] == 1
    assert total["usage_coverage_response_weight"] == .5
    assert total["mean_allocated_per_component"] is None
    assert rows[1]["visual"]["size_value"] is None


def test_no_tool_response_stays_in_ledger_and_unassigned_bucket():
    rows = allocate_usage([response(output_tokens=40)], [])
    assert rows[0]["component_id"] is None and rows[0]["allocation_method"] == "unassigned_response"
    total = region_totals(rows)[0]
    assert total["components"] == 0 and total["output_tokens"]["known_total"] == 40
    assert total["output_tokens"]["mean_allocated_per_component"] is None


def test_generated_but_unexecuted_component_does_not_erase_inference_expenditure():
    rows = allocate_usage([response(output_tokens=80)], [component("a", execution_status="not_executed")])
    assert rows[0]["usage"]["output_tokens"] == 80


def test_duplicate_response_component_and_orphan_ids_rejected():
    with pytest.raises(ValueError, match="Duplicate response"):
        allocate_usage([response(),response()], [])
    with pytest.raises(ValueError, match="Duplicate component"):
        allocate_usage([response()], [component("a"), component("a")])
    with pytest.raises(ValueError, match="Unknown response"):
        allocate_usage([], [component("a")])


def test_same_source_response_id_requires_explicit_duplicate_reconciliation():
    ledger = [dict(response(),source_response_id="source"), dict(response("r:t1"),source_response_id="source")]
    with pytest.raises(ValueError, match="source response"):
        allocate_usage(ledger, [])


def test_detail_reasoning_and_cache_are_preserved_not_added_to_totals():
    usage = normalize_usage(dict(input_tokens=100, output_tokens=50,
        input_tokens_details=dict(cached_tokens=80), output_tokens_details=dict(reasoning_tokens=30)))
    assert usage == dict(input_tokens=100, cached_input_tokens=80, output_tokens=50,
                         reasoning_tokens=30, cost_usd=None)


def test_unsupported_and_conflicting_provider_fields_are_not_guessed():
    assert normalize_usage(dict(prompt_token_count=99))["input_tokens"] is None
    with pytest.raises(ValueError, match="Conflicting"):
        normalize_usage(dict(input_tokens=10, prompt_tokens=20))
    for invalid in [-1, float("nan"), float("inf"), True, "10", 1.5]:
        with pytest.raises(ValueError):
            normalize_usage(dict(output_tokens=invalid))


def test_ledger_retains_response_ids_no_tool_and_missing_usage_turns():
    messages = [dict(role="user", content="task"),
        dict(object="response", id="a", output=[], usage=dict(input_tokens=20,output_tokens=5)),
        dict(type="function_call_output", output="ok"),
        dict(object="response", id="b", output=[dict(type="function_call")])]
    ledger = response_ledger(messages,"r")
    assert [r["response_id"] for r in ledger] == ["r:t0","r:t1"]
    assert ledger[0]["tool_call_count"] == 0 and ledger[1]["tool_call_count"] == 1
    assert ledger[1]["usage"]["output_tokens"] is None


def test_version_accounting_uses_generation_context_unless_explicitly_assigned():
    r = dict(response(output_tokens=10),generation_version="V0")
    a = allocate_usage([r], [component("edit",state_after="V1")])[0]
    assert a["version_region"] == "V0"
    b = allocate_usage([r], [component("edit",version_region="V0->V1")])[0]
    assert b["version_region"] == "V0->V1"
    root = allocate_usage([dict(response(output_tokens=10),generation_version=0)], [component("root")])[0]
    assert root["version_region"] == "0"


def test_mixed_response_sensitivity_preserves_total_without_claiming_role_cost():
    rows = allocate_usage([response(output_tokens=90)], [component("a"),component("b",role="verification")])
    region = region_totals(rows,mixed_response_bucket=True)[0]
    assert region["role"] == "mixed_response"
    assert region["output_tokens"]["known_total"] == 90
    assert region["output_tokens"]["whole_response_associated_total"] == 90


def test_alternative_graph_views_conserve_same_ledger_not_extra_cost():
    rows = allocate_usage([response(output_tokens=101)], [component("a",version_region="V0"),
        component("b",version_region="V1",role="verification"),component("c",version_region="V1")])
    for dims in [("role",),("version_region",),("role","version_region"),("contribution_label",)]:
        assert sum(r["output_tokens"]["known_total"] for r in region_totals(rows,dims)) == pytest.approx(101)


def test_conservation_rejects_double_counted_allocation():
    ledger = [response(output_tokens=10)]
    rows = allocate_usage(ledger,[component("a"),component("b")])
    bad = deepcopy(rows)
    bad[0]["usage"]["output_tokens"] = 10
    with pytest.raises(ValueError, match="double-counted"):
        assert_conservation(ledger,bad)
    with pytest.raises(ValueError, match="Duplicate allocation"):
        assert_conservation(ledger,rows+[rows[0]])


def test_resource_contribution_keeps_unassigned_cost_uncertain():
    rows = allocate_usage([response(output_tokens=60),response("r:t1",output_tokens=40)],
        [component("a",contribution_label="direct"),component("b",contribution_label="non_direct")])
    result = contribution_resource_bounds(rows)[0]["output_tokens"]
    assert result["lower"] == .3 and result["upper"] == .7


def test_missing_and_zero_usage_cannot_produce_resource_precision():
    for usage,status in [({},"missing_usage"),({"output_tokens":0},"zero_total")]:
        rows = allocate_usage([response(**usage)],[component("a",contribution_label="direct")])
        result = contribution_resource_bounds(rows)[0]["output_tokens"]
        assert result["lower"] is None and result["status"] == status


def test_multitarget_duplication_and_cross_run_joins_are_rejected():
    with pytest.raises(ValueError,match="different runs"):
        allocate_usage([response()], [component("a",run_id="other")])
    with pytest.raises(ValueError,match="single string/integer"):
        allocate_usage([response()], [component("a",target_region=["a.py","b.py"])])
