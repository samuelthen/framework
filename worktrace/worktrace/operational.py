"""Observable command categories for expenditure analysis, not utility labels.

Never execute source commands. Keep mixed and opaque work explicit. These are
lexical operational proxies; context-sensitive human intent remains separate.
"""
import re
from .parse import shell
from .versions import is_inspection


CHECK = re.compile(r'(?:^|\s)(?:pytest|py\.test|nosetests|jest|vitest|mocha|rspec|phpunit|ctest)(?:\s|$)|'
                   r'\bpython[23]?\s+-m\s+(?:pytest|unittest|doctest|py_compile|compileall)\b|'
                   r'\bgo\s+(?:test|vet|build)\b|\bcargo\s+(?:test|check|build|clippy)\b|'
                   r'\b(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:test(?::[\w-]+)?|check|lint|build|typecheck)\b|'
                   r'\b(?:mvn|gradle|\./gradlew)\s+(?:test|check|verify)\b|\b(?:mypy|flake8|ruff\s+check|tsc)\b')


def category(command):
    """Return one category for a call; no within-call output attribution."""
    parts=shell.split_chain(command or '') or [command or '']
    roles=set()
    for part in parts:
        toks=shell._strip_prefix(shell._tokens(part))
        if not toks:continue
        if toks[0] in {'cd','export','set','unset','env'}:continue
        kind=shell.classify(part)
        if kind in {'edit','revert'}:
            roles.add('edit');continue
        # Only execute-looking heads can match a checker. A grep query or echo
        # containing "pytest" is not itself a verification action.
        head=toks[0].rsplit('/',1)[-1]
        python_module=head in {'python','python2','python3'} and toks[1:2]==['-m']
        checker_head=head in {'pytest','py.test','nosetests','jest','vitest','mocha','rspec','phpunit','ctest',
                             'go','cargo','npm','pnpm','yarn','bun','mvn','gradle','gradlew','mypy','flake8','ruff','tsc','uv','poetry'}
        if kind=='run' and (checker_head or python_module) and CHECK.search(' '.join(toks)):
            roles.add('verification');continue
        if kind in {'read','search'}:
            roles.add('exploration');continue
        if kind=='run':
            write,_=shell.write_info([part])
            if write is True:roles.add('edit')
            elif is_inspection({'parts':[part]}):roles.add('exploration')
            else:roles.add('opaque_execution')
        elif kind=='probe':roles.add('artifact_inspection')
        elif kind=='submit':roles.add('administration')
        elif toks[0] in {'echo','printf','true','false',':','pwd','mkdir','date','whoami','sleep','exit'}:
            roles.add('administration')
        else:roles.add('opaque_execution')
    if not roles:return 'administration'
    return next(iter(roles)) if len(roles)==1 else 'mixed_call'


def result_screen(op):
    """Native-call status only; a pipeline exit is not every check's outcome."""
    if op.get('missing_result'):return 'missing_result'
    text=op.get('agent_output') or op.get('output') or ''
    if op.get('exit_code')==-1 or re.search(r'(?i)timed? out|timeout after|command timeout',text):
        return 'timeout_or_interrupted'
    if not text.strip():return 'empty_observation'
    if op.get('agent_saw_truncated'):return 'truncated_observation'
    return 'observed_nonzero' if op.get('exit_code') not in (0,None) else 'observed_zero' if op.get('exit_code')==0 else 'exit_unknown'
