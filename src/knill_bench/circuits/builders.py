"""Shared Hex gates with exact symbolic CSS stabilizer-sign flow.

A sign is a set of measurement indices, combined by symmetric difference.
No sampled error or reference-sample sign is used to construct a detector.
"""
from collections import Counter
import stim
import numpy as np
from knill_bench.codes import Code
from knill_bench.models import CompiledExperiment
from hex_qec.circuit_generation.circuit_generation import (
    qubit_initialisation, qubit_measurement, measure_X_stabilizers_surface_code,
    measure_Z_stabilizers_surface_code, noiseless_unitary_state_prep,
)
from hex_qec.modularisation.module_generation import generate_transversal_cnot_module


class Builder:
    def __init__(self, case):
        self.case = case
        self.code = Code.rotated(case['distance'])
        self.blocks = self.code.blocks(1 if case['protocol'] == 'se_memory' else 2*case['cycles']+1)
        self.c = stim.Circuit()
        self.ledger, self.detectors, self.schedule = [], [], []
        self.signs = {}
        self.pending_detectors = None
        self.se_counts = Counter()
        self.live = {0}
        self.time = 0.0
        self.spacetime = 0.0
        self.physical_schedule = []
        self.layer = 0
        self.round = 0
        self.cycle = -1
        self.obs = set()
        self.noise = case['noise']
        self.p = case['p']

    def add(self, fragment, block, phase, ideal=False):
        start = self.c.num_measurements
        start_time = self.time
        # Hex fragments already carry legacy noise. Explicit profile rebuilds
        # noise from ideal operations once, with serial instruction layers.
        if self.noise['profile'] == 'explicit' and not ideal:
            fragment = self.explicit(fragment.without_noise())
        self.c += fragment
        self.schedule.append(dict(layer=self.layer, cycle=self.cycle, block=block,
                                  phase=phase, start_time=None if self.noise['profile']=='hex_legacy' else start_time,
                                  measurements=self.c.num_measurements-start))
        self.layer += 1
        return start

    def explicit(self, fragment):
        out = stim.Circuit()
        rates = self.case['rates']
        durations = self.noise['durations']
        # Serial two-qubit gate schedule: Stim may coalesce repeated-qubit pairs
        # into one instruction, so instruction boundaries are not time layers.
        scheduled = []
        for instruction in fragment:
            targets = instruction.targets_copy()
            if instruction.name in {'CX', 'CZ'}:
                scheduled.extend(stim.CircuitInstruction(instruction.name, targets[i:i+2], instruction.gate_args_copy()) for i in range(0, len(targets), 2))
            else:
                scheduled.append(instruction)
        for op in scheduled:
            ts = op.targets_copy()
            if op.name in {'DETECTOR', 'OBSERVABLE_INCLUDE', 'QUBIT_COORDS', 'TICK'}:
                continue
            qs = [t.value for t in ts]
            is_m = op.name in {'M','MX','MR','MRX'}
            is_r = op.name in {'R','RX','MR','MRX'}
            kind = 'measurement' if is_m else 'reset' if is_r else 'p2' if op.name in {'CX','CZ'} else 'p1'
            if is_m:
                out.append('Z_ERROR' if op.name.endswith('X') else 'X_ERROR', qs, rates['measurement'])
            out.append(op)
            if is_r:
                out.append('Z_ERROR' if op.name.endswith('X') else 'X_ERROR', qs, rates['reset'])
            elif not is_m and op.name != 'I':
                out.append('DEPOLARIZE2' if kind=='p2' else 'DEPOLARIZE1', qs, rates[kind])
            duration = durations[kind]
            active = set(q for b in self.live for values in self.blocks[b].values() for q in values)
            idle = sorted(active - set(qs))
            if idle and rates['idle']:
                # Depolarizing channels compose by multiplying Bloch shrinkage.
                idle_p = .75*(1-(1-4*rates['idle']/3)**duration)
                out.append('DEPOLARIZE1', idle, idle_p)
            out.append('TICK')
            self.physical_schedule.append(dict(start=self.time, duration=duration, operation=op.name, targets=qs, active_blocks=sorted(self.live), idle_qubits=idle))
            self.spacetime += duration*len(active)
            self.time += duration
        return out

    def record(self, start, block, basis, operation, count, qubits):
        indices = list(range(start, start+count))
        for i, (r, q) in enumerate(zip(indices, qubits)):
            self.ledger.append(dict(record=r, cycle=self.cycle, block=block, basis=basis,
                                    operation=operation, index=i, qubit=q, logical_layer=self.layer,
                                    se_round=self.round, physical_time=None if self.noise['profile']=='hex_legacy' else self.time))
        return indices

    def detector(self, records, block, sector, check, phase):
        records = sorted(records)
        if self.pending_detectors is not None:
            self.pending_detectors.append(dict(records=records,block=block,sector=sector,check=check,phase=phase))
            return
        self.c.append('DETECTOR', [stim.target_rec(r-self.c.num_measurements) for r in records],
                      [block, 0 if sector=='x' else 1, check, self.layer])
        self.detectors.append(dict(block=block, sector=sector, check=check, records=records, phase=phase))

    def initialize(self, b, basis, ideal=False):
        self.live.add(b)
        frag = stim.Circuit()
        if ideal:
            frag.append('R',self.blocks[b]['data_qubits'])
            frag += noiseless_unitary_state_prep(self.code.matrices, basis, 0)
        else:
            qubit_initialisation(frag, basis, self.blocks[b], self.p)
        self.add(frag, b, 'initial_ideal' if ideal else 'reset', ideal=ideal)
        for sector, h in zip(('x','z'), self.code.matrices[:2]):
            self.signs[b, sector] = [set() if ideal or basis==sector else None for _ in range(h.shape[0])]

    def se(self, b, phase):
        self.round += 1
        self.se_counts[f'{b}:{phase}'] += 1
        for sector, fn, stabs in zip(('x','z'), (measure_X_stabilizers_surface_code, measure_Z_stabilizers_surface_code), self.code.stabilizers[:2]):
            frag = stim.Circuit()
            fn(frag, stabs, self.blocks[b], self.p)
            start = self.add(frag, b, phase)
            recs = self.record(start, b, sector, phase, len(stabs), self.blocks[b][sector+'_ancillas'])
            signs = self.signs[b, sector]
            for k, r in enumerate(recs):
                if signs[k] is not None:
                    self.detector(signs[k] ^ {r}, b, sector, k, phase)
                signs[k] = {r}

    def cx(self, control, target):
        frag = generate_transversal_cnot_module(self.p, self.blocks[control]['data_qubits'], self.blocks[target]['data_qubits']).circuit
        self.add(frag, [control,target], 'transversal_cnot')
        # Eigenvalues of output X_c and Z_t are products of input signs.
        self.signs[control,'x'] = [a ^ b for a,b in zip(self.signs[control,'x'],self.signs[target,'x'])]
        self.signs[target,'z'] = [a ^ b for a,b in zip(self.signs[control,'z'],self.signs[target,'z'])]

    def measure(self, b, basis, phase):
        frag = stim.Circuit()
        qubit_measurement(frag, basis, self.blocks[b], self.p)
        start = self.add(frag, b, phase)
        recs = self.record(start, b, basis, phase, self.code.distance**2, self.blocks[b]['data_qubits'])
        h = self.code.matrices[0 if basis=='x' else 1]
        for k in range(h.shape[0]):
            parity = {recs[i] for i in h.getrow(k).indices}
            self.detector(parity ^ self.signs[b,basis][k], b, basis, k, phase)
        self.live.remove(b)
        logical = self.code.matrices[2 if basis=='x' else 3].indices
        return {recs[i] for i in logical}

    def build(self):
        case = self.case
        self.initialize(0, case['basis'], ideal=case['initial_boundary']['kind']=='ideal_encoded')
        if case['initial_boundary']['kind']=='noisy_preparation':
            for _ in range(case['distance']):
                self.se(0, 'initial_boundary')
        d = 0
        if case['protocol']=='se_memory':
            for j in range(case['cycles']):
                self.cycle=j
                self.se(0,'memory')
        else:
            for j in range(case['cycles']):
                self.cycle=j
                a,b = 2*j+1,2*j+2
                for block,basis in ((a,'z'),(b,'x')):
                    self.initialize(block,basis)
                    for _ in range(case['prep_rounds']):
                        self.se(block,'preparation')
                for control in (b,d):
                    self.cx(control,a)
                    if case['post_gate_rounds']:
                        scope = sorted(self.live) if case['post_gate_scope']=='all_active' else [control,a]
                        self.pending_detectors=[]
                        for block in scope:
                            self.se(block,'post_gate')
                        pending=self.pending_detectors
                        self.pending_detectors=None
                        by_key={(r['block'],r['sector'],r['check']):set(r['records']) for r in pending}
                        # Express the round comparison in the pre-gate frame:
                        # delta_pre = T_CX^{-1} delta_output, with T_CX^{-1}=T_CX.
                        # Transform detector rows only; measured output signs are
                        # retained unchanged for the next circuit layer.
                        for row in pending:
                            records=set(row['records'])
                            if row['sector']=='x' and row['block']==control:
                                records ^= by_key[a,'x',row['check']]
                            if row['sector']=='z' and row['block']==a:
                                records ^= by_key[control,'z',row['check']]
                            self.detector(records,row['block'],row['sector'],row['check'],row['phase'])
                mx = self.measure(d,'x','bell')
                mz = self.measure(a,'z','bell')
                self.obs ^= mx if case['basis']=='x' else mz
                d=b
        self.obs ^= self.measure(d,case['basis'],'final_readout')
        self.c.append('OBSERVABLE_INCLUDE',[stim.target_rec(r-self.c.num_measurements) for r in sorted(self.obs)],0)
        assert sorted(r['record'] for r in self.ledger)==list(range(self.c.num_measurements))
        if not self.c.has_flow(stim.Flow(measurements=sorted(self.obs))):
            raise ValueError('terminal observable fails signed stabilizer backpropagation')
        dem = self.c.detector_error_model(allow_gauge_detectors=False, approximate_disjoint_errors=False)
        # Strict extraction independently checks the boundary and all relations.
        counts = Counter()
        for op in self.c.flattened():
            counts[op.name] += len(op.targets_copy()) // (2 if op.name in {'CX','CZ','DEPOLARIZE2'} else 1)
        noise_counts={k:v for k,v in counts.items() if k in {'X_ERROR','Z_ERROR','Y_ERROR','DEPOLARIZE1','DEPOLARIZE2'}}
        metadata = dict(noise_location_counts=noise_counts,
                        total_two_qubit_gates=counts.get('CX',0)+counts.get('CZ',0),
                        total_one_qubit_gates=sum(counts.get(k,0) for k in ('H','S','X','Y','Z')),
                        se_counts=dict(self.se_counts), schedule=self.schedule, operation_counts=dict(counts),
                        peak_live_blocks=1 if case['protocol']=='se_memory' else 3,
                        peak_live_qubits=(1 if case['protocol']=='se_memory' else 3)*(2*case['distance']**2-1),
                        allocated_simulator_qubits=self.c.num_qubits,
                        data_qubits_per_block=case['distance']**2, check_qubits_per_block=case['distance']**2-1,
                        total_block_preparations=len(self.blocks), elapsed_time=self.time if self.noise['profile']=='explicit' else None,
                        time_unit=self.noise.get('time_unit'), physical_schedule=self.physical_schedule,
                        spacetime_volume=self.spacetime if self.noise['profile']=='explicit' else None, detector_basis='pre_gate_round_comparisons_with_css_sign_flow',
                        coordinates=self.code.coordinates(), boundary_frame='raw_signs_retained_terminal_observable',
                        decoding_scope='terminal_full_history', edge_correlations=False)
        return CompiledExperiment(self.c,dem,self.ledger,self.detectors,sorted(self.obs),metadata)


def build(case):
    return Builder(case).build()
