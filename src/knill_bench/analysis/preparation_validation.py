"""Independent saved-witness algebra/connectivity; no sampling or matching."""
from itertools import product
import numpy as np


def unpack(value, count):
    raw=bytes.fromhex(value) if isinstance(value,str) else value
    if len(raw)!=(count+7)//8:
        raise ValueError('packed witness length disagrees with original model')
    bits=np.unpackbits(np.frombuffer(raw,dtype=np.uint8),bitorder='little')
    if bits[count:].any(): raise ValueError('nonzero witness padding')
    return bits[:count]


def parity(matrix, bits):
    return np.asarray(matrix @ bits).ravel().astype(np.uint8)%2


def temporal_path(h, past, future, difference):
    """BFS in ORIGINAL-column support, independent of matching subdivisions."""
    n=h.shape[0]; adjacency={i:[] for i in range(n+2)}
    for j in np.flatnonzero(difference):
        endpoints=list(h[:,int(j)].nonzero()[0])
        if past[j]: endpoints.append(n)
        if future[j]: endpoints.append(n+1)
        if len(endpoints) not in (0,2): raise ValueError('difference has a non-graphlike open endpoint')
        if endpoints:
            a,b=endpoints;adjacency[a].append((b,int(j)));adjacency[b].append((a,int(j)))
    parents={n:None};queue=[n]
    for node in queue:
        for other,column in adjacency[node]:
            if other not in parents: parents[other]=(node,column);queue.append(other)
    if n+1 not in parents: raise ValueError('difference support contains no past-to-future path')
    node=n+1;columns=[]
    while node!=n:
        node,column=parents[node];columns.append(column)
    return columns[::-1]


def validate_witness(x,z,retained,saved):
    """Check same-solve full witnesses, never substitute a new compact solve."""
    n=x.h_online.shape[1];nz=z.h.shape[1]
    y=unpack(retained['online_x'],x.h_online.shape[0])
    yz=unpack(retained['online_z'],z.h.shape[0])
    xvalid,cvalid,zvalid=(saved[k] for k in ('baseline_valid','complementary_valid','z_decoder_valid'))
    expected='invalid_syndrome' if not xvalid else 'no_complementary_solution' if not cvalid else 'z_decoder_invalid' if not zvalid else 'ok'
    if saved['status']!=expected or (cvalid and not xvalid): raise ValueError('retained validity/status disagreement')
    for key,valid in (('baseline_weight',xvalid),('complementary_weight',cvalid),('gap',cvalid)):
        value=saved[key]
        if valid and (value is None or not np.isfinite(value) or value<0): raise ValueError('invalid retained cost/gap')
        if not valid and value is not None: raise ValueError('unavailable retained cost/gap must be null')
    if cvalid and (saved['complementary_weight']-saved['baseline_weight'])/x.weight_scale!=saved['gap']:
        raise ValueError('retained common-objective gap disagreement')
    if saved['output_mode']!='full_witness':
        if any(k in saved for k in ('baseline_errors','complementary_errors','z_errors')):
            raise ValueError('compact result cannot carry a substituted full witness')
        return dict(status='unavailable',reason='compact mode has no full same-solve witness')
    a=unpack(saved['baseline_errors'],n);b=unpack(saved['complementary_errors'],n)
    ze=unpack(saved['z_errors'],nz)
    if a[x.inactive_columns].any() or b[x.inactive_columns].any() or ze[np.flatnonzero(z.probabilities==0)].any():
        raise ValueError('witness selected an impossible p=0 mechanism')
    frozen=np.intersect1d(x.frozen_columns,x.active_columns)
    if saved['frozen_original_columns']!=frozen.tolist(): raise ValueError('original frozen column order changed')
    if not np.array_equal(unpack(saved['baseline_frozen'],len(frozen)),a[frozen]):
        raise ValueError('saved frozen assignment differs from baseline witness')
    if saved['baseline_valid']:
        if not np.array_equal(parity(x.h_online,a),y): raise ValueError('baseline syndrome constraint failed')
        if int(x.weights@a)!=saved['baseline_weight']: raise ValueError('baseline integer objective failed')
        rows=[i for i,f in enumerate(x.feature_ids) if f.startswith('tau_x:')]
        if not np.array_equal(parity(x.feature_map,a)[rows],unpack(saved['tau_x_prediction'],len(rows))):
            raise ValueError('baseline X feature map failed')
        if bool(x.past@a%2)!=saved['baseline_past'] or bool(x.future@a%2)!=saved['baseline_future']:
            raise ValueError('baseline temporal parity failed')
    if saved['z_decoder_valid']:
        if not np.array_equal(parity(z.h,ze),yz): raise ValueError('known-zero Z syndrome failed')
        features=parity(z.feature_map,ze);rows=[i for i,f in enumerate(z.feature_ids) if f.startswith('tau_z:')]
        if (not np.array_equal(features[rows],unpack(saved['tau_z_prediction'],len(rows)))
                or features[z.feature_ids.index('logical_z')]!=unpack(saved['logical_z_prediction'],1)[0]):
            raise ValueError('known-zero Z/logical feature map failed')
    if not saved['complementary_valid']:
        if saved['gap'] is not None or saved['complementary_weight'] is not None:
            raise ValueError('unavailable complement must have null score/cost')
        return dict(status='pass',path_status='unavailable',reason=saved['status'])
    if not saved['baseline_valid']: raise ValueError('complement without baseline')
    if not np.array_equal(parity(x.h_online,b),y): raise ValueError('complement syndrome constraint failed')
    if not np.array_equal(a[frozen],b[frozen]): raise ValueError('all spatial zero/one assignments must remain fixed')
    delta=a^b
    if (x.past@delta%2,x.future@delta%2)!=(1,1): raise ValueError('both temporal parities must flip')
    cost0,cost1=int(x.weights@a),int(x.weights@b)
    if cost1!=saved['complementary_weight'] or cost1<cost0:
        raise ValueError('complement common integer objective including fixed costs failed')
    if saved['gap']!=(cost1-cost0)/x.weight_scale: raise ValueError('scaled gap disagrees with integer objective')
    path=temporal_path(x.h_online,x.past,x.future,delta)
    return dict(status='pass',path_status='pass',path_original_columns=path,
        path_mechanism_ids=[x.mechanism_ids[j] for j in path],difference_original_columns=np.flatnonzero(delta).tolist(),
        weight0=cost0,weight1=cost1,minimum_claim='constraints/cost checked; optimum established by separate small-graph tests',
        x_active_columns=x.active_columns.tolist(),z_active_columns=z.active_columns.tolist())


def spatial_escape_example():
    """Exhaustive four-variable example: two open ports defeat a P/F-only cut."""
    h=np.array([[1,1,0,0]],dtype=np.uint8);p=np.array([1,0,1,0],dtype=np.uint8)
    f=np.array([0,1,0,1],dtype=np.uint8);w=np.array([5,7,1,1])
    errors=np.array(list(product((0,1),repeat=4)),dtype=np.uint8)
    feasible=(errors@h.T%2).ravel()==0
    opposite=feasible & (errors@p%2==1)&(errors@f%2==1)
    costs=errors@w;loose=errors[np.flatnonzero(opposite)[np.argmin(costs[opposite])]]
    fixed=opposite & ~errors[:,2:].any(axis=1)
    strict=errors[np.flatnonzero(fixed)[np.argmin(costs[fixed])]]
    assert costs[opposite].min()==2 and costs[fixed].min()==12
    return dict(kind='synthetic_exhaustive_graph_not_a_physical_fault',h_online=h.tolist(),past=p.tolist(),future=f.tolist(),
        weights=w.tolist(),frozen_columns=[2,3],baseline=[0]*4,unfrozen=loose.tolist(),fixed=strict.tolist(),
        unfrozen_cost=2,fixed_cost=12,enumerated_assignments=16,
        unfrozen_explanation='two disconnected past/spatial and future/spatial ports; no P-F path',
        fixed_explanation='P--online--F path after freezing every spatial port')
