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
