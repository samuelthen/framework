"""Real Git scope checks in disposable repos, plus conservative trace cases.

Every executed Git command is authored here; no dataset command is executed.
"""
import subprocess

from worktrace.facts import extract_facts
from worktrace.versions import build_version_graph


def git(repo,*args):
    p=subprocess.run(['git','-C',str(repo),*args],text=True,capture_output=True,check=True)
    return p.stdout


def version(commands):
    ops=extract_facts([dict(op_id=f'o{i}',turn_id=f't{i}',command=c,output=o,exit_code=e)
                       for i,(c,o,e) in enumerate(commands)])
    return build_version_graph(dict(run_id='r',task_id='t',model='test'),ops)


def setup_repo(path):
    git(path,'init','-q')
    (path/'tracked.py').write_text('old\n')
    git(path,'add','tracked.py')
    git(path,'-c','user.name=Regression Test','-c','user.email=test@example.invalid','commit','-qm','base')
    return [('git status --porcelain',git(path,'status','--porcelain'),0),
            ('git ls-files',git(path,'ls-files'),0)]


def test_real_untracked_file_survives_checkout(tmp_path):
    cmds=setup_repo(tmp_path)
    (tmp_path/'untracked.py').write_text('new\n')
    git(tmp_path,'checkout','.')
    assert (tmp_path/'untracked.py').read_text()=='new\n'
    assert version(cmds+[('echo new > untracked.py','',0),('git checkout .','',0)])['final']!=0


def test_real_staged_edit_survives_checkout(tmp_path):
    cmds=setup_repo(tmp_path)
    (tmp_path/'tracked.py').write_text('new\n')
    git(tmp_path,'add','tracked.py')
    git(tmp_path,'checkout','.')
    assert (tmp_path/'tracked.py').read_text()=='new\n'
    assert git(tmp_path,'diff','--cached')
    assert version(cmds+[('sed -i s/old/new/ tracked.py','',0),('git add tracked.py','',0),('git checkout .','',0)])['final']!=0


def test_real_supported_restore_returns_initial_contents(tmp_path):
    cmds=setup_repo(tmp_path)
    (tmp_path/'tracked.py').write_text('new\n')
    git(tmp_path,'checkout','.')
    assert (tmp_path/'tracked.py').read_text()=='old\n'
    assert version(cmds+[('sed -i s/old/new/ tracked.py','',0),('git checkout .','',0)])['final']==0


def test_no_tracking_evidence_cannot_claim_root():
    assert version([('sed -i s/old/new/ a.py','',0),('git checkout -- a.py','',0)])['final']!=0


def test_truncated_tracking_list_cannot_establish_restore_scope():
    assert version([('git status --porcelain','',0),('git ls-files','tracked.py\n[Output truncated]',0),
                    ('sed -i s/old/new/ tracked.py','',0),('git checkout .','',0)])['final']!=0


def test_staged_only_restore_does_not_undo_worktree_edit():
    cmds=[('git status --porcelain','',0),('git ls-files','a.py\n',0)]
    assert version(cmds+[('sed -i s/x/y/ a.py','',0),('git restore --staged a.py','',0)])['final']!=0


def test_partial_restore_cannot_remove_untracked_changes():
    cmds=[('git status --porcelain','',0),('git ls-files','a.py\n',0)]
    assert version(cmds+[('echo x > new.py','',0),('git checkout -- new.py','',0)])['final']!=0


def test_known_write_sensitivity_still_retains_index_uncertainty():
    cmds=[('git status --porcelain','',0),('git ls-files','a.py\n',0),
          ('sed -i s/x/y/ a.py','',0),('git add a.py','',0),('git checkout .','',0)]
    ops=extract_facts([dict(op_id=f'o{i}',turn_id=f't{i}',command=c,output=o,exit_code=e)
                       for i,(c,o,e) in enumerate(cmds)])
    g=build_version_graph(dict(run_id='r',task_id='t',model='m'),ops,unknown_creates_version=False)
    assert not g['final_is_initial']
    assert g['nodes'][g['final']]['uncertain']
