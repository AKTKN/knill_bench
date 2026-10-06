import matplotlib
import pytest

matplotlib.use('Agg')
from knill_bench.analysis.plotting import plot_logical_error_rates
from knill_bench.analysis.report import wilson


def test_plot_groups_wilson_band_and_rejects_ambiguous_cases(tmp_path):
    rows = []
    for distance in (3, 5):
        for p, errors in ((0.001, 0), (0.002, distance)):
            low, high = wilson(errors, 100)
            rows.append(dict(protocol='memory', distance=distance, basis='z', p=p,
                             errors=errors, valid=100, ler=errors / 100,
                             ci_low=low, ci_high=high))
    fig, ax = plot_logical_error_rates(rows, filters={'basis': 'z'}, group_by='distance')
    assert fig.dpi == 300
    assert ax.get_yscale() == 'log'
    assert len(ax.lines) == 2
    assert len(ax.collections) == 2
    assert list(ax.lines[0].get_xdata()) == [0.001, 0.002]
    fig.savefig(tmp_path / 'plot.png', dpi=300)
    assert (tmp_path / 'plot.png').is_file()
    with pytest.raises(ValueError, match='multiple cases'):
        plot_logical_error_rates(rows, filters={'basis': 'z'}, group_by='protocol')
