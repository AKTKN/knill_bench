"""Exact small independent-component inference and explicit unsupported cases."""

import itertools
import math

import numpy as np
import pymatching
import pytest
import stim

from knill_bench.converter.decoding import GraphlikeModelError
from knill_bench.converter.local_matching import LocalMatching


def test_simple_temporal_predictions_against_separate_pymatching_graph():
    dem = stim.DetectorErrorModel("error(.1) D0 L0\nerror(.1) D0 D1\nerror(.1) D1 L1")
    events = np.array(list(itertools.product([False,True],repeat=2)))
    model = LocalMatching.temporal(dem, output_count=2)
    reference = pymatching.Matching.from_detector_error_model(dem, enable_correlations=False)
    assert np.array_equal(model.decode(events), reference.decode_batch(events, enable_correlations=False))
    assert model.summary["components"] == model.summary["graph_components"] == 3


def test_all_separator_components_retained_and_inferred_independently():
    dem = stim.DetectorErrorModel("error(.1) D0 L0 ^ D1 L1\nerror(.8) L2")
    model = LocalMatching.temporal(dem, output_count=3)
    events = np.array(list(itertools.product([False,True],repeat=2)))
    expected = np.column_stack((events, np.ones(4,dtype=bool)))
    assert np.array_equal(model.decode(events), expected)
    assert model.summary["source_events"] == 2 and model.summary["components"] == 3
    assert model.summary["separators"] == 1 and model.summary["prior_only_components"] == 1
    assert model.summary["complemented_components"] == 1


def test_parallel_different_label_alternatives_are_not_implicitly_merged():
    # More likely alternative appears SECOND, proving no first-edge label choice.
    model = LocalMatching.temporal(stim.DetectorErrorModel("error(.01) D0 L0\nerror(.1) D0 L1"), output_count=2)
    assert model.auxiliary_count == 2
    assert model.matching.num_edges == 4
    assert model.decode(np.array([[False],[True]])).tolist() == [[False,False],[False,True]]
    # Independent exhaustive minimum component-pattern log weight reference.
    for observed in (0,1):
        candidates=[]
        for bits in itertools.product([0,1],repeat=2):
            if bits[0]^bits[1] == observed:
                candidates.append((sum(b*math.log((1-p)/p) for b,p in zip(bits,[.01,.1])),bits))
        expected=min(candidates)[1]
        assert model.decode(np.array([[bool(observed)]]))[0].tolist() == list(map(bool,expected))


def test_capacity_predictions_against_independent_small_check_matrix_model():
    h=np.array([[1,1,0],[0,1,1]],dtype=np.uint8)
    events=np.array(list(itertools.product([False,True],repeat=2)))
    ours=LocalMatching.capacity(h)
    reference=pymatching.Matching.from_check_matrix(h,weights=np.ones(3))
    assert np.array_equal(ours.decode(events),reference.decode_batch(events,enable_correlations=False))
    assert np.array_equal((ours.decode(events).astype(np.uint8) @ h.T %2).astype(bool),events)


@pytest.mark.parametrize("text", ["error(.1) D0 D1 D2", "error(.1) D0 ^ D1 D2 D3"])
def test_residual_hyperedges_raise_without_trimming(text):
    with pytest.raises(GraphlikeModelError):
        LocalMatching.temporal(stim.DetectorErrorModel(text),output_count=1)


def test_noiseless_declared_prediction_width_and_deterministic_components():
    dem=stim.DetectorErrorModel("detector D2\nlogical_observable L3")
    model=LocalMatching.temporal(dem,output_count=4)
    assert model.decode(np.zeros((3,3),dtype=bool)).shape == (3,4)
    deterministic=LocalMatching.temporal(stim.DetectorErrorModel("error(1) D0 L0"),output_count=1)
    assert deterministic.decode(np.ones((3,1),dtype=bool)).all()
