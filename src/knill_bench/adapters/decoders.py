from time import perf_counter_ns, process_time_ns
import numpy as np
import pymatching
import stim
from ldpc.bplsd_decoder import BpLsdDecoder
from lomatching import MoMatching
from lomatching.util import get_circuit_subgraph
from knill_bench.decoding.dem import convert_dem
from knill_bench.models import Predictions


class NonmatchableModel(ValueError):
    """Only strict graph decomposition/support failures may trigger fallback."""


def decompose(circuit):
    try:
        dem=circuit.detector_error_model(decompose_errors=True,allow_gauge_detectors=False,approximate_disjoint_errors=False)
    except ValueError as exc:
        if 'Failed to decompose errors' in str(exc):
            raise NonmatchableModel(str(exc)) from exc
        raise
    for op in dem.flattened():
        if op.type!='error': continue
        size=0
        for t in op.targets_copy()+[stim.target_separator()]:
            if t.is_separator():
                if size>2: raise NonmatchableModel('decomposed component has >2 detectors')
                size=0
            elif t.is_relative_detector_id(): size+=1
    return dem


class MatchingAdapter:
    def __init__(self, compiled, kind):
        self.kind=kind
        self.metadata={'edge_correlations':False,'output_kind':'logical_observable_flip_predictions'}
        if kind=='pymatching':
            self.dem=decompose(compiled.circuit)
            self.decoder=pymatching.Matching.from_detector_error_model(self.dem)
            self.metadata['selected_detectors']=list(range(compiled.dem.num_detectors))
        else:
            # Conservative observing-region superset: every check of the selected
            # CSS sector on every block. This includes all records capable of
            # constraining the selected logical Pauli, including both Bell branches.
            # It avoids noise-dependent automatic boundary-edge region discovery.
            basis=compiled.metadata['basis']
            indices=np.array([i for i,v in enumerate(compiled.detectors) if v['sector']==basis],dtype=np.int64)
            sub=get_circuit_subgraph(compiled.circuit,indices)
            self.dem=decompose(sub)
            self.decoder=MoMatching(dem=compiled.dem,dem_subgraphs=[self.dem],det_inds_subgraphs=[indices])
            self.metadata.update(selected_detectors=indices.tolist(),observables=[0],
                                 region_policy='complete_selected_css_sector_superset',
                                 selected_dem=str(self.dem))
        self.metadata['decomposition']='strict_graphlike_components'

    def decode_batch(self, syndromes, measurements=None):
        pred=np.asarray(self.decoder.decode_batch(syndromes),dtype=np.uint8)
        return Predictions(pred,np.ones(len(pred),dtype=bool),[None]*len(pred))

    def decode_one(self, syndrome, measurements=None):
        pred=np.asarray(self.decoder.decode(syndrome),dtype=np.uint8).reshape(1,-1)
        return Predictions(pred,np.ones(1,dtype=bool),[None])


class GlobalBPLSD:
    kind='bplsd_global'
    def __init__(self,dem,params):
        self.model=convert_dem(dem)
        model=self.model
        self.active=np.flatnonzero((np.diff(model.h.indptr)>0)&(model.q>0)&(model.q<1))
        self.fixed=(model.q>=.5).astype(np.uint8)
        self.fixed[self.active]=0
        self.offset_s=np.asarray(model.h@self.fixed%2,dtype=np.uint8)
        self.offset_l=np.asarray(model.l@self.fixed%2,dtype=np.uint8)
        self.h=model.h[:,self.active].tocsc(); self.l=model.l[:,self.active].tocsc()
        options={k:v for k,v in params.items() if k!='kind'}
        self.decoder=BpLsdDecoder(self.h,error_channel=model.q[self.active].tolist(),**options) if len(self.active) else None
        self.metadata=dict(output_kind='logical_observable_flip_predictions',batch_api=False,
                           zero_detector_policy='independent_prior_MAP_each_fault_tie_predict_one',
                           diagnostic_availability=['bp_converged','bp_iterations','residual_weight'],**model.diagnostics())

    def decode_one(self,syndrome,measurements=None,stats=False):
        s=np.asarray(syndrome,dtype=np.uint8)^self.offset_s
        pre=perf_counter_ns(); cpu=process_time_ns()
        if self.decoder is None:
            correction=np.empty(0,dtype=np.uint8)
        else:
            correction=np.asarray(self.decoder.decode(s),dtype=np.uint8)
        wall=perf_counter_ns()-pre; cpu=process_time_ns()-cpu
        post=perf_counter_ns()
        residual=int(np.count_nonzero(np.asarray(self.h@correction%2)^s))
        pred=(np.asarray(self.l@correction%2,dtype=np.uint8)^self.offset_l).reshape(1,-1)
        diag=dict(bp_converged=bool(self.decoder.converge) if self.decoder else None,
                  bp_iterations=int(self.decoder.iter) if self.decoder else None,
                  lsd_used=not bool(self.decoder.converge) if self.decoder else None,
                  recovery_weight=int(np.count_nonzero(correction)),cluster_count=None,
                  backend_wall_ns=wall,backend_cpu_ns=cpu,postprocessing_ns=perf_counter_ns()-post)
        return Predictions(pred,np.array([residual==0]),[residual],[diag])

    def diagnose(self,syndrome):
        if self.decoder is None:
            return {'cluster_count':None,'availability':'no_active_fault_variables'}
        self.decoder.reset_cluster_stats()
        self.decoder.set_do_stats(True)
        try:
            self.decode_one(syndrome)
            stats=self.decoder.statistics
            clusters=stats.get('individual_cluster_stats',{})
            # Diagnostic replay occurs outside all primary decoder-call timers.
            return {'cluster_count':len(clusters),'availability':'ldpc_public_statistics_separate_profiled_replay',
                    'cluster_stats':clusters,'bp_converged':bool(self.decoder.converge),'bp_iterations':int(self.decoder.iter)}
        finally:
            self.decoder.set_do_stats(False)
            self.decoder.reset_cluster_stats()

    def decode_batch(self,syndromes,measurements=None):
        pred=[];valid=[];res=[];diag=[]
        for s in syndromes:
            r=self.decode_one(s)
            pred.append(r.logical_flips[0]);valid.append(r.valid[0]);res+=r.residual;diag+=r.diagnostics
        return Predictions(np.array(pred,dtype=np.uint8),np.array(valid),res,diag)


def construct(compiled,case,cfg):
    result={};aliases={};details={}
    def get(name):
        if name in result: return result[name]
        params=cfg['decoders'][name]
        kind=params['kind']
        if kind=='bplsd_global': obj=GlobalBPLSD(compiled.dem,params)
        elif kind=='hex_native_pipeline':
            from knill_bench.adapters.hex_native import NativeHex
            obj=NativeHex(case,compiled)
        else: obj=MatchingAdapter(compiled,kind)
        result[name]=obj
        return obj
    for name in case['decoders']:
        try:
            get(name); aliases[name]=name
            details[name]={'requested':name,'effective':name,'fallback_reason':None}
        except NonmatchableModel as exc:
            params=cfg['decoders'][name]
            if params['on_nonmatchable']=='error': raise
            fallback=params['fallback_decoder']
            get(fallback);aliases[name]=fallback
            details[name]={'requested':name,'effective':fallback,'fallback_reason':str(exc),
                           'failure_type':'NonmatchableModel'}
    return result,aliases,details
