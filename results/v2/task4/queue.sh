#!/bin/bash
# API jobs in sequence (the SoCLaaS key's queue is small)
cd /home/user/framework/worktrace
while pgrep -f "scripts/v2_task4.py second" >/dev/null; do sleep 15; done
../.venv/bin/python scripts/v2_task4.py selfcons > ../results/v2/task4/selfcons.log 2>&1
../.venv/bin/python scripts/v2_ctb.py label > ../results/v2/task4/ctb_label.log 2>&1
echo ALLDONE >> ../results/v2/task4/selfcons.log
