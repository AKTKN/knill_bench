"""Publication sized logical error rate plots from a completed run directory."""
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

from knill_bench.analysis.report import wilson
from knill_bench.data.storage import read_rows


# Case fields accepted by filters and grouping. A curve must have one observation per p.
PARAMETERS = (
    'protocol', 'distance', 'basis', 'cycles', 'prep_rounds',
    'post_gate_rounds', 'post_gate_scope', 'geometry', 'requested_decoder',
    'effective_decoder', 'decoder_kind', 'validation_status',
)


def load_logical_error_rates(run):
    """Return one count-weighted record per case; invalid decoder shots are excluded."""
    run = Path(run)
    cases = read_rows(run, 'cases')
    batches = read_rows(run, 'decoder_batches')
    if not cases:
        raise ValueError(f'No cases found in {run}')
    counts = defaultdict(lambda: [0, 0, 0])
    for batch in batches:
        item = counts[batch['case_id']]
        item[0] += batch['errors']
        item[1] += batch['valid']
        item[2] += batch['failed']
    rows = []
    for case in cases:
        errors, valid, failed = counts[case['case_id']]
        if valid == 0:
            continue
        if errors < 0 or errors > valid:
            raise ValueError(f"Invalid error counts for {case['case_id']}")
        low, high = wilson(errors, valid)
        rows.append({**{key: case[key] for key in PARAMETERS},
                     'p': case['p'], 'case_id': case['case_id'],
                     'errors': errors, 'valid': valid, 'failed': failed,
                     'ler': errors / valid, 'ci_low': low, 'ci_high': high})
    return rows


def plot_logical_error_rates(rows, *, filters=None, group_by=('protocol', 'distance'),
                             figsize=(3.45, 2.65), ax=None):
    """Plot filtered cases, with each group as a curve and a 95% Wilson band.

    Any parameter varying at the same physical error rate must be filtered or
    grouped. This prevents silently joining distinct experiments into one curve.
    """
    filters = {} if filters is None else dict(filters)
    group_by = (group_by,) if isinstance(group_by, str) else tuple(group_by)
    unknown = (set(filters) | set(group_by)) - set(PARAMETERS)
    if unknown:
        raise ValueError(f'Unknown parameter(s): {sorted(unknown)}; choose from {PARAMETERS}')
    if len(set(group_by)) != len(group_by):
        raise ValueError('group_by contains duplicate parameters')
    selected = [r for r in rows if all(r[k] in v if isinstance(v, (set, list, tuple)) else r[k] == v
                                      for k, v in filters.items())]
    if not selected:
        raise ValueError('No cases match the filters')
    groups = defaultdict(list)
    for row in selected:
        groups[tuple(row[k] for k in group_by)].append(row)
    for key, items in groups.items():
        ps = [r['p'] for r in items]
        if len(ps) != len(set(ps)):
            raise ValueError(f'Group {key} has multiple cases at the same p; add filters or group_by parameters')
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize, dpi=300, layout='constrained')
    else:
        fig = ax.figure
    for key, items in sorted(groups.items(), key=lambda pair: str(pair[0])):
        items.sort(key=lambda r: r['p'])
        x = [r['p'] for r in items]
        y = [r['ler'] for r in items]
        label = ', '.join(f'{name}={value}' for name, value in zip(group_by, key)) or 'Selected cases'
        line, = ax.plot(x, y, marker='o', markersize=3, linewidth=1.2, label=label)
        ax.fill_between(x, [r['ci_low'] for r in items], [r['ci_high'] for r in items],
                        color=line.get_color(), alpha=0.2, linewidth=0)
    ax.set(xlabel='Physical error rate $p$', ylabel='Logical error rate', xlim=(0, None))
    ax.set_yscale('log')
    ax.tick_params(labelsize=8, direction='in', top=True, right=True)
    ax.xaxis.label.set_size(9)
    ax.yaxis.label.set_size(9)
    ax.legend(fontsize=7, frameon=False)
    return fig, ax


def save_figure(fig, path):
    """Save at 300 dpi; PDF remains vector based."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches='tight')
    return path
