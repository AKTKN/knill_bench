"""Bounded saved-data gap/risk reports. No sampler or decoder is constructed."""
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from knill_bench.data.preparation import GAP_EDGES
from knill_bench.data.storage import atomic_json, read_rows, file_sha256
from knill_bench.decoding.temporal_artifact import read_temporal_model
from knill_bench.decoding.preparation_prefix import PrefixDemModel
from .confidence import WilsonInterval
from .preparation_validation import unpack, validate_witness, spatial_escape_example

METRICS=('sign_x','sign_z','code_space','logical_z','logical_z_given_code_correct')
FIELDS=('sign_miss_x','sign_miss_z','code_sign_miss','logical_z_error')


def blank():
    return dict(shots=0,eligible=0,invalid_reasons=dict(x_baseline=0,no_complement=0,z_decoder=0),
        **{s:dict(**{m:dict(shots=0,errors=0) for m in METRICS},joint_counts=[0]*8,joint_denominator=0)
           for s in ('unconditional','selected')})


def add(target,source):
    for k in ('shots','eligible'): target[k]+=source[k]
    for k in target['invalid_reasons']: target['invalid_reasons'][k]+=source['invalid_reasons'][k]
    for scope in ('unconditional','selected'):
        for metric in METRICS:
            for k in ('shots','errors'): target[scope][metric][k]+=source[scope][metric][k]
        target[scope]['joint_denominator']+=source[scope]['joint_denominator']
        target[scope]['joint_counts']=[a+b for a,b in zip(target[scope]['joint_counts'],source[scope]['joint_counts'])]


def check_summary(s):
    n=s['shots'];eligible=s['eligible']
    if type(n) is not int or not 0<=eligible<=n: raise ValueError('invalid assigned/eligible denominator')
    for value in s['invalid_reasons'].values():
        if type(value) is not int or not 0<=value<=n: raise ValueError('invalid reason count')
    for scope in ('unconditional','selected'):
        t=s[scope];j=t['joint_counts']
        if len(j)!=8 or any(type(v) is not int or v<0 for v in j) or sum(j)!=t['joint_denominator']:
            raise ValueError('joint contingency counts disagree')
        for metric in METRICS:
            m=t[metric]
            if not all(type(m[k]) is int for k in ('shots','errors')) or not 0<=m['errors']<=m['shots']<=n:
                raise ValueError('metric event/valid denominator disagrees')
            if scope=='selected' and metric!='logical_z_given_code_correct' and m['shots']!=eligible:
                raise ValueError('common valid denominator disagrees')
        if t['code_space']['shots']!=sum(j): raise ValueError('code/joint denominator disagrees')
        if t['code_space']['errors']!=sum(j[2:]): raise ValueError('code/joint events disagree')
        if t['logical_z_given_code_correct']['shots']!=j[0]+j[1] or t['logical_z_given_code_correct']['errors']!=j[1]:
            raise ValueError('code-correct logical denominator disagrees')


def from_shots(rows, threshold=-np.inf):
    """Recompute event counters from nullable compact columns, never truth/graphs."""
    result=blank();result['shots']=len(rows)
    for r in rows:
        x,z,c=r['baseline_valid'],r['z_decoder_valid'],r['complementary_valid']
        if not all(type(v) is bool for v in (x,z,c)) or (c and not x): raise ValueError('invalid compact masks')
        expected='invalid_syndrome' if not x else 'no_complementary_solution' if not c else 'z_decoder_invalid' if not z else 'ok'
        if r['status']!=expected: raise ValueError('compact status disagrees with masks')
        for field,valid in zip(FIELDS,(x,z,x and z,z)):
            if (r[field] is None)!= (not valid): raise ValueError('compact null event disagrees with mask')
        if x and z and r['code_sign_miss']!=(r['sign_miss_x'] or r['sign_miss_z']):
            raise ValueError('compact full-code error disagrees with CSS events')
        for key,valid in (('baseline_weight',x),('complementary_weight',c),('gap',c)):
            value=r[key]
            if valid and (value is None or not np.isfinite(value) or value<0): raise ValueError('invalid compact score/cost')
            if not valid and value is not None: raise ValueError('unavailable compact score must be null')
        eligible=x and z and c
        selected=eligible and r['gap']>=threshold
        result['eligible']+=int(selected)
        for reason,hit in (('x_baseline',not x),('no_complement',x and not c),('z_decoder',not z)):
            result['invalid_reasons'][reason]+=int(hit)
        for scope,mask in (('unconditional',True),('selected',selected)):
            if not mask:continue
            table=result[scope]
            for metric,field,valid in zip(METRICS,FIELDS,(x,z,x and z,z)):
                if valid:
                    table[metric]['shots']+=1;table[metric]['errors']+=int(r[field])
            if x and z:
                index=4*int(r['sign_miss_x'])+2*int(r['sign_miss_z'])+int(r['logical_z_error'])
                table['joint_counts'][index]+=1;table['joint_denominator']+=1
                if not r['code_sign_miss']:
                    table['logical_z_given_code_correct']['shots']+=1
                    table['logical_z_given_code_correct']['errors']+=int(r['logical_z_error'])
    return result



def interval(k,n):
    lo,hi=WilsonInterval().bounds(int(k),int(n))
    return dict(rate=k/n if n else None,lower=float(lo) if n else None,upper=float(hi) if n else None)


def _typed(path,rows,fields):
    schema=pa.schema(fields,metadata={b'preparation_analysis_version':b'1',b'interval':b'Wilson_95_pointwise_fixed_shots'})
    pq.write_table(pa.Table.from_pylist(rows,schema=schema),path,compression='zstd')


def _audit_model(run,case):
    """Recheck saved online record boundary and same-X/all-label marginal."""
    import stim
    from knill_bench.decoding.temporal_validation import compare_marginal_models
    meta=json.loads(case['metadata_json']);sid=case['sampling_case_id'];rows=meta['detectors'];ledger=meta['ledger']
    cut=meta['output_cut'];rounds=case['rounds']
    if meta['physical_se_rounds']!=rounds or meta['offline_completion_sampled'] or meta['terminal_recovery']:
        raise ValueError('physical rounds/output convention disagrees')
    circuit=stim.Circuit.from_file(str(run/'circuits'/meta['production_circuit']))
    prefix=circuit[:cut['instruction_count']];suffix=circuit[cut['instruction_count']:]
    if prefix.num_measurements!=cut['measurement_count'] or any(op.name not in {'MPP','M','OBSERVABLE_INCLUDE'} for op in suffix):
        raise ValueError('evaluation suffix contains noise or wrong physical cut')
    for sector in ('x','z'):
        selected=[r for r in rows if r['sector']==sector]
        expected_rounds=range(2,rounds+1) if sector=='x' else range(1,rounds+1)
        checks=len(meta['evaluation_labels'][f'tau_{sector}'])
        if [(r['round_index'],r['check_index']) for r in selected]!=[(r,j) for r in expected_rounds for j in range(checks)]:
            raise ValueError('unknown first X anchor or missing known-zero Z anchor/order')
        if [r['detector_id'] for r in selected]!=meta['sample_map'][f'online_{sector}_detector_ids']:
            raise ValueError('sampler/decoder online row map disagrees')
        for r in selected:
            records=[ledger[i] for i in r['record_ids']]
            expected=[1] if r['round_index']==1 else [r['round_index']-1,r['round_index']]
            if ([v['round_index'] for v in records]!=expected or any(v['source']!='se' or v['sector']!=sector
                    or v['check_index']!=r['check_index'] or v['record_id']>=cut['measurement_count'] for v in records)):
                raise ValueError('online detector contains evaluator or wrong-prefix records')
    if {r['round_index'] for r in ledger if r['source']=='se'}!=set(range(1,rounds+1)):
        raise ValueError('physical SE ledger does not contain exactly R rounds')
    certificate=compare_marginal_models(stim.DetectorErrorModel.from_file(str(run/'models'/f'{sid}.nominal.dem')),
        stim.DetectorErrorModel.from_file(str(run/'models'/f'{sid}.completed.dem')),
        production_detector_ids=meta['online_x_detector_ids'],
        completed_detector_ids=[r['detector_id'] for r in meta['completed_detectors'] if r['role']=='online'],
        production_observable_ids=list(range(circuit.num_observables)),completed_observable_ids=list(range(circuit.num_observables)))
    desc=meta['decoder_models'][case['decoder']]
    x=read_temporal_model(run/'models'/desc['x_artifact'],expected_sha256=desc['definition']['x_model_sha256'])
    z=PrefixDemModel.from_artifact(json.loads((run/'models'/desc['z_artifact']).read_text()))
    if z.model_sha256!=desc['definition']['z_model_sha256'] or z.scope!='known_zero_Z_prefix_v1':
        raise ValueError('saved separate Z-prefix identity disagrees')
    if z.detector_ids!=tuple(meta['online_z_detector_ids']): raise ValueError('Z-prefix detector map disagrees')
    return meta,x,z,certificate


def analyze_saved(run, *, output=None, thresholds=None):
    """Write a NEW explicit analysis directory; immutable published input files."""
    run=Path(run).resolve()
    cuts=tuple([-np.inf,*GAP_EDGES,np.inf] if thresholds is None else thresholds)
    if not cuts or any(isinstance(v,bool) or not isinstance(v,(int,float)) or np.isnan(v) for v in cuts) or len(set(cuts))!=len(cuts):
        raise ValueError('thresholds must be distinct real numbers, not NaN')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out=Path(output).resolve() if output is not None else run/'analysis'/f'{stamp}_{uuid.uuid4().hex[:8]}'
    if out==run or any(out.is_relative_to(run/k) for k in ('data','models','circuits','checkpoints','staging','logs')):
        raise ValueError('analysis output must be a separate analysis directory')
    out.mkdir(parents=True,exist_ok=False)
    identity=dict(analysis_version=1,run=str(run),output=str(out),thresholds=['-inf' if v==-np.inf else '+inf' if v==np.inf else v for v in cuts],
        interval='two-sided Wilson 95%, no continuity correction, fixed-shot pointwise',
        threshold_interpretation='exploratory offline curves; no simultaneous or data-selected-cut coverage',
        objective='common integer minimum independent-DEM representative cost difference / weight_scale',
        freezing='all degree-one completed spatial ports fixed to baseline, including zeros',
        logical_evaluation='prefix_frame_only: known-zero Z prediction XOR ideal logical-Z readout exactly once',
        physical_cut='after final Z extraction; ideal suffix evaluation-only',
        no_physical_fault_lift=True,source_hashes={p.name:file_sha256(p) for p in
            (Path(__file__),Path(__file__).with_name('preparation_validation.py'),Path(__file__).with_name('preparation.py'),Path(__file__).with_name('preparation_figures.py'),Path(__file__).with_name('confidence.py'))})
    try:
        rows=_analyze(run,out,cuts,identity)
    except Exception as error:
        atomic_json(out/'validation_summary.json',dict(identity,status='fail',failure_reason=str(error)))
        (out/'report.md').write_text(f'# Preparation analysis failed\n\n{error}\n')
        raise
    return rows,out


def _analyze(run,out,cuts,identity):
    from .preparation import summarize
    totals=summarize(run,out)  # validates artifact/checkpoint hashes first
    parameters=json.loads((run/'parameters.json').read_text());cfg=parameters['config']
    compact=cfg['storage']['save_shot_results']
    if not compact and any(v not in (-np.inf,np.inf,*GAP_EDGES) for v in cuts):
        raise ValueError('aggregate-only reports require saved gap-bin edges (or +/-inf); arbitrary cuts need compact shots')
    cases={c['case_id']:c for c in read_rows(run,'preparation_cases')}
    models={cid:_audit_model(run,c) for cid,c in cases.items()}
    bins=defaultdict(blank);overall=defaultdict(blank);selected=defaultdict(blank);pairs={};examples=[]
    model_checks={cid:dict(status='pass',test_identity='saved_online_cut_and_X_all_label_marginal_plus_known_zero_Z_v1',
        source_hashes=m[0]['source_hashes'],x_graph_hash=m[1].artifact_sha256,z_graph_hash=m[2].model_sha256,
        marginal=m[3]) for cid,m in models.items()}
    for ckpath in sorted((run/'checkpoints').glob('*.json')):
        ck=json.loads(ckpath.read_text());parts=lambda table:run/'data'/table/f'part-{ckpath.stem}.parquet'
        chunks=pq.read_table(parts('preparation_chunks')).to_pylist()
        shot_rows=pq.read_table(parts('preparation_shots')).to_pylist() if compact else []
        bycase=defaultdict(list);shot_lookup={}
        for r in shot_rows:shot_lookup[r['case_id'],r['shot_index']]=r
        for r in shot_rows:bycase[r['case_id']].append(r)
        for row in chunks:
            cid=row['case_id'];s=json.loads(row['summary_json']);check_summary(s)
            if s['shots']!=ck['shots']:raise ValueError('chunk summary/physical count mismatch')
            for field,metric in zip(('sign_miss_x','sign_miss_z','code_sign_miss','logical_z_errors'),METRICS):
                if row[field]!=s['unconditional'][metric]['errors']:raise ValueError('chunk metric column/count disagreement')
            add(overall[cid],s);entries=json.loads(row['gap_bins_json']);combined=blank()
            if [v['bin'] for v in entries]!=list(range(-1,len(GAP_EDGES))):raise ValueError('missing/duplicate gap bins')
            for b in entries:
                check_summary(b['summary']);add(combined,b['summary']);add(bins[cid,b['bin']],b['summary'])
                if b['bin']==-1 and b['summary']['eligible']:raise ValueError('unavailable gap cannot be accepted')
            expected=blank();add(expected,s)
            if combined!=expected:raise ValueError('gap bins do not partition chunk counters')
            if compact:
                shots=bycase.pop(cid,[])
                start=ck['chunk_id']*parameters['batch_partition']
                if sorted(r['shot_index'] for r in shots)!=list(range(start,start+ck['shots'])) or any(
                    r['sampling_case_id']!=ck['sampling_case_id'] or r['replicate']!=ck['replicate'] or r['chunk_id']!=ck['chunk_id'] for r in shots):
                    raise ValueError('compact row identity/count mismatch')
                recomputed=from_shots(shots)
                if recomputed!=expected:raise ValueError('compact events disagree with aggregate counts')
                for b in entries:
                    subset=[r for r in shots if (-1 if r['gap'] is None else int(np.searchsorted(GAP_EDGES,r['gap'],side='right')-1))==b['bin']]
                    small=blank();add(small,b['summary'])
                    if from_shots(subset)!=small:raise ValueError('compact gap bins disagree with aggregate counts')
                scale=models[cid][1].weight_scale
                for r in shots:
                    if r['complementary_valid'] and (r['complementary_weight']-r['baseline_weight'])/scale!=r['gap']:
                        raise ValueError('compact common-objective scaled gap disagrees')
                for cut in cuts:add(selected[cid,cut],from_shots(shots,cut))
            else:
                for cut in cuts:
                    for b in entries:
                        if b['bin']>=0 and b['left']>=cut:add(selected[cid,cut],b['summary'])
            for pair in s.get('paired_comparisons',[]):
                key=(row['sampling_case_id'],pair['left'],pair['right'],pair['metric'])
                if len(pair['counts'])!=4 or sum(pair['counts'])!=pair['jointly_valid'] or any(type(v) is not int or v<0 for v in pair['counts']):
                    raise ValueError('paired event counts disagree')
                target=pairs.setdefault(key,[0]*4);pairs[key]=[a+b for a,b in zip(target,pair['counts'])]
        if bycase:raise ValueError('unexpected compact decoder case')
        for retained in pq.read_table(parts('preparation_retained')).to_pylist():
            if retained['sample_hash']!=ck['sample_hash'] or retained['sampling_case_id']!=ck['sampling_case_id'] or not (
                    ck['chunk_id']*parameters['batch_partition']<=retained['shot_index']<ck['chunk_id']*parameters['batch_partition']+ck['shots']):
                raise ValueError('retained original chunk identity mismatch')
            for name,saved in json.loads(retained['decoder_results_json']).items():
                cid=saved['case_id'];meta,x,z,_=models[cid]
                if retained['circuit_hash']!=meta['circuit_hash'] or retained['maps_hash']!=meta['maps_hash'] or saved['model_sha256']!=cases[cid]['model_hash']:
                    raise ValueError('retained source/model identity mismatch')
                if saved['output_mode']!=meta['decoder_models'][name]['definition']['output_mode']:
                    raise ValueError('retained same-mode decoder identity disagrees')
                witness=validate_witness(x,z,retained,saved)
                # Truth is joined only AFTER all graph checks, for example labels.
                tx=unpack(retained['truth_tau_x'],len(meta['evaluation_labels']['tau_x']))
                tz=unpack(retained['truth_tau_z'],len(meta['evaluation_labels']['tau_z']))
                lx=unpack(saved['tau_x_prediction'],len(tx));lz=unpack(saved['tau_z_prediction'],len(tz))
                errors=dict(sign_x=bool(np.any(tx^lx)) if saved['baseline_valid'] else None,
                    sign_z=bool(np.any(tz^lz)) if saved['z_decoder_valid'] else None,
                    logical_z=bool((unpack(retained['truth_logical_z'],1)^unpack(saved['logical_z_prediction'],1))[0]) if saved['z_decoder_valid'] else None)
                if compact:
                    shot=shot_lookup.get((cid,retained['shot_index']))
                    if shot is None or any(shot[k]!=saved[k] for k in ('gap','baseline_weight','complementary_weight','status','baseline_valid','complementary_valid','z_decoder_valid')):
                        raise ValueError('retained correction disagrees with original compact row')
                    if any(shot[field]!=errors[metric] for field,metric in (('sign_miss_x','sign_x'),('sign_miss_z','sign_z'),('logical_z_error','logical_z'))):
                        raise ValueError('retained truth/prediction events disagree with compact row')
                examples.append(dict(case_id=cid,decoder=name,replicate=retained['replicate'],chunk_id=retained['chunk_id'],
                    shot_index=retained['shot_index'],sample_hash=retained['sample_hash'],reason=retained['reason'],gap=saved['gap'],
                    errors=errors,witness=witness,original={k:(v.hex() if isinstance(v,bytes) else v) for k,v in retained.items()}))
    rates=[];curves=[];joint=[]
    common=[('case_id',pa.string()),('distance',pa.int64()),('rounds',pa.int64()),('p',pa.float64()),('decoder',pa.string())]
    def base(cid):return {k:cases[cid][k] for k,_ in common}
    for cid in cases:
        for index in range(-1,len(GAP_EDGES)):
            counts=bins[cid,index]
            for scope in ('unconditional','selected'):
                for metric in METRICS:
                    m=counts[scope][metric]
                    rates.append(dict(base(cid),bin=index,left=GAP_EDGES[index] if index>=0 else None,
                        right=GAP_EDGES[index+1] if 0<=index<len(GAP_EDGES)-1 else None,
                        occupancy=counts['shots'],scope='metric_valid' if scope=='unconditional' else 'common_gap_valid',
                        metric=metric,denominator=m['shots'],events=m['errors'],**interval(m['errors'],m['shots'])))
                joint.append(dict(base(cid),kind='bin',bin=index,scope=scope,counts=counts[scope]['joint_counts']))
        for cut in cuts:
            counts=selected[cid,cut];n=overall[cid]['shots'];accepted=counts['eligible'];invalid=n-overall[cid]['eligible']
            for metric in METRICS:
                m=counts['selected'][metric];k=m['errors'];den=m['shots']
                curves.append(dict(base(cid),threshold=float(cut),metric=metric,attempts=n,accepted=accepted,invalid=invalid,
                    rejected_valid=n-invalid-accepted,events=k,conditional_denominator=den,
                    A=accepted/n if n else None,A_lower=interval(accepted,n)['lower'],A_upper=interval(accepted,n)['upper'],
                    U=k/n if n else None,U_lower=interval(k,n)['lower'],U_upper=interval(k,n)['upper'],
                    Q=interval(k,den)['rate'],Q_lower=interval(k,den)['lower'],Q_upper=interval(k,den)['upper']))
            joint.append(dict(base(cid),kind='threshold',threshold='-inf' if cut==-np.inf else '+inf' if cut==np.inf else cut,
                counts=counts['selected']['joint_counts']))
        for scope in ('unconditional','selected'):
            joint.append(dict(base(cid),kind='overall',scope=scope,counts=overall[cid][scope]['joint_counts']))
    _typed(out/'conditional_rates.parquet',rates,common+[(k,t) for k,t in
        [('bin',pa.int64()),('left',pa.float64()),('right',pa.float64()),('occupancy',pa.int64()),('scope',pa.string()),
         ('metric',pa.string()),('denominator',pa.int64()),('events',pa.int64()),('rate',pa.float64()),('lower',pa.float64()),('upper',pa.float64())]])
    _typed(out/'threshold_curve.parquet',curves,common+[(k,pa.string() if k=='metric' else pa.int64() if k in
        {'attempts','accepted','invalid','rejected_valid','events','conditional_denominator'} else pa.float64()) for k in
        ('threshold','metric','attempts','accepted','invalid','rejected_valid','events','conditional_denominator','A','A_lower','A_upper','U','U_lower','U_upper','Q','Q_lower','Q_upper')])
    atomic_json(out/'joint_counts.json',joint)
    atomic_json(out/'paired_comparisons.json',dict(available=bool(pairs),reason='saved paired 2x2 event counts; cells 00,01,10,11' if pairs else
        'one decoder or historical aggregate data without paired counters; no independent-sample difference inferred',
        comparisons=[dict(sampling_case_id=k[0],left=k[1],right=k[2],metric=k[3],counts=v,disagreements=v[1]+v[2]) for k,v in pairs.items()]))
    (out/'retained_examples').mkdir()
    atomic_json(out/'retained_examples/examples.json',examples)
    escape=spatial_escape_example();atomic_json(out/'retained_examples/spatial_escape.json',escape)
    for row in totals:
        points=[json.loads(p.read_text()) for p in (run/'checkpoints').glob('*.json') if json.loads(p.read_text())['sampling_case_id']==row['sampling_case_id']]
        row['workers']=cfg['sampling']['workers'];row['chunk_size']=cfg['sampling']['chunk_size']
        row['measured_costs']['staging_write_ns']=sum(p.get('staging_write_ns',0) for p in points)
        row['measured_costs']['parent_commit_ns']=sum(p.get('parent_commit_ns',0) for p in points)
    document=json.loads((out/'preparation_summary.json').read_text())
    document.update(cases=totals,logical_evaluation='prefix_frame_only')
    atomic_json(out/'preparation_summary.json',document)
    validation=dict(identity,status='pass',failure_reason=None,saved_model_checks=model_checks,
        retained_examples=len(examples),full_witness_pass=sum(e['witness']['status']=='pass' for e in examples),
        path_pass=sum(e['witness'].get('path_status')=='pass' for e in examples),
        compact_witness_unavailable=sum(e['witness']['status']=='unavailable' for e in examples),
        compact_aggregate_counts='pass' if compact else 'not available: aggregate-only run',
        independent_synthetic_enumeration=dict(status='pass',assignments=escape['enumerated_assignments']),
        repository_deterministic_tests='not executed by analysis; exact commands/results are recorded in TEST.md',
        run_artifact_hashes=json.loads((run/'manifest.json').read_text())['preparation_artifacts'])
    atomic_json(out/'validation_summary.json',validation)
    from .preparation_figures import write_figures, write_markdown
    write_figures(out,rates,curves,cases,escape)
    write_markdown(run,out,totals,overall,validation,cuts)
    return totals
