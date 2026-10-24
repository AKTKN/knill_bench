"""Preparation describe/construct delegation; no live graphs during describe."""
from pathlib import Path
from time import perf_counter_ns
import json

from knill_bench.config import digest
from knill_bench.decoding.preparation_model import compile_preparation_boundary_model, compile_preparation_prefix_model
from knill_bench.decoding.preparation_prefix import PrefixDemModel
from knill_bench.decoding.temporal_artifact import read_temporal_model
from .temporal_gap import TemporalGapDecoder, describe_temporal_models


def describe(compiled,case,cfg):
    start=perf_counter_ns(); models={}; graphs={}; cache={}
    for name in case['decoders']:
        params=cfg['decoders'][name]; scale=params['weight_scale']
        if scale not in cache:
            cache[scale]=(compile_preparation_boundary_model(compiled,weight_scale=scale),
                          compile_preparation_prefix_model(compiled,weight_scale=scale))
        x,z=cache[scale]
        models[name]=describe_temporal_models(x,z,output_mode=params['output_mode'])
        graphs[name]=(x,z)
    aliases={n:n for n in case['decoders']}
    details={n:dict(requested=n,effective=n,fallback_reason=None) for n in case['decoders']}
    return aliases,details,models,graphs,dict(preparation_model_compile_ns=perf_counter_ns()-start)


def construct(runtime,case,cfg):
    root=Path(runtime.metadata['model_artifact_root']).resolve(); result={}
    for name in case['decoders']:
        descriptor=runtime.metadata['decoder_models'][name]
        paths={}
        for sector in ('x','z'):
            path=(root/descriptor[f'{sector}_artifact']).resolve()
            if path.parent!=root: raise ValueError('unsafe preparation model artifact path')
            paths[sector]=path
        x=read_temporal_model(paths['x'],expected_sha256=descriptor['definition']['x_model_sha256'])
        z=PrefixDemModel.from_artifact(json.loads(paths['z'].read_text()))
        if z.model_sha256!=descriptor['definition']['z_model_sha256']:
            raise ValueError('saved Z-prefix model identity changed')
        params=cfg['decoders'][name]
        if params['weight_scale']!=x.weight_scale:
            raise ValueError('saved preparation model scale conflicts with configuration')
        decoder=TemporalGapDecoder(x,z,output_mode=params['output_mode'])
        if decoder.model_sha256!=descriptor['model_sha256']:
            raise ValueError('saved preparation decoder definition changed')
        result[name]=decoder
    return result,{n:n for n in result},runtime.metadata['decoder_details']
