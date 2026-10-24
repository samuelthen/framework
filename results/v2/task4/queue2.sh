#!/bin/bash
cd /home/user/framework/worktrace
while pgrep -f "scripts/v2_ctb.py label" >/dev/null; do sleep 15; done
../.venv/bin/python scripts/v2_task4.py selfcons > ../results/v2/task4/selfcons.log 2>&1
echo ALLDONE >> ../results/v2/task4/selfcons.log
