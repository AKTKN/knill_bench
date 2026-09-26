"""Strict, JSON-compatible configuration with named integer length rules."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import math
import yaml

PROTOCOLS = {'se_memory', 'knill_hex_dminus2', 'knill_aft_postgate', 'knill_aft_prep_only'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()[:24]


def fields(obj, allowed, where):
    if not isinstance(obj, dict):
        raise ValueError(f'{where} must be a mapping')
    unknown = set(obj)-set(allowed.split())
    if unknown:
        raise ValueError(f'{where}: unknown fields {sorted(unknown)}')


def integer(v, where, minimum=1):
    if type(v) is not int or v < minimum:
        raise ValueError(f'{where} must be an integer >= {minimum}')


def choice(v, options, where):
    if v not in options:
        raise ValueError(f'{where} must be one of {options}; got {v!r}')


def load(path):
    return resolve(yaml.safe_load(Path(path).read_text()))


def resolve(raw):
    cfg = copy.deepcopy(raw)
    fields(cfg, 'schema_version experiment noise decoders protocols sampling timing storage diagnostics', 'root')
    if cfg.get('schema_version') != 1:
        raise ValueError('schema_version must be 1')
    e = cfg['experiment']
    fields(e, 'name master_seed output_root code distances bases physical_error_rates cycles cycles_per_distance replicates initial_boundary final_readout comparison', 'experiment')
    e.setdefault('name','knill_bench'); e.setdefault('output_root','results')
    e.setdefault('master_seed',12345); e.setdefault('replicates',1)
    integer(e['master_seed'],'master_seed',0); integer(e['replicates'],'replicates')
    choice(e.setdefault('code','rotated_surface'), ['rotated_surface'], 'code')
    for d in e['distances']:
        integer(d,'distance',3)
        if d % 2 == 0: raise ValueError('distances must be odd')
    for b in e['bases']: choice(b,['x','z'],'basis')
    for p in e['physical_error_rates']:
        if isinstance(p,bool) or not isinstance(p,(int,float)) or not math.isfinite(p) or not 0 <= p <= .5:
            raise ValueError('physical_error_rates must be finite in [0, 0.5]')
    if ('cycles' in e) == ('cycles_per_distance' in e):
        raise ValueError('specify exactly one of cycles or cycles_per_distance')
    for n in e.get('cycles',e.get('cycles_per_distance')): integer(n,'cycles')
    for key in ('distances','bases','physical_error_rates','cycles' if 'cycles' in e else 'cycles_per_distance'):
        if not e[key] or len(set(e[key]))!=len(e[key]): raise ValueError(f'{key} must be nonempty and unique')
    boundary=e.setdefault('initial_boundary',{'kind':'ideal_encoded'})
    fields(boundary,'kind','initial_boundary'); choice(boundary['kind'],['ideal_encoded','noisy_preparation'],'boundary')
    choice(e.setdefault('final_readout','noisy_destructive'),['noisy_destructive'],'final_readout')
    comparison=e.setdefault('comparison',{'kind':'equal_cycles'})
    fields(comparison,'kind target_time','comparison')
    choice(comparison['kind'],['equal_cycles','equal_time'],'comparison')
    if comparison['kind']=='equal_time':
        if not isinstance(comparison.get('target_time'),(int,float)) or comparison['target_time']<=0:
            raise ValueError('equal_time requires positive target_time in noise.time_unit')
    n=cfg.setdefault('noise',{'profile':'hex_legacy'})
    fields(n,'profile multipliers durations time_unit preparation_schedule','noise')
    choice(n['profile'],['hex_legacy','explicit'],'noise.profile')
    if n['profile']=='hex_legacy':
        if set(n)!={'profile'}: raise ValueError('hex_legacy has no configurable rates or duration; use explicit')
        if comparison['kind']=='equal_time': raise ValueError('equal_time requires explicit noise schedule')
    else:
        choice(n.setdefault('preparation_schedule','serial_wait'),['serial_wait'],'preparation_schedule')
        if not isinstance(n.get('time_unit'),str) or not n['time_unit']: raise ValueError('explicit noise requires time_unit')
        for key in ('multipliers','durations'):
            fields(n[key], 'p1 p2 reset measurement idle' if key=='multipliers' else 'p1 p2 reset measurement',key)
            required={'p1','p2','reset','measurement','idle'} if key=='multipliers' else {'p1','p2','reset','measurement'}
            if set(n[key])!=required: raise ValueError(f'{key} requires {sorted(required)}')
            for k,v in n[key].items():
                if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 or (key=='durations' and v==0):
                    raise ValueError(f'{key}.{k} must be finite and {"positive" if key=="durations" else "nonnegative"}')
        for p in e['physical_error_rates']:
            if any(p*v>.5 for v in n['multipliers'].values()): raise ValueError('resolved noise probabilities must be <= 0.5')
    for name, dec in cfg['decoders'].items():
        kind=dec.get('kind')
        if kind=='bplsd_global':
            fields(dec,'kind bp_method max_iter ms_scaling_factor schedule lsd_method lsd_order',f'decoders.{name}')
            defaults=dict(bp_method='minimum_sum',max_iter=100,ms_scaling_factor=.75,schedule='parallel',lsd_method='LSD_0',lsd_order=0)
            for k,v in defaults.items(): dec.setdefault(k,v)
            choice(dec['bp_method'],['minimum_sum','product_sum'],'bp_method')
            choice(dec['schedule'],['parallel','serial'],'schedule')
            choice(dec['lsd_method'],['LSD_0','LSD_E','LSD_CS'],'lsd_method')
            integer(dec['max_iter'],'max_iter'); integer(dec['lsd_order'],'lsd_order',0)
            if dec['lsd_method']=='LSD_0' and dec['lsd_order']!=0: raise ValueError('LSD_0 requires lsd_order=0')
            if not 0 < dec['ms_scaling_factor'] <= 1: raise ValueError('ms_scaling_factor must be in (0,1]')
        elif kind in {'pymatching','lomatching'}:
            fields(dec,'kind on_nonmatchable fallback_decoder',f'decoders.{name}')
            dec.setdefault('on_nonmatchable','error')
            choice(dec['on_nonmatchable'],['error','bplsd_global'],'on_nonmatchable')
            if dec['on_nonmatchable']=='bplsd_global':
                fallback=cfg['decoders'].get(dec.get('fallback_decoder'),{})
                if fallback.get('kind')!='bplsd_global': raise ValueError('fallback_decoder must name a bplsd_global decoder')
        elif kind=='hex_native_pipeline':
            fields(dec,'kind offline_decoder online_decoder final_readout_decoder prior_policy',f'decoders.{name}')
            for k in ('offline_decoder','online_decoder','final_readout_decoder'):
                choice(dec.setdefault(k,'pymatching'),['pymatching'],k)
            choice(dec.setdefault('prior_policy','legacy'),['legacy'],'prior_policy')
        else: raise ValueError(f'unsupported decoder kind {kind!r}')
    ids=[]
    for proto in cfg['protocols']:
        fields(proto,'id decoders prep_rounds post_gate_rounds post_gate_scope','protocol')
        pid=proto['id']; choice(pid,PROTOCOLS,'protocol.id'); ids.append(pid)
        defaults=(0,0) if pid=='se_memory' else ({'rule':'d_minus_2'},0) if pid=='knill_hex_dminus2' else (1,int(pid=='knill_aft_postgate'))
        if proto.setdefault('prep_rounds',defaults[0]) != defaults[0]: raise ValueError(f'{pid} requires prep_rounds={defaults[0]}')
        if proto.setdefault('post_gate_rounds',defaults[1]) != defaults[1]: raise ValueError(f'{pid} requires post_gate_rounds={defaults[1]}')
        choice(proto.setdefault('post_gate_scope','all_active'),['all_active','gate_operands'],'post_gate_scope')
        if not proto['decoders'] or len(set(proto['decoders']))!=len(proto['decoders']): raise ValueError('protocol decoders must be nonempty and unique')
        for dn in proto['decoders']:
            if dn not in cfg['decoders']: raise ValueError(f'unknown decoder {dn}')
            kind=cfg['decoders'][dn]['kind']
            allowed={'pymatching','bplsd_global'} if pid=='se_memory' else {'hex_native_pipeline'} if pid=='knill_hex_dminus2' else {'lomatching','bplsd_global'}
            choice(kind,allowed,f'{pid} decoder')
    if len(set(ids))!=len(ids): raise ValueError('protocol IDs must be unique')
    s=cfg.setdefault('sampling',{})
    fields(s,'workers shots_per_case chunk_size stop_rule max_pending_chunks_per_worker native_threads_per_worker max_shots target_errors time_budget_seconds reference_decoder','sampling')
    for k,v in dict(workers=1,shots_per_case=64,chunk_size=32,max_pending_chunks_per_worker=2,native_threads_per_worker=1).items():
        integer(s.setdefault(k,v),k)
    choice(s.setdefault('stop_rule','fixed_shots'),['fixed_shots','target_errors','time_budget'],'stop_rule')
    if s['stop_rule']!='fixed_shots':
        integer(s.setdefault('max_shots',s['shots_per_case']),'max_shots')
        if s['stop_rule']=='target_errors':
            integer(s.get('target_errors'),'target_errors')
            if not s.get('reference_decoder'): raise ValueError('target_errors requires reference_decoder selected in every protocol')
            if any(s['reference_decoder'] not in p['decoders'] for p in cfg['protocols']): raise ValueError('reference_decoder must be selected in every protocol')
        elif not isinstance(s.get('time_budget_seconds'),(int,float)) or s['time_budget_seconds']<=0:
            raise ValueError('time_budget requires positive time_budget_seconds')
    t=cfg.setdefault('timing',{})
    fields(t,'collect_batch_times latency_sample_count_per_case latency_sampling warmup_shots isolated_replay_workers','timing')
    for k,v in dict(collect_batch_times=True,latency_sample_count_per_case=8,latency_sampling='deterministic_uniform',warmup_shots=4,isolated_replay_workers=1).items(): t.setdefault(k,v)
    for k in ('latency_sample_count_per_case','warmup_shots'): integer(t[k],k,0)
    choice(t['latency_sampling'],['deterministic_uniform'],'latency_sampling')
    integer(t['isolated_replay_workers'],'isolated_replay_workers')
    st=cfg.setdefault('storage',{})
    fields(st,'format compression save_shot_results save_decoder_calls save_all_syndromes retained_failure_samples_per_case retained_uniform_samples_per_case','storage')
    for k,v in dict(format='parquet',compression='zstd',save_shot_results=True,save_decoder_calls=True,save_all_syndromes=False,retained_failure_samples_per_case=8,retained_uniform_samples_per_case=8).items(): st.setdefault(k,v)
    choice(st['format'],['parquet'],'format'); choice(st['compression'],['zstd','snappy','none'],'compression')
    for k in ('retained_failure_samples_per_case','retained_uniform_samples_per_case'): integer(st[k],k,0)
    for obj, keys in ((t,['collect_batch_times']),(st,['save_shot_results','save_decoder_calls','save_all_syndromes'])):
        for k in keys:
            if type(obj[k]) is not bool: raise ValueError(f'{k} must be boolean')
    dg=cfg.setdefault('diagnostics',{})
    fields(dg,'bp_lsd_stats structural_metrics','diagnostics')
    choice(dg.setdefault('bp_lsd_stats','sampled'),['off','sampled'],'bp_lsd_stats')
    if type(dg.setdefault('structural_metrics',True)) is not bool: raise ValueError('structural_metrics must be boolean')
    return cfg


def grid(cfg):
    e=cfg['experiment']
    for d,b,p,n,proto in itertools.product(e['distances'],e['bases'],e['physical_error_rates'],e.get('cycles',e.get('cycles_per_distance')),cfg['protocols']):
        cycles=n if 'cycles' in e else n*d
        case=dict(protocol=proto['id'],distance=d,basis=b,p=float(p),cycles=cycles,
                  prep_rounds=d-2 if proto['id']=='knill_hex_dminus2' else proto['prep_rounds'],
                  post_gate_rounds=proto['post_gate_rounds'],post_gate_scope=proto['post_gate_scope'],
                  initial_boundary=e['initial_boundary'],noise=cfg['noise'],final_readout=e['final_readout'])
        case['rates']={k:float(p)*v for k,v in cfg['noise'].get('multipliers',dict(p1=0,p2=1,reset=1,measurement=1,idle=0)).items()}
        if e['comparison']['kind']=='equal_time':
            # Build actual schedules; choose the largest complete history not exceeding target.
            from knill_bench.circuits.builders import build
            target=e['comparison']['target_time']
            one=build(dict(case,cycles=1)).metadata['elapsed_time']
            two=build(dict(case,cycles=2)).metadata['elapsed_time']
            step=two-one
            cycles=max(1,1+int((target-one)//step))
            case['cycles']=cycles
            actual=build(case).metadata['elapsed_time']
            case['target_time']=target; case['time_mismatch']=actual-target
        case['sampling_case_id']=digest(case)
        case['decoders']=proto['decoders']
        case['decoder_specs']=cfg['decoders']
        yield case
