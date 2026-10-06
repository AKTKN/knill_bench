"""Count-weighted estimates and separately labeled latency/work plots."""
from collections import defaultdict,Counter
from itertools import combinations
import json
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
from knill_bench.data.storage import read_rows,write_table
from knill_bench.config import digest


def wilson(errors,shots,z=1.959963984540054):
    if not shots: return None,None
    p=errors/shots;denom=1+z*z/shots
    center=(p+z*z/(2*shots))/denom
    half=z*np.sqrt(p*(1-p)/shots+z*z/(4*shots*shots))/denom
    return max(0.,float(center-half)),min(1.,float(center+half))


def analyze(run):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    run=Path(run);cases=read_rows(run,'cases');batches=read_rows(run,'decoder_batches');calls=read_rows(run,'decoder_calls')
    cfg=json.loads((run/'parameters.json').read_text())['config']
    by_batch=defaultdict(list);by_call=defaultdict(list)
    for r in batches: by_batch[r['case_id']].append(r)
    for r in calls:
        if r['phase']=='terminal' and r['timing_mode']=='latency' and not r['warmup']: by_call[r['case_id']].append(r)
    summary=[]
    for case in cases:
        meta=json.loads(case['metadata_json']);eff=meta['effective_case_id'];rs=by_batch[eff]
        shots=sum(r['shots'] for r in rs);errors=sum(r['errors'] for r in rs);valid=sum(r['valid'] for r in rs);failed=sum(r['failed'] for r in rs)
        low,high=wilson(errors,valid)
        wall=sum(r['wall_ns'] or 0 for r in rs);cpu=sum(r['cpu_ns'] or 0 for r in rs)
        # Replay observations are shown separately, not pooled with concurrent runs.
        lat=np.array([r['wall_ns'] for r in by_call[eff] if not r['replay']],dtype=float)
        stats=dict(latency_count=len(lat))
        for name,fn in [('mean',np.mean),('std',np.std),('median',np.median),('p90',lambda x:np.quantile(x,.9)),('p95',lambda x:np.quantile(x,.95)),('p99',lambda x:np.quantile(x,.99)),('max',np.max)]:
            stats[f'latency_{name}_ns']=float(fn(lat)) if len(lat) else None
        row={k:case[k] for k in ('case_id','protocol','distance','basis','p','cycles','requested_decoder','effective_decoder')}
        row.update(shots=shots,errors=errors,valid=valid,failed=failed,ler=errors/valid if valid else None,ci_low=low,ci_high=high,
            interval_kind='Wilson_95_fixed_shots' if cfg['sampling']['stop_rule']=='fixed_shots' else 'Wilson_95_descriptive_sequential_not_coverage_guarantee',
            computational_failure_rate=failed/shots if shots else None,total_task_failure_rate=(errors+failed)/shots if shots else None,
            decode_wall_seconds=wall/1e9,decode_cpu_seconds=cpu/1e9,throughput_shots_per_second=shots*1e9/wall if wall else None,
            amortized_wall_ns_per_shot=wall/shots if shots and wall else None,work_ns_per_cycle=wall/shots/case['cycles'] if shots and wall else None,
            peak_live_qubits=meta['peak_live_qubits'],elapsed_time=meta['elapsed_time'],spacetime_volume=meta.get('spacetime_volume'),timing_scope='terminal_full_history_concurrent' if cfg['sampling']['workers']>1 else 'terminal_full_history_one_worker',**stats)
        summary.append(row)
    write_table(run/'summary.parquet','summary',summary,cfg['storage']['compression'])
    disagreement=Counter()
    for r in read_rows(run,'paired_chunks'):
        key=(r['sampling_case_id'],r['first_case_id'],r['second_case_id'])
        for source,target in (('paired_valid_shots','count'),('disagreements','disagreements'),
                              ('first_only_error','first'),('second_only_error','second')):
            disagreement[key,target]+=r[source]
    paired=[]
    for key in sorted({k[0] for k in disagreement}):
        paired.append(dict(sampling_case_id=key[0],first_case_id=key[1],second_case_id=key[2],paired_valid_shots=disagreement[key,'count'],
            disagreements=disagreement[key,'disagreements'],first_only_error=disagreement[key,'first'],second_only_error=disagreement[key,'second']))
    write_table(run/'data/paired_disagreements.parquet','paired_disagreements',paired,cfg['storage']['compression'])
    plots=run/'plots';plots.mkdir(exist_ok=True)
    def finish(fig,name):
        fig.tight_layout();fig.savefig(plots/f'{name}.png',dpi=160);plt.close(fig)
    for basis in ('x','z'):
        fig,ax=plt.subplots(figsize=(9,5))
        groups=defaultdict(list)
        for r in summary:
            if r['basis']==basis and r['ler'] is not None:
                groups[(r['protocol'],r['requested_decoder'],r['distance'],r['cycles'])].append(r)
        for key,rs in groups.items():
            rs.sort(key=lambda x:x['p']);xs=[r['p'] for r in rs];ys=[r['ler'] for r in rs]
            ax.errorbar(xs,ys,yerr=[[max(0,r['ler']-r['ci_low']) for r in rs],[max(0,r['ci_high']-r['ler']) for r in rs]],marker='o',label=f'{key[0]} / {key[1]} d={key[2]} N={key[3]}')
        ax.set(xlabel='Physical sweep parameter p',ylabel=f'{basis.upper()} memory failure probability (95% Wilson)');ax.legend(fontsize=6)
        finish(fig,f'ler_{basis}')
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for r in summary:
        if r['ler'] is not None and r['amortized_wall_ns_per_shot'] is not None:
            label=f"{r['protocol']}/{r['requested_decoder']}"
            axes[0].scatter(r['amortized_wall_ns_per_shot']/1e6,r['ler'],label=label)
            axes[1].scatter(r['peak_live_qubits'],r['ler'])
    axes[0].set(xlabel='Terminal full-history wall work / shot (ms)',ylabel='Memory LER');axes[1].set(xlabel='Peak live physical qubits',ylabel='Memory LER')
    finish(fig,'ler_work_resources')
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    latency_groups=defaultdict(list)
    for c in calls:
        if c['phase']=='terminal' and c['timing_mode']=='latency':latency_groups[(c['backend'],c['replay'],c['concurrent_load'])].append(c['wall_ns']/1e6)
    for key,values in latency_groups.items():
        xs=np.sort(values);axes[0].step(xs,np.arange(1,len(xs)+1)/len(xs),label=str(key))
    axes[0].set(xlabel='Actual terminal invocation wall time (ms)',ylabel='Empirical cumulative probability');axes[0].legend(fontsize=6)
    for r in summary:
        if r['throughput_shots_per_second']: axes[1].scatter(r['distance'],r['throughput_shots_per_second'])
    axes[1].set(xlabel='Distance',ylabel='Batched decoder throughput (shots/s)');finish(fig,'latency_and_throughput')
    fig,ax=plt.subplots(figsize=(8,4));phase=Counter()
    for c in calls:
        if c['backend']=='hex_native_pipeline' and c['timing_mode']=='throughput' and c['phase']!='terminal' and not c['phase'].startswith('backend_'):phase[c['phase']]+=c['wall_ns']/1e6
    ax.bar(list(phase),list(phase.values()));ax.set(ylabel='Summed native batch service time (ms)');finish(fig,'native_cost_breakdown')
    diag=read_rows(run,'diagnostics');fig,axes=plt.subplots(1,2,figsize=(10,4))
    for logical_failure in (False,True):
        values=[r['bp_iterations'] for r in diag if r['kind']=='sampled_decoder' and r['bp_iterations'] is not None and json.loads(r['details_json']).get('logical_failure')==logical_failure]
        if values:axes[0].hist(values,alpha=.5,label=f'logical failure={logical_failure}')
    axes[0].set(xlabel='BP iterations (sampled)',ylabel='Observations');axes[0].legend(fontsize=7)
    struct={r['sampling_case_id']:r for r in diag if r['kind']=='structural'}
    for c,r in zip(cases,summary):
        if r['amortized_wall_ns_per_shot'] is not None:axes[1].scatter(struct[c['sampling_case_id']]['faults'],r['amortized_wall_ns_per_shot']/1e6)
    axes[1].set(xlabel='Undecomposed DEM fault columns',ylabel='Wall work / shot (ms)');finish(fig,'bp_and_model_cost')
    supplemental(run,cases,summary,calls,diag,cfg,finish,plt)
    text=['# Smoke/experiment report','',f"Physical chunks: {len(read_rows(run,'batches'))}. Decoder cases: {len(cases)}.",'',
          'Protocol | Basis | d | Cycles | Decoder | Errors / valid | Computational failures | LER 95% interval',
          '--- | --- | --- | --- | --- | --- | --- | ---']
    for r in summary:
        ci=f"[{r['ci_low']:.4g}, {r['ci_high']:.4g}]" if r['ci_low'] is not None else 'undefined'
        text.append(f"{r['protocol']} | {r['basis']} | {r['distance']} | {r['cycles']} | {r['requested_decoder']} → {r['effective_decoder']} | {r['errors']} / {r['valid']} | {r['failed']} | {ci}")
    text+=['','Terminal full-history memory decoding does not establish an online bounded-latency QEC architecture.',
           'A small smoke experiment is a software check, not a threshold estimate or proof of gadget fault tolerance.',
           'Separate protocol trials are unpaired. Decoder disagreement uses identical physical shots only.',
           'Cluster statistics use separate profiled replays; null values indicate unavailable fields, not zero.']
    (run/'report.md').write_text('\n'.join(text)+'\n')
    return summary


def supplemental(run,cases,summary,calls,diagnostics,cfg,finish,plt):
    """Separate wall/CPU and replay/load strata, with null-aware BP/LSD summaries."""
    timing=defaultdict(list)
    for row in calls:
        if row['phase']=='terminal' and row['timing_mode']=='latency' and not row['warmup'] and not row['profiling']:
            for clock in ('wall','cpu'):
                timing[row['case_id'],row['backend'],row['replay'],row['concurrent_load'],clock].append(row[clock+'_ns'])
    timing_rows=[]
    for key,values in timing.items():
        a=np.asarray(values,dtype=float)
        timing_rows.append(dict(case_id=key[0],backend=key[1],replay=key[2],concurrent_load=key[3],clock=key[4],count=len(a),
            mean_ns=float(np.mean(a)),std_ns=float(np.std(a)),median_ns=float(np.median(a)),p90_ns=float(np.quantile(a,.9)),
            p95_ns=float(np.quantile(a,.95)),p99_ns=float(np.quantile(a,.99)),max_ns=float(np.max(a))))
    write_table(run/'data/latency_statistics.parquet','latency_statistics',timing_rows,cfg['storage']['compression'])
    dg=defaultdict(list)
    for row in diagnostics:
        if row['kind']=='sampled_decoder':dg[row['case_id'],json.loads(row['details_json'])['logical_failure']].append(row)
    diagnostic_rows=[]
    for (cid,failure),rows in dg.items():
        iterations=[r['bp_iterations'] for r in rows if r['bp_iterations'] is not None]
        clusters=[r['cluster_count'] for r in rows if r['cluster_count'] is not None]
        diagnostic_rows.append(dict(case_id=cid,logical_failure=failure,samples=len(rows),bp_counter_samples=len(iterations),
            bp_converged_count=sum(r['bp_converged'] is True for r in rows),lsd_used_count=sum(r['lsd_used'] is True for r in rows),
            mean_bp_iterations=float(np.mean(iterations)) if iterations else None,cluster_counter_samples=len(clusters),mean_cluster_count=float(np.mean(clusters)) if clusters else None))
    write_table(run/'data/decoder_diagnostics_summary.parquet','decoder_diagnostics_summary',diagnostic_rows,cfg['storage']['compression'])
    native=defaultdict(list)
    for row in calls:
        if row['backend']=='hex_native_pipeline' and row['timing_mode']=='throughput':native[row['case_id'],row['phase']].append(row)
    native_rows=[]
    for (cid,phase),rows in native.items():
        native_rows.append(dict(case_id=cid,phase=phase,scope='terminal_full_history',calls=len(rows),shots=sum(r['batch_size'] for r in rows),
            wall_ns=sum(r['wall_ns'] for r in rows),cpu_ns=sum(r['cpu_ns'] for r in rows),
            hierarchy='nested_backend' if phase.startswith('backend_') else 'inclusive_terminal' if phase=='terminal' else 'module_or_frame'))
    write_table(run/'data/native_cost_summary.parquet','native_cost_summary',native_rows,cfg['storage']['compression'])
    structural={r['sampling_case_id']:r for r in diagnostics if r['kind']=='structural'}
    model_rows=[]
    for case,summ in zip(cases,summary):
        d=structural[case['sampling_case_id']]
        metadata=json.loads((run/'models'/f"{case['sampling_case_id']}.metadata.json").read_text())
        dm=metadata['decoder_models'][case['effective_decoder']]
        selected=dm.get('selected_detectors')
        model_rows.append(dict(case_id=case['case_id'],detectors=d['detectors'],faults=d['faults'],hyperedges=d['hyperedges'],
            selected_detectors=len(selected) if selected is not None else None,amortized_wall_ns=summ['amortized_wall_ns_per_shot']))
    write_table(run/'data/model_cost.parquet','model_cost',model_rows,cfg['storage']['compression'])
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    for row in model_rows:
        for ax,key in zip(axes,('faults','hyperedges','selected_detectors')):
            if row[key] is not None and row['amortized_wall_ns'] is not None:ax.scatter(row[key],row['amortized_wall_ns']/1e6)
    for ax,label in zip(axes,('DEM fault variables','Undecomposed hyperedges','Selected matching-subgraph detectors')):
        ax.set(xlabel=label,ylabel='Terminal wall work / shot (ms)')
    finish(fig,'hyperedges_subgraphs_cost')
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    for failure in (False,True):
        rows=[r for r in diagnostic_rows if r['logical_failure']==failure]
        samples=sum(r['bp_counter_samples'] for r in rows)
        if samples:
            axes[0].bar(str(failure),sum(r['bp_converged_count'] for r in rows)/samples)
            axes[1].bar(str(failure),sum(r['lsd_used_count'] for r in rows)/samples)
        cluster_values=[r['cluster_count'] for r in diagnostics if r['kind']=='sampled_decoder' and r['cluster_count'] is not None and json.loads(r['details_json'])['logical_failure']==failure]
        if cluster_values:axes[2].hist(cluster_values,alpha=.5,label=str(failure))
    axes[0].set(xlabel='Logical failure',ylabel='Sampled BP convergence fraction');axes[1].set(xlabel='Logical failure',ylabel='Sampled LSD-use fraction')
    axes[2].set(xlabel='Recorded individual cluster entries',ylabel='Separate diagnostic replay samples');axes[2].legend(title='Logical failure',fontsize=7)
    finish(fig,'convergence_lsd_clusters')
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    scheduled=False
    for r in summary:
        if r['elapsed_time'] is not None and r['ler'] is not None:
            scheduled=True;axes[0].scatter(r['elapsed_time'],r['ler']);axes[1].scatter(r['spacetime_volume'],r['ler'])
    if not scheduled:
        for ax in axes:ax.text(.5,.5,'Time undefined for hex_legacy',ha='center',transform=ax.transAxes)
    axes[0].set(xlabel='Actual scheduled elapsed time (configured unit)',ylabel='LER');axes[1].set(xlabel='Scheduled physical-qubit × time volume',ylabel='LER')
    finish(fig,'elapsed_time_spacetime')
