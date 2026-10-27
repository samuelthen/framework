"""Small logged Soc client for experimental subjects; credentials stay host-only."""
import json
from pathlib import Path
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler,Request,build_opener
import uuid


def load_env(path):
    result={}
    for line in Path(path).read_text().splitlines():
        line=line.strip()
        if line and not line.startswith('#') and '=' in line:
            key,value=line.removeprefix('export ').split('=',1)
            result[key.strip()]=value.strip().strip('\"\'')
    for key in ['SOCLAAS_BASE_URL','SOCLAAS_API_KEY']:
        if not result.get(key):raise ValueError('Missing '+key)
    if not result['SOCLAAS_BASE_URL'].startswith('https://'):raise ValueError('HTTPS required')
    return result


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


class Budget:
    def __init__(self,max_requests=144,max_returned_tokens=2_000_000):
        self.max_requests=max_requests;self.max_tokens=max_returned_tokens
        self.requests=0;self.tokens=0;self.pending=0;self.unknown_usage_attempts=0;self.lock=threading.Lock()
    def reserve(self,payload):
        allowance=len(json.dumps(payload).encode())+payload['max_tokens']+4096
        with self.lock:
            if self.requests>=self.max_requests or self.tokens+self.pending+allowance>self.max_tokens:raise RuntimeError('Experimental API ceiling reached')
            self.requests+=1;self.pending+=allowance
        return allowance
    def settle(self,usage,allowance):
        value=(usage or {}).get('total_tokens')
        with self.lock:
            self.pending-=allowance
            if isinstance(value,int) and not isinstance(value,bool) and value>=0:self.tokens+=value
            else:self.tokens+=allowance;self.unknown_usage_attempts+=1


class Client:
    def __init__(self,env,model,folder,budget):
        self.env=env;self.model=model;self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True)
        self.budget=budget
    def complete(self,messages,tools=None,max_tokens=3072):
        payload=dict(model=self.model,messages=messages,max_tokens=max_tokens,reasoning_effort='low')
        if tools:payload['tools']=tools
        identifier=uuid.uuid4().hex
        (self.folder/f'{identifier}.request.json').write_text(json.dumps(payload))
        for attempt in range(3):
            allowance=self.budget.reserve(payload);start=time.monotonic();settled=False
            row=dict(request_id=identifier,attempt=attempt+1,model=self.model,usage=None,cost_usd=None)
            try:
                request=Request(self.env['SOCLAAS_BASE_URL'].rstrip('/')+'/chat/completions',
                    data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.env['SOCLAAS_API_KEY']})
                with build_opener(NoRedirect()).open(request,timeout=90) as response:data=json.load(response)
                data=json.loads(json.dumps(data).replace(self.env['SOCLAAS_API_KEY'],'[REDACTED]'))
                row.update(status='completed',usage=data.get('usage'),returned_model=data.get('model'))
                self.budget.settle(row['usage'],allowance);settled=True
                (self.folder/f'{identifier}.response.json').write_text(json.dumps(data))
                return data
            except (HTTPError,URLError,TimeoutError,ValueError) as error:
                code=error.code if isinstance(error,HTTPError) else None
                row.update(status='error',error_type=type(error).__name__,http_status=code)
                retry=code in {408,429,500,502,503,504} or isinstance(error,(URLError,TimeoutError))
                if attempt==2 or not retry:raise RuntimeError('Soc request failed; see sanitized log') from None
                time.sleep(2*(attempt+1))
            finally:
                if not settled:self.budget.settle(row['usage'],allowance)
                row['seconds']=time.monotonic()-start
                with (self.folder/'usage.jsonl').open('a') as output:output.write(json.dumps(row)+'\n')


class AgentModel:
    def __init__(self,client):self.client=client
    def query(self,messages,**kwargs):
        from types import SimpleNamespace
        from minisweagent.models.utils.actions_toolcall import BASH_TOOL,parse_toolcall_actions
        fields={'role','content','tool_calls','tool_call_id','reasoning_content','reasoning'}
        prepared=[{k:v for k,v in m.items() if k in fields} for m in messages if m['role'] in {'system','user','assistant','tool'}]
        data=self.client.complete(prepared,tools=[BASH_TOOL]);choice=data['choices'][0]
        message={k:v for k,v in choice['message'].items() if k in fields};message['role']='assistant'
        calls=[SimpleNamespace(id=t.get('id'),function=SimpleNamespace(**t.get('function',{}))) for t in message.get('tool_calls') or []]
        actions=parse_toolcall_actions(calls,format_error_template='{{error}}. Use the bash tool.',template_kwargs={'finish_reason':choice.get('finish_reason')})
        return {**message,'extra':{'actions':actions,'cost':0.0,'cost_known':False}}
    def format_message(self,**kwargs):return kwargs
    def format_observation_messages(self,message,outputs,template_vars=None):
        from minisweagent.models.utils.actions_toolcall import format_toolcall_observation_messages
        return format_toolcall_observation_messages(actions=message.get('extra',{}).get('actions',[]),outputs=outputs,
            observation_template='Return code: {{output.returncode}}\n{{output.output[-12000:]}}\n{{output.exception_info|default(\'\')}}')
    def get_template_vars(self,**kwargs):return {'model_name':self.client.model}
    def serialize(self):return {'info':{'config':{'model':{'model_id':self.client.model,'reasoning_effort_requested':'low'}},'cost_known':False}}
