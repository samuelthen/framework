"""Synthetic example of a component sequence over code-version states."""
from pathlib import Path
import json
import os
import sys

os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/worktrace-example-mpl')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'worktrace'))
from worktrace.resources import ROLE_MARKERS, CONTRIBUTION_COLORS
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    out = ROOT / 'output/figures'
    out.mkdir(parents=True, exist_ok=True)
    roles = ['exploration', 'exploration', 'edit', 'verification', 'verification',
             'edit', 'verification', 'exploration', 'verification']
    labels = ['direct', 'direct', 'direct', 'direct', 'non_direct',
              'uncertain', 'uncertain', 'non_direct', 'uncertain']
    titles = ['Read source', 'Read tests', 'Implement fix', 'Check fix', 'Repeat check',
              'Extra edit', 'Check new version', 'Re-read code', 'Edge-case check']
    inp = [1000, 1000, 2500, 3000, 3100, 3200, 3400, 3500, 3600]
    cache = [600, 600, 1800, 2400, 2500, 2600, 2800, 2900, 3000]
    output = [300, 300, 900, 240, 60, 200, 120, 100, 80]
    responses = ['R1', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8']
    xx = list(range(1, 10))
    yy = [0, 0, 1, 2, 2, 3, 4, 4, 4]
    assert sum(output) == 2300
    assert sum(output[3:]) == 800
    fig = plt.figure(figsize=(18, 10), facecolor='#FCFCFA')
    gs = fig.add_gridspec(2, 1, height_ratios=[3.7, 2.2], hspace=.32,
                          left=.11, right=.98, top=.85, bottom=.18)
    ax = fig.add_subplot(gs[0])
    ink, muted = '#17252D', '#53616B'
    fig.text(.035, .945, 'WorkTrace: component progression across code versions',
             fontsize=23, weight='bold', color=ink)
    fig.text(.035, .905, 'ILLUSTRATIVE ONLY  |  Synthetic actions, labels, usage, and checkpoint outcomes',
             fontsize=12, color=muted)
    for y in [0, 2, 4]:
        ax.axhline(y, color='#D5DDE2', lw=1, zorder=0)
    ax.fill_between([3.5, 5.5], 1.65, 2.35, color='#E5F3E9', zorder=0)
    ax.fill_between([6.5, 9.5], 3.65, 4.35, color='#E5F3E9', zorder=0)
    ax.text(3.65, 2.42, 'V1: first confirmed PASS', color='#24763C', weight='bold', fontsize=11)
    ax.text(7.1, 4.42, 'V2: final version, PASS', color='#24763C', weight='bold', fontsize=11)
    ax.text(.7, .42, 'V0: FAIL', color='#9C4747', fontsize=10, weight='bold')
    # The crossing at x=3.5 is the state after the first edit has completed.
    path_x = [1, 2, 2.5, 3.5, 4, 5, 5.5, 6.5, 7, 8, 9]
    path_y = [0, 0, 0, 2, 2, 2, 2, 4, 4, 4, 4]
    ax.plot(path_x, path_y, color='#6B7780', lw=2, zorder=1)
    for xa, xb, y in [(1.25, 1.7, 0), (4.25, 4.7, 2), (7.25, 7.7, 4), (8.25, 8.7, 4)]:
        ax.annotate('', (xb, y), (xa, y), arrowprops=dict(arrowstyle='->', color='#6B7780', lw=1.7))
    ax.axvline(3.5, color='#24763C', ls=(0, (4, 4)), lw=1.3, zorder=0)
    ax.text(3.58, -.8, 'First passing state exists here', fontsize=10, color='#24763C')
    for i, (x, y, role, label, title) in enumerate(zip(xx, yy, roles, labels, titles), 1):
        ax.scatter(x, y, s=600, marker=ROLE_MARKERS[role],
                   c=CONTRIBUTION_COLORS[label], edgecolors='white', linewidths=.8, zorder=4)
        ax.text(x, y, f'C{i}', color='white', weight='bold', fontsize=11,
                ha='center', va='center', zorder=5)
        ax.text(x, y - .47, title, ha='center', va='top', fontsize=9.5, color=ink)
    ax.set(xlim=(.5, 9.5), ylim=(-1, 5), yticks=[0, 2, 4],
           yticklabels=['V0\nInitial', 'V1\nAfter edit 1', 'V2\nAfter edit 2'],
           xticks=xx, xticklabels=[f'{i}' for i in xx])
    ax.set_xlabel('Component order →', fontsize=11, color=ink, labelpad=9)
    ax.set_ylabel('Code version\n(distinct states)', fontsize=11, color=ink, labelpad=15)
    ax.tick_params(axis='both', length=0, labelsize=10, colors=muted)
    for s in ['top', 'right', 'left']:
        ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_color('#C4CCD1')

    ta = fig.add_subplot(gs[1]); ta.axis('off')
    row_names = ['Classification', 'Contribution', 'Response', 'Input tokens',
                 'Cached input¹', 'Output tokens', 'Attribution']
    rows = [roles, [s.replace('_', '-') for s in labels], responses,
            [f'{v:,}' for v in inp], [f'{v:,}' for v in cache],
            [f'{v:,}' for v in output], ['½ of R1', '½ of R1'] + ['Response'] * 7]
    table = ta.table(cellText=rows, colLabels=[f'C{i}' for i in xx], rowLabels=row_names,
                     cellLoc='center', loc='center', bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False); table.set_fontsize(9)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('#D5DDE2'); cell.set_linewidth(.6)
        cell.set_facecolor('#F1F4F5' if r == 0 or c == -1 else 'white')
        if r == 0:
            cell.set_text_props(weight='bold', color=ink)
        if r == 1 and c >= 0:
            cell.set_text_props(color=ink, weight='bold')
        if r == 2 and c >= 0:
            cell.set_text_props(color=CONTRIBUTION_COLORS[labels[c]], weight='bold')
    fig.text(.035, .125, 'Shape: circle exploration, diamond edit, square verification. Color: green direct, orange non-direct, gray uncertain.',
             fontsize=11, color=ink)
    fig.text(.035, .088, 'Output: 2,300 total tokens; 800 after the first confirmed passing state, including 200 for an extra edit.',
             fontsize=12, weight='bold', color=ink)
    fig.text(.035, .052, '¹ Cached input is included in input here; do not add it again. R1 shares are estimated. Other entries show response-associated usage.',
             fontsize=10, color=muted)
    fig.text(.035, .025, 'A PASS requires evaluation of that exact version under the same final-test protocol. Later work is not automatically redundant.',
             fontsize=10, color=muted)
    for ext in ['png', 'pdf', 'svg']:
        path = out / f'worktrace_component_version_example.{ext}'
        fig.savefig(path, dpi=150, facecolor=fig.get_facecolor())
        if ext == 'svg':
            path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines()) + '\n')
    plt.close(fig)
    data = dict(status='synthetic illustration; not empirical evidence',
                components=[dict(component_id=f'C{i+1}', role=roles[i], contribution=labels[i],
                                 response_id=responses[i], input_tokens=inp[i], cached_input_tokens=cache[i],
                                 output_tokens=output[i]) for i in range(9)],
                version_outcomes={'V0': 'synthetic_fail', 'V1': 'synthetic_pass', 'V2': 'synthetic_pass'})
    (out / 'worktrace_component_version_example.json').write_text(json.dumps(data, indent=2) + '\n')
    print(out / 'worktrace_component_version_example.png')


if __name__ == '__main__':
    main()
