"""Bounded two-protocol, multi-worker interruption/resume memory check."""
import argparse
import json
import os
import resource
import tempfile
import threading
from pathlib import Path
import yaml

from knill_bench.config import load
from knill_bench.simulation.runner import prepare,execute_run
from knill_bench.analysis.report import analyze
from knill_bench.data.storage import read_rows


def rss(pid):
    try:lines=(Path('/proc')/str(pid)/'status').read_text().splitlines()
    except OSError:return None
    for line in lines:
        if line.startswith('VmRSS:'):return int(line.split()[1])*1024
    return None


def children(pid):
    try:return [int(x) for x in (Path('/proc')/str(pid)/'task'/str(pid)/'children').read_text().split()]
    except OSError:return []


class RssMonitor:
    """Sample concurrent RSS on Linux; no extra runtime dependency."""
    def __init__(self):
        self.stop=threading.Event();self.parent_peak=0;self.worker_peak=0;self.total_peak=0
        self.thread=threading.Thread(target=self.sample,daemon=True)
    def __enter__(self):self.thread.start();return self
    def __exit__(self,*_):self.stop.set();self.thread.join()
    def sample(self):
        import os
        while not self.stop.is_set():
            parent=rss(os.getpid()) or 0
            pending=children(os.getpid());workers=[]
            while pending:
                pid=pending.pop();workers.append(rss(pid) or 0);pending.extend(children(pid))
            self.parent_peak=max(self.parent_peak,parent)
            self.worker_peak=max(self.worker_peak,max(workers,default=0))
            self.total_peak=max(self.total_peak,parent+sum(workers))
            self.stop.wait(.02)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--distance',type=int,default=7)
    parser.add_argument('--cycles',type=int,default=7)
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--shots',type=int,default=12)
    parser.add_argument('--chunk-size',type=int,default=4)
    args=parser.parse_args()
    cfg=load(Path(__file__).parents[1]/'configs/smoke.yaml')
    cfg['experiment'].update(distances=[args.distance],bases=['z'],cycles=[args.cycles],physical_error_rates=[.001])
    cfg['protocols']=[p for p in cfg['protocols'] if p['id'] in ('knill_hex_dminus2','knill_aft_postgate')]
    cfg['sampling'].update(workers=args.workers,shots_per_case=args.shots,chunk_size=args.chunk_size,
                           max_pending_chunks_per_worker=1,model_cache_size=1)
    cfg['timing']['latency_sample_count_per_case']=0
    cfg['storage'].update(save_shot_results=False,retained_uniform_samples_per_case=2,
                          retained_failure_samples_per_case=2)
    with tempfile.TemporaryDirectory() as directory,RssMonitor() as monitor:
        cfg['experiment']['output_root']=directory
        path=Path(directory)/'config.yaml';path.write_text(yaml.safe_dump(cfg))
        run=prepare(path)
        parent_after_prepare=rss(os.getpid())
        execute_run(run,max_new_chunks=1)
        parent_after_interrupt=rss(os.getpid())
        assert json.loads((run/'manifest.json').read_text())['status']=='interrupted'
        execute_run(run)
        parent_after_resume=rss(os.getpid())
        assert json.loads((run/'manifest.json').read_text())['status']=='complete'
        batches=read_rows(run,'batches')
        keys={(r['sampling_case_id'],r['replicate'],r['chunk_id']) for r in batches}
        expected=len(cfg['protocols'])*((args.shots+args.chunk_size-1)//args.chunk_size)
        assert len(keys)==len(batches)==expected
        assert not read_rows(run,'shots')
        assert all(len([r for r in read_rows(run,'retained_samples') if r['sampling_case_id']==sid])<=4
                   for sid in {r['sampling_case_id'] for r in batches})
        summary=analyze(run)
        assert summary
        checkpoints=[json.loads(p.read_text()) for p in (run/'checkpoints').glob('*.json')]
        by_case={}
        for row in batches:
            by_case.setdefault(row['sampling_case_id'],{}).setdefault(row['pid'],[]).append(row)
        per_case_worker_rss={sid:{str(pid):max(r.get('worker_rss_bytes') or 0 for r in checkpoints
            if r['sampling_case_id']==sid and (r['replicate'],r['chunk_id']) in
            {(b['replicate'],b['chunk_id']) for b in rows}) for pid,rows in pids.items()}
            for sid,pids in by_case.items()}
        pids_by_case=[set(pids) for pids in by_case.values()]
        shared_case_worker_pids=sorted(set.intersection(*pids_by_case)) if pids_by_case else []
        setup=[c['setup_timing'] for c in checkpoints if c.get('setup_timing')]
        print(json.dumps(dict(distance=args.distance,cycles=args.cycles,workers=args.workers,
            shots_per_case=args.shots,chunk_size=args.chunk_size,
            chunks=len(checkpoints),summary_rows=len(summary),
            parent_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            sampled_parent_peak_rss_bytes=monitor.parent_peak,
            sampled_total_peak_rss_bytes=monitor.total_peak,
            parent_rss_after_prepare_bytes=parent_after_prepare,
            parent_rss_after_interrupt_bytes=parent_after_interrupt,
            parent_rss_after_resume_bytes=parent_after_resume,
            worker_peak_rss_bytes=max(c['worker_peak_rss_bytes'] for c in checkpoints),
            sampled_worker_peak_rss_bytes=monitor.worker_peak,
            model_rss_delta_bytes=[s['model_rss_delta_bytes'] for s in setup],
            first_worker_decoder_construct_ns=[s['decoder_construct_ns'] for s in setup],
            decoder_sparse_matrix_bytes=[s['decoder_sparse_matrix_bytes'] for s in setup],
            active_chunk_rss_delta_bytes=max(c['active_chunk_rss_delta_bytes'] or 0 for c in checkpoints),
            max_ipc_payload_bytes=max(c['ipc_payload_bytes'] for c in checkpoints),
            max_staged_bytes=max(c['staged_bytes'] for c in checkpoints),
            max_staging_write_ns=max(c['staging_write_ns'] for c in checkpoints),
            max_parent_commit_ns=max(c['parent_commit_ns'] for c in checkpoints),
            per_case_worker_rss_bytes=per_case_worker_rss,
            shared_case_worker_pids=shared_case_worker_pids,
            raw_chunk_bytes=sorted(set(c['raw_chunk_bytes'] for c in checkpoints)),
            detector_chunk_bytes=sorted(set(c['detector_chunk_bytes'] for c in checkpoints)))))


if __name__=='__main__':main()
