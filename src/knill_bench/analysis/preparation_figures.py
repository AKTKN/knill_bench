"""Standard Matplotlib scientific exports from typed saved-data summaries."""
import json
import shlex
import textwrap
import numpy as np


def write_figures(out,rates,curves,cases,escape):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    root=out/'figures';root.mkdir()
    distances=sorted({r['distance'] for r in cases.values()})
    caption=('Independent DEM minimum-cost gap; all completed spatial ports fixed to baseline. '
             'Native Hex hex_legacy noise; cut after final Z extraction; ideal suffix evaluation-only.\n'
             'Legend gives R, p, decoder and physical attempts; panels give d. 95% pointwise Wilson intervals; exploratory fixed-R cuts.')
    def label(case):
        n=sum(r['occupancy'] for r in rates if r['case_id']==case['case_id'] and r['metric']=='sign_x' and r['scope']=='metric_valid')
        return f"R={case['rounds']}, p={case['p']:g}, {case['decoder']}, N={n}"
    def save(fig,name,caption_override=None):
        wrapped='\n'.join(textwrap.fill(line,width=max(50,int(fig.get_figwidth()*18)))
            for line in (caption_override or caption).splitlines())
        bottom=(len(wrapped.splitlines())*8.5+12)/(72*fig.get_figheight())+.02
        fig.text(.03,.015,wrapped,fontsize=7,va='bottom')
        fig.tight_layout(rect=(0,bottom,1,1))
        for ext in ('png','pdf','svg'):fig.savefig(root/f'{name}.{ext}',dpi=300,bbox_inches='tight')
        plt.close(fig)
    with plt.rc_context({'font.size':9,'axes.labelsize':10,'pdf.fonttype':42,'svg.fonttype':'none'}):
        fig,axes=plt.subplots(4,len(distances),squeeze=False,figsize=(5*len(distances),11),sharex='col')
        for col,d in enumerate(distances):
            for case in cases.values():
                if case['distance']!=d:continue
                for row,metric in enumerate(('sign_x','sign_z','code_space')):
                    data=[r for r in rates if r['case_id']==case['case_id'] and r['scope']=='metric_valid' and r['metric']==metric and r['bin']>=0 and r['denominator']]
                    x=[r['left'] for r in data];y=np.array([r['rate'] for r in data])
                    axes[row,col].errorbar(x,y,yerr=[y-[r['lower'] for r in data],[r['upper'] for r in data]-y],marker='o',capsize=2,label=label(case))
                    for r in data:axes[row,col].annotate(f"{r['events']}/{r['denominator']}",(r['left'],r['rate']),xytext=(2,5),textcoords='offset points',fontsize=7)
                    axes[row,col].set_ylabel(f'{metric}: shot miss probability');axes[row,col].set_ylim(-.03,1.05)
                occupancy=[r for r in rates if r['case_id']==case['case_id'] and r['metric']=='sign_x' and r['scope']=='metric_valid' and r['bin']>=0]
                axes[3,col].plot([r['left'] for r in occupancy],[r['occupancy'] for r in occupancy],marker='.',label=label(case))
            axes[0,col].set_title(f'd={d}');axes[0,col].legend(fontsize=7)
            axes[3,col].set_xscale('symlog',base=2,linthresh=1)
            axes[3,col].set_xticks([0,1,2,4,8,16,32,64],['0','1','2','4','8','16','32','64'])
            axes[3,col].set_xlabel('gap bin left edge (final bin unbounded)');axes[3,col].set_ylabel('bin occupancy (attempts)')
        save(fig,'gap_sign_risk')
        fig,axes=plt.subplots(1,len(distances),squeeze=False,figsize=(5*len(distances),4.8))
        for col,d in enumerate(distances):
            ax=axes[0,col]
            for case in cases.values():
                if case['distance']!=d:continue
                for scope,style in (('metric_valid','-'),('common_gap_valid','--')):
                    data=[r for r in rates if r['case_id']==case['case_id'] and r['scope']==scope and r['metric']=='logical_z' and r['bin']>=0 and r['denominator']]
                    y=np.array([r['rate'] for r in data]);x=[r['left'] for r in data]
                    ax.errorbar(x,y,yerr=[y-[r['lower'] for r in data],[r['upper'] for r in data]-y],linestyle=style,marker='o',capsize=2,label=label(case)+', '+scope)
                    for r in data:ax.annotate(f"{r['events']}/{r['denominator']}",(r['left'],r['rate']),xytext=(2,5),textcoords='offset points',fontsize=7)
            ax.set_xscale('symlog',base=2,linthresh=1)
            ax.set(title=f'd={d}',xlabel='gap bin left edge',ylabel='logical-Z readout error probability',ylim=(-.03,1.05));ax.legend(fontsize=6)
        save(fig,'gap_logical_risk')
        fig,axes=plt.subplots(3,1,figsize=(9,11))
        for case in cases.values():
            for metric in ('sign_x','code_space','logical_z'):
                data=[r for r in curves if r['case_id']==case['case_id'] and r['metric']==metric and r['Q'] is not None]
                x=np.array([r['A'] for r in data]);y=np.array([r['Q'] for r in data]);name=f"d={case['distance']}, "+label(case)+', '+metric
                axes[0].errorbar(x,y,yerr=[y-[r['Q_lower'] for r in data],[r['Q_upper'] for r in data]-y],marker='.',label=name)
                allcuts=[r for r in curves if r['case_id']==case['case_id'] and r['metric']==metric and r['attempts']]
                axes[1].plot([r['A'] for r in allcuts],[r['U'] for r in allcuts],marker='.',label=name)
            data=[r for r in curves if r['case_id']==case['case_id'] and r['metric']=='sign_x' and r['attempts']]
            axes[2].plot([r['A'] for r in data],[r['rejected_valid']/r['attempts'] for r in data],marker='.',label=label(case)+' valid rejects')
            axes[2].plot([r['A'] for r in data],[r['invalid']/r['attempts'] for r in data],linestyle='--',label=label(case)+' invalid')
        for ax,ylabel in zip(axes,('Q: error / accepted','U: accepted errors / attempts','reject or invalid / attempts')):
            ax.set(xlabel='A: accepted / all physical attempts',ylabel=ylabel,ylim=(-.03,1.05));ax.legend(fontsize=6)
        save(fig,'acceptance_risk')
        fig,axes=plt.subplots(1,2,figsize=(9,4.6))
        coords={'P':(0,1),'v':(1,1),'F':(2,1),'S_P':(0,0),'S_F':(2,0)}
        edges=[('P','v',5),('v','F',7),('P','S_P',1),('F','S_F',1)]
        for ax,selected,title in zip(axes,(escape['unfrozen'],escape['fixed']),('Unfrozen: cost 2, disconnected spatial escape','All spatial ports fixed: cost 12, P–F path')):
            for i,(a,b,w) in enumerate(edges):
                xa,ya=coords[a];xb,yb=coords[b]
                ax.plot([xa,xb],[ya,yb],color='tab:red' if selected[i] else '.75',linewidth=4 if selected[i] else 1)
                ax.text((xa+xb)/2+.04,(ya+yb)/2+.08,f'e{i}: w={w}',fontsize=8)
            for node,(x,y) in coords.items():
                ax.scatter([x],[y],s=100,color='white',edgecolor='black',zorder=3);ax.text(x,y-.17,node,ha='center')
            ax.set_title(title,fontsize=9);ax.set(xlim=(-.4,2.5),ylim=(-.5,1.5));ax.axis('off')
        fig.suptitle('Synthetic exhaustive counterexample, baseline=0000, syndrome=0 (16 assignments)',fontsize=10)
        save(fig,'spatial_freezing_counterexample',caption_override='Synthetic exhaustive graph example, independent of physical sampling. The baseline is 0000; the complement flips P/F and keeps syndrome 0. Freezing ALL degree-one spatial ports (e2,e3) forces a P-F path. Red edges are the selected difference; costs use the same integer weights. No physical fault trajectory or posterior is inferred.')
        examples=json.loads((out/'retained_examples/examples.json').read_text())
        misses=[e for e in examples if e['errors']['sign_x'] and e['gap'] is not None]
        if misses:
            fig,ax=plt.subplots(figsize=(8,4.5))
            ax.bar(range(len(misses)),[e['gap'] for e in misses]);ax.set(xlabel='retained X-sign miss (bounded biased diagnostic set)',ylabel='observed gap')
            ax.set_xticks(range(len(misses)),[f"{e['decoder']}\nr{e['replicate']} c{e['chunk_id']} s{e['shot_index']}" for e in misses],fontsize=6)
            ax.set_title('Actual retained sign misses; not a frequency estimate or proof of impossibility')
            save(fig,'retained_sign_misses')


def write_markdown(run,out,totals,overall,validation,cuts):
    def number(value):return 'undefined' if value is None else f'{value:.6g}'
    text='# Fixed-R preparation validation and saved-data report\n\n'
    summary=json.loads((out/'preparation_summary.json').read_text())
    text+=f"Saved execution status: {summary['status']}; unpublished failed assigned shots: {summary['failed_attempt_assigned_shots_unpublished']}. These are excluded from observed scientific denominators.\n\n"
    text+='The saved-file, online-boundary, model-marginal and available same-solve witness checks passed. '
    text+='This report does not execute repository tests; their exact results are recorded in TEST.md.\n\n'
    text+='For graphlike completed independent DEM terms, Hδ=0, δ_S=0 and Pδ=Fδ=1 imply that the difference support contains a P–F path. '
    text+='All degree-one spatial ports (zeros and ones) are frozen. Additional cycles/multiple paths are allowed. '
    text+='This concerns minimum representatives of an independent DEM model; it does not identify the sampled physical fault, sum posterior classes, or prove fault tolerance.\n\n'
    text+='X/Z sign miss means at least one wrong output check, not a per-check rate. E_code is their OR. '
    text+='Logical-Z readout uses the separate known-zero Z-prefix prediction XOR terminal ideal logical measurement exactly once (prefix_frame_only); sign misses are retained. '
    text+='The handoff cut is after final Z extraction; ideal X MPP/destructive Z are evaluator-only. First X is unanchored; first Z is known zero.\n\n'
    text+='| d | R | physical p | decoder | physical attempts | X misses/valid | Z misses/valid | code misses/valid | logical-Z errors/valid |\n|---|---|---|---|---|---|---|---|---|\n'
    for r in totals:
        text+=f"| {r['distance']} | {r['rounds']} | {r['p']} | {r['decoder']} | {r['shots']} | {r['sign_miss_x']}/{r['baseline_valid']} | {r['sign_miss_z']}/{r['z_decoder_valid']} | {r['code_sign_miss']}/{r['code_valid']} | {r['logical_z_errors']}/{r['logical_valid']} |\n"
    text+='\nEach bin table gives its occupancy, metric-valid denominator, events and a two-sided 95% Wilson score interval. '
    text+='A second common_gap_valid scope requires all three decoder masks. Zero events retain a positive upper bound; empty denominators are null. '
    text+='Invalid/no-complement shots stay in unconditional denominators when their metric is defined and are excluded from acceptance.\n\n'
    text+='A=accepted/all attempts, U=accepted errors/all attempts, Q=accepted errors/accepted. Acceptance requires X baseline, X complement, Z baseline and inclusive gap>=g. '
    text+='threshold_curve.parquet also records invalid and valid-rejected counts separately, intervals for A/U/Q and P(logical-Z error | E_code=0,accept). '
    text+='joint_counts.json stores cells indexed 4*E_X+2*E_Z+E_LZ overall, per bin and per cut. '
    text+='paired_comparisons.json records 00/01/10/11 event counts for variants on the same physical samples, when available. '
    text+='The fixed saved bin edges are 0,1,2,4,8,16,32,64 (left inclusive, last unbounded), plus unavailable scores.\n\n'
    text+='Curves are exploratory offline classification of fixed-shot, fixed-R data. Wilson intervals are pointwise approximate intervals, with no simultaneous or data-selected-threshold coverage guarantee. '
    text+='Gap is not a calibrated posterior log odds; exp(-gap) is not used as a failure probability. '
    text+='X-gap concerns mainly Z-type faults, whereas logical-Z readout depends mainly on X-type faults; flat logical risk can arise from sector separation. '
    text+='Tiny samples cannot establish a gap–risk trend or resolve rare errors; non-observation is not impossibility. No adaptive continuation, teleportation or factory efficiency was measured.\n\n'
    text+='| d | R | p | shots | workers (saved YAML) | chunk | sample ms | X base ms | X comp ms | Z ms | staging I/O ms | parent commit ms | peak RSS MiB | decode shots/s |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n'
    for r in totals:
        m=r['measured_costs'];ms=lambda k:number(m.get(k,0)/1e6)
        text+=f"| {r['distance']} | {r['rounds']} | {r['p']} | {r['shots']} | {r['workers']} | {r['chunk_size']} | {ms('sampling_ns')} | {r['x_baseline_ns']/1e6:.4g} | {r['x_complementary_ns']/1e6:.4g} | {r['z_decode_ns']/1e6:.4g} | {ms('staging_write_ns')} | {ms('parent_commit_ns')} | {m['worker_peak_rss_bytes']/2**20:.3g} | {number(m['decode_shots_per_second'])} |\n"
    text+='\nTimers sum measured chunk phases, may overlap across workers, and are not elapsed wall time. Sampling excludes sampler compilation. Decode excludes setup/warmup/replay/evaluation/I/O. '
    text+='I/O staging and parent commit overlap in scope; do not add them to infer throughput. RSS is the process lifetime high-water mark including imports, not incremental graph memory. '
    text+='Multiple decoders share physical sampling/I/O costs; repeated rows do not represent extra physical attempts. Future efficiency claims require representative budgets and an actual adaptive/factory implementation.\n\n'
    text+=f"Validated retained decoder examples: {validation['retained_examples']}; full witnesses: {validation['full_witness_pass']}; P–F paths: {validation['path_pass']}; compact witnesses unavailable: {validation['compact_witness_unavailable']}. "
    text+='Examples retain original chunk/sample hashes, packed observations/truth and original mechanism path IDs. Full witnesses describe their own solve, including ties; compact witnesses are never replaced by a debug replay. '
    text+='The spatial escape figure is explicitly synthetic exhaustive enumeration; actual retained misses, if any, appear separately and are a biased diagnostic sample.\n\n'
    for name in ('gap_sign_risk','gap_logical_risk','acceptance_risk','spatial_freezing_counterexample'):
        text+=f'![{name}](figures/{name}.png)\n\n'
    args=' '.join('--gap-threshold='+str(v) for v in cuts)
    command=f"bash scripts/python.sh -m knill_bench.cli analyze {shlex.quote(str(run))} --output {shlex.quote(str(out)+'_reanalysis')} {args}"
    text+='Reanalysis (choose a new output directory each time):\n\n```bash\n'+command+'\n```\n\n'
    text+='Machine-readable outputs: conditional_rates.parquet, threshold_curve.parquet, joint_counts.json, paired_comparisons.json, preparation_summary.json, validation_summary.json. '
    text+='Figures are PNG (300 dpi), PDF and SVG. No simulation/config/checkpoint file was changed.\n'
    (out/'report.md').write_text(text)
