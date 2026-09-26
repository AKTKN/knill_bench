"""Lossless independent-event DEM conversion, including separator XOR semantics."""
from dataclasses import dataclass
from collections import Counter
import numpy as np
from scipy.sparse import csc_matrix
import stim


@dataclass
class FaultModel:
    h: csc_matrix
    l: csc_matrix
    q: np.ndarray
    trivial_events: int

    def diagnostics(self):
        weights=np.diff(self.h.indptr)
        return dict(detectors=self.h.shape[0],faults=self.h.shape[1],observables=self.l.shape[0],
                    h_nnz=self.h.nnz,l_nnz=self.l.nnz,hyperedges=int(np.sum(weights>2)),
                    column_weight_histogram={str(k):v for k,v in Counter(weights.tolist()).items()},
                    undetectable_columns=int(np.sum(weights==0)),trivial_events=self.trivial_events)


def convert_dem(dem: stim.DetectorErrorModel, merge=True):
    events={}; separate=[]; trivial=0
    for op in dem.flattened():
        if op.type!='error': continue
        q=op.args_copy()[0]
        if not np.isfinite(q) or not 0<=q<=1: raise ValueError('invalid DEM probability')
        ds=set(); ls=set()
        for t in op.targets_copy():
            if t.is_separator(): continue
            if t.is_relative_detector_id(): ds.symmetric_difference_update([t.val])
            elif t.is_logical_observable_id(): ls.symmetric_difference_update([t.val])
            else: raise ValueError(f'unsupported DEM error target {t}')
        if not ds and not ls:
            trivial+=1
            continue  # Identity event has no effect on syndrome or logical truth.
        key=(tuple(sorted(ds)),tuple(sorted(ls)))
        if merge:
            old=events.get(key,0.)
            events[key]=old+q-2*old*q
        else: separate.append((key,q))
    entries=list(events.items()) if merge else separate
    hr=[];hc=[];lr=[];lc=[];qs=[]
    for col,((ds,ls),q) in enumerate(entries):
        hr.extend(ds);hc.extend([col]*len(ds));lr.extend(ls);lc.extend([col]*len(ls));qs.append(q)
    shape=(dem.num_detectors,len(qs))
    h=csc_matrix((np.ones(len(hr),dtype=np.uint8),(hr,hc)),shape=shape)
    l=csc_matrix((np.ones(len(lr),dtype=np.uint8),(lr,lc)),shape=(dem.num_observables,len(qs)))
    return FaultModel(h,l,np.array(qs,dtype=float),trivial)
