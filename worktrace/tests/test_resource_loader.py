"""Response usage joins must preserve no-tool responses and avoid duplication."""
import json

from worktrace.loaders.jetbrains import load_response_usage, load_row


def test_jetbrains_usage_is_kept_once_per_response_not_per_tool():
    messages = [dict(object='response',id='planning',output=[],usage=dict(input_tokens=10,output_tokens=20)),
        dict(object='response',id='tools',output=[
            dict(type='function_call',name='bash',call_id='a',arguments='{"command":"cat a.py"}'),
            dict(type='function_call',name='bash',call_id='b',arguments='{"command":"pytest"}')],
            usage=dict(input_tokens=30,output_tokens=40)),
        dict(type='function_call_output',call_id='a',output='code'),
        dict(type='function_call_output',call_id='b',output='passed')]
    row=dict(model='luna',instance_id='task',run=1,messages=json.dumps(messages),
             reward=1,resolved=True,status='completed')
    _,ops=load_row(row)
    ledger=load_response_usage(row)
    assert len(ops)==2 and len(ledger)==2
    assert ops[0]['response_id']==ops[1]['response_id']==ledger[1]['response_id']
    assert ledger[0]['tool_call_count']==0
    assert sum(r['usage']['output_tokens'] for r in ledger)==60
    assert 'output_tokens' not in ops[0] and 'usage' not in ops[0]


def test_harbor_response_cost_has_explicit_provenance_and_missing_stays_null():
    row = dict(model='luna', instance_id='task', run=1, cost_source='harbor_agent_result',
               messages=json.dumps([
                   dict(object='response', output=[], extra=dict(cost=.001)),
                   dict(object='response', output=[], usage=None)]))
    first, second = load_response_usage(row)
    assert first['usage']['cost_usd'] == .001
    assert first['raw_extra_cost'] == .001
    assert 'extra.cost' in first['cost_provenance']
    assert first['usage']['input_tokens'] is None
    assert second['usage']['cost_usd'] is None


def test_public_map_zero_response_placeholders_are_not_free_usage():
    row = dict(model='gemini_3_7_flash', instance_id='task', run=1,
               cost_source='trajectory_tokens_litellm_public_map',
               messages=json.dumps([dict(object='response', output=[], extra=dict(cost=0.0))]))
    record, = load_response_usage(row)
    assert record['raw_extra_cost'] == 0
    assert record['usage']['cost_usd'] is None
