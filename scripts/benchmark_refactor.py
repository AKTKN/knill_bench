"""Reproducible setup/sampling/decoder benchmark; also runs against the parent commit.

Example: PYTHONPATH=/path/to/checkout/src .venv/bin/python scripts/benchmark_refactor.py \
    --protocol knill_aft_postgate --distance 7 --cycles 21 --shots 16
"""
import argparse
import hashlib
import json
import resource
import tempfile
import time
from pathlib import Path
import yaml

from knill_bench.config import load,grid
from knill_bench.circuits.builders import build
from knill_bench.adapters.decoders import construct
from knill_bench.simulation.runner import prepare
from knill_bench.data.provenance import sha


def rss_bytes():
    for line in Path('/proc/self/status').read_text().splitlines():
        if line.startswith('VmRSS:'):return int(line.split()[1])*1024
    return None


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--protocol',choices=('se_memory','knill_hex_dminus2','knill_aft_postgate','knill_aft_prep_only'),required=True)
    parser.add_argument('--distance',type=int,default=7)
    parser.add_argument('--cycles',type=int,required=True)
    parser.add_argument('--shots',type=int,default=16)
    parser.add_argument('--mode',choices=('prepare','profile','sampling'),default='profile')
    args=parser.parse_args()
    cfg=load(Path(__file__).parents[1]/'configs/smoke.yaml')
    cfg['experiment'].update(distances=[args.distance],bases=['z'],cycles=[args.cycles],physical_error_rates=[.001])
    cfg['protocols']=[p for p in cfg['protocols'] if p['id']==args.protocol]
    if args.mode=='prepare':
        with tempfile.TemporaryDirectory() as directory:
            cfg['experiment']['output_root']=directory
            config=Path(directory)/'config.yaml';config.write_text(yaml.safe_dump(cfg))
            begin=time.perf_counter_ns();run=prepare(config)
            model_meta=json.loads(next((run/'models').glob('*.metadata.json')).read_text())
            print(json.dumps(dict(mode='prepare',protocol=args.protocol,distance=args.distance,cycles=args.cycles,
                setup_seconds=(time.perf_counter_ns()-begin)/1e9,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                case_count=len(list((run/'circuits').glob('*.stim'))),
                setup_timing=model_meta.get('setup_timing'),
                graph_bytes=sum(p.stat().st_size for p in (run/'models').glob('*.graph.dem')))))
        return
    case=next(grid(cfg))
    begin=time.perf_counter_ns();compiled=build(case);build_ns=time.perf_counter_ns()-begin
    if args.mode=='sampling':
        seed=4321
        begin=time.perf_counter_ns();raw=compiled.circuit.compile_sampler(seed=seed).sample(args.shots)
        raw_sampling_ns=time.perf_counter_ns()-begin
        begin=time.perf_counter_ns();syndrome,observable=compiled.circuit.compile_m2d_converter().convert(
            measurements=raw,separate_observables=True)
        conversion_ns=time.perf_counter_ns()-begin
        begin=time.perf_counter_ns();direct_syndrome,direct_observable=compiled.circuit.compile_detector_sampler(
            seed=seed).sample(shots=args.shots,separate_observables=True)
        direct_sampling_ns=time.perf_counter_ns()-begin
        import numpy as np
        print(json.dumps(dict(mode='sampling',protocol=args.protocol,distance=args.distance,
            cycles=args.cycles,shots=args.shots,build_ns=build_ns,raw_sampling_ns=raw_sampling_ns,
            conversion_ns=conversion_ns,direct_sampling_ns=direct_sampling_ns,
            detector_equal=bool(np.array_equal(syndrome,direct_syndrome)),
            observable_equal=bool(np.array_equal(observable,direct_observable)),
            raw_bytes=raw.nbytes,detector_bytes=syndrome.nbytes,observable_bytes=observable.nbytes)))
        return
    compiled.metadata['basis']=case['basis']
    after_build=rss_bytes()
    begin=time.perf_counter_ns();decoders,aliases,details=construct(compiled,case,cfg)
    construct_ns=time.perf_counter_ns()-begin;after_model=rss_bytes()
    physical_seed=4321
    begin=time.perf_counter_ns();raw=compiled.circuit.compile_sampler(seed=physical_seed).sample(args.shots)
    sampling_ns=time.perf_counter_ns()-begin
    begin=time.perf_counter_ns();syndromes,obs=compiled.circuit.compile_m2d_converter().convert(measurements=raw,separate_observables=True)
    conversion_ns=time.perf_counter_ns()-begin
    predictions={};times={};native_phases={}
    for name,decoder in decoders.items():
        begin=time.perf_counter_ns();prediction=decoder.decode_batch(syndromes,raw)
        times[name]=time.perf_counter_ns()-begin
        if getattr(decoder,'kind',None)=='hex_native_pipeline':
            for event in getattr(decoder,'events',[]):
                native_phases[event['phase']]=native_phases.get(event['phase'],0)+event['wall_ns']
        predictions[name]=dict(predictions_sha256=hashlib.sha256(prediction.logical_flips.tobytes()).hexdigest(),
            valid_sha256=hashlib.sha256(prediction.valid.tobytes()).hexdigest(),
            residual_sha256=hashlib.sha256(json.dumps(prediction.residual).encode()).hexdigest(),
            errors=int(((prediction.logical_flips!=obs).any(axis=1)&prediction.valid).sum()))
    print(json.dumps(dict(mode='profile',protocol=args.protocol,distance=args.distance,cycles=args.cycles,shots=args.shots,
        sampling_case_id=case['sampling_case_id'],circuit_hash=sha(str(compiled.circuit)),model_hash=sha(str(compiled.dem)),
        build_ns=build_ns,decoder_construct_ns=construct_ns,sampling_ns=sampling_ns,conversion_ns=conversion_ns,
        native_phase_wall_ns=native_phases,
        decoder_sparse_matrix_bytes={name:getattr(decoder,'sparse_matrix_bytes',None) for name,decoder in decoders.items()},
        decode_ns=times,after_build_rss_bytes=after_build,model_rss_delta_bytes=after_model-after_build,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        raw_bytes=raw.nbytes,detector_bytes=syndromes.nbytes,observable_bytes=obs.nbytes,
        raw_sha256=hashlib.sha256(raw.tobytes()).hexdigest(),
        detector_sha256=hashlib.sha256(syndromes.tobytes()).hexdigest(),
        observable_sha256=hashlib.sha256(obs.tobytes()).hexdigest(),aliases=aliases,
        fallback={k:v['fallback_reason'] for k,v in details.items()},predictions=predictions)))


if __name__=='__main__':main()
