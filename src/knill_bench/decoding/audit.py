"""Bounded physical-fault witnesses; no graph-distance FT claims."""
from collections import defaultdict
import json
from pathlib import Path
import numpy as np
import stim
from knill_bench.simulation.worker import model,case_id,pack
from knill_bench.data.storage import write_table,atomic_json


def insert_fault(circuit,locations):
    """Replace the specified stochastic Pauli locations by deterministic Paulis."""
    at=defaultdict(list)
    for location in locations:
        if len(location.stack_frames)!=1:raise ValueError('audit requires flattened circuit')
        offset=location.stack_frames[0].instruction_offset
        if location.flipped_measurement is not None:
            raise ValueError('audit expects explicit pre-measurement Pauli noise')
        for item in location.flipped_pauli_product:
            target=item.gate_target
            axis='X' if target.is_x_target else 'Y' if target.is_y_target else 'Z'
            at[offset].append((axis,target.value))
    out=stim.Circuit()
    for i,op in enumerate(circuit.flattened()):
        one=stim.Circuit();one.append(op);out+=one.without_noise()
        for axis,q in at[i]:out.append(axis,[q])
    return out


def audit_run(run,budget=1000):
    if budget<1:raise ValueError('budget must be positive')
    run=Path(run);params=json.loads((run/'parameters.json').read_text());cfg=params['config']
    report=[]
    for case in params['grid']:
        if case['distance'] not in (3,5):continue
        compiled,decoders,aliases,details,converter=model(case,cfg)
        explanations=compiled.circuit.flattened().explain_detector_error_model_errors(reduce_to_one_representative_error=False)
        mechanisms=[];labels=defaultdict(set)
        for event_id,e in enumerate(explanations):
            if not e.circuit_error_locations:continue
            s=np.zeros(compiled.dem.num_detectors,dtype=np.uint8);o=np.zeros(compiled.dem.num_observables,dtype=np.uint8)
            for item in e.dem_error_terms:
                t=item.dem_target
                if t.is_relative_detector_id():s[t.val]^=1
                elif t.is_logical_observable_id():o[t.val]^=1
            labels[pack(s)].add(pack(o));mechanisms.append((event_id,e,s,o))
        # d=3 enumerates every relevant single-Pauli D/L equivalence class and
        # counts all physical locations. d=5 uses a declared diagnostic budget.
        chosen=mechanisms if case['distance']==3 else mechanisms[:budget]
        rows=[];raw_verified=0
        for event_id,e,s,o in chosen:
            representative=e.circuit_error_locations[0]
            faulty=insert_fault(compiled.circuit,[representative])
            raw=faulty.compile_sampler(seed=event_id+901).sample(1)
            ss,oo=converter.convert(measurements=raw,separate_observables=True)
            if not np.array_equal(ss[0],s) or not np.array_equal(oo[0],o):
                raise AssertionError('physical fault witness disagrees with DEM column effect')
            raw_verified+=1
            for name,decoder in decoders.items():
                pred=decoder.decode_one(s,raw[0])
                rows.append(dict(sampling_case_id=case['sampling_case_id'],case_id=case_id(case,name),distance=case['distance'],basis=case['basis'],cycles=case['cycles'],protocol=case['protocol'],
                    event_id=event_id,physical_locations=len(e.circuit_error_locations),fault_weight=1,syndrome=pack(s),actual=pack(o),predicted=pack(pred.logical_flips[0]),
                    decoder_valid=bool(pred.valid[0]),logical_failure=bool(np.any(pred.logical_flips[0]!=o)),undetectable_logical=bool(not s.any() and o.any()),
                    ambiguous_single_fault_syndrome=len(labels[pack(s)])>1,representative_location=str(representative),
                    validation_scope='all_relevant_single_Pauli_classes_one_raw_representative' if case['distance']==3 else 'bounded_single_Pauli_classes'))
        if case['distance']==5 and len(mechanisms)>1:
            rng=np.random.default_rng(102)
            for trial in range(min(budget,32)):
                a,b=rng.choice(len(mechanisms),2,replace=False);ea=mechanisms[a];eb=mechanisms[b]
                s=ea[2]^eb[2];o=ea[3]^eb[3]
                faulty=insert_fault(compiled.circuit,[ea[1].circuit_error_locations[0],eb[1].circuit_error_locations[0]])
                raw=faulty.compile_sampler(seed=trial+1201).sample(1)
                ss,oo=converter.convert(measurements=raw,separate_observables=True)
                assert np.array_equal(ss[0],s) and np.array_equal(oo[0],o)
                for name,decoder in decoders.items():
                    pred=decoder.decode_one(s,raw[0])
                    rows.append(dict(sampling_case_id=case['sampling_case_id'],case_id=case_id(case,name),distance=5,basis=case['basis'],cycles=case['cycles'],protocol=case['protocol'],
                        event_id=trial,physical_locations=2,fault_weight=2,syndrome=pack(s),actual=pack(o),predicted=pack(pred.logical_flips[0]),decoder_valid=bool(pred.valid[0]),
                        logical_failure=bool(np.any(pred.logical_flips[0]!=o)),undetectable_logical=bool(not s.any() and o.any()),ambiguous_single_fault_syndrome=False,
                        representative_location=str(ea[1].circuit_error_locations[0])+'\n'+str(eb[1].circuit_error_locations[0]),validation_scope='bounded_two_fault_witnesses'))
        write_table(run/'data/fault_audit'/f"part-{case['sampling_case_id']}.parquet",'fault_audit',rows,cfg['storage']['compression'])
        report.append(dict(sampling_case_id=case['sampling_case_id'],protocol=case['protocol'],distance=case['distance'],basis=case['basis'],cycles=case['cycles'],
            total_relevant_physical_locations=sum(len(e.circuit_error_locations) for _,e,_,_ in mechanisms),total_equivalence_classes=len(mechanisms),
            raw_single_fault_witnesses=raw_verified,ambiguous_syndromes=sum(len(v)>1 for v in labels.values()),
            decoder_failures={name:sum(r['logical_failure'] or not r['decoder_valid'] for r in rows if r['case_id']==case_id(case,name)) for name in decoders}))
        print(f"audited {case['protocol']} d={case['distance']} {case['basis']} N={case['cycles']}: {raw_verified} single-fault witnesses",flush=True)
    atomic_json(run/'logs/fault_audit.json',dict(cases=report,scope='single-Pauli equivalence-class enumeration; bounded d5 pairs; no FT proof'))
    return str(run/'data/fault_audit')
