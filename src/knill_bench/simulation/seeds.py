import hashlib
import numpy as np
from knill_bench.config import canonical


def seed(master,case_id,replicate,chunk,stream='physical'):
    blob=canonical([1,master,case_id,replicate,chunk,stream]).encode()
    return int.from_bytes(hashlib.sha256(blob).digest()[:8],'little')


def selected_indices(master,case_id,replicate,total,count,stream):
    rng=np.random.default_rng(seed(master,case_id,replicate,0,stream))
    return set(rng.choice(total,size=min(total,count),replace=False).tolist())
