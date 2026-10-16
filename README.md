# knill_bench

Reproducible physical Stim memory experiments comparing repeated surface-code syndrome extraction with three Knill strategies. The package uses the requested Hex checkout and user-owned LOM/surface-sim forks. It keeps circuit identity, decoder choice, classical work, and live hardware resources separate.

The `auxiliary-system` branch also supplies independent **schema-v2
experiments**: strict d/p-only configurations, compact provenance, streamed
point-level Parquet output and the **B1 eight-cycle Fig.4(d) runner**.
See [the v2 contract](docs/auxiliary_v2.md) and [the Fig.4(d) guide](docs/fig4d.md).
Factory execution remains B2. Existing commands below retain schema-v1 behavior.

```bash
bash scripts/bootstrap.sh
source .venv/bin/activate
bash scripts/run_simulation.sh configs/smoke.yaml
python -m knill_bench.cli analyze results/<run-directory>
python -m knill_bench.cli benchmark-latency results/<run-directory> --workers 1
```

The smoke configuration has distances 3/5, X/Z memories, one/two cycles, 64 shots per physical point, two workers, and four timed individual calls per case. The larger benchmark is supplied but is never launched by bootstrap or tests.

| Stable protocol | Fresh A/B preparation | Post-CNOT SE | Intended decoder |
|---|---|---|---|
| `se_memory` | None | One ordinary X/Z SE round per memory cycle | Full-history PyMatching; selectable global BP-LSD |
| `knill_hex_dminus2` | Exactly d−2 rounds each | None | Native Hex preparation repair, Bell decoding, frame propagation, final decoding |
| `knill_aft_postgate` | One round each | One full X/Z round on **D, A, B after each CNOT** | LOM; selectable global BP-LSD |
| `knill_aft_prep_only` | One round each | None | LOM; selectable global BP-LSD |

Each Knill cycle executes `CX(B,A)`, optional SE, `CX(D,A)`, optional SE, then `MX(D)` and `MZ(A)`. B becomes the new memory. Ancilla preparation does not insert SE on D. The optional `gate_operands` scope is labeled separately in every case.

```bash
python -m knill_bench.cli validate-config configs/benchmark.yaml
python -m knill_bench.cli build configs/benchmark.yaml
python -m knill_bench.cli run configs/benchmark.yaml   # deliberate larger run
python -m knill_bench.cli resume results/<run-directory> --workers 2
python -m knill_bench.cli validate-references
python -m knill_bench.cli audit-faults results/<run-directory> --budget 12
python -m pytest -q
```

`build` writes circuit/model artifacts without sampling. `run` creates a new UTC timestamped directory. `resume` retains chunk identities and validates configuration, source, package, model, and environment compatibility. Worker count may change. Source changes require a new run. Analysis can be repeated; isolated timing replay appends separately labeled observations from retained uniform samples.

See [design](docs/design.md), [dependency provenance](docs/dependencies.md), [schemas](docs/data_schema.md), and [validation evidence](docs/validation.md). [Implementation report](docs/implementation_report.md) records the final smoke results and limitations.

Terminal full-history memory decoding does not by itself establish an online bounded-latency QEC architecture. The preparation length d−2 is an experimental choice, not a guarantee of gadget fault tolerance. Small smoke runs cannot establish thresholds or asymptotic exponents.


## Schema-v2 experiments

```bash
.venv/bin/knill-bench-v2 validate-config configs/fig4d_v2_example.yaml
.venv/bin/knill-bench-v2 validate-config configs/logical_zero_factory_v2_example.yaml
.venv/bin/knill-bench-v2 prepare configs/logical_zero_factory_v2_example.yaml
# Deliberate production sweep; not a smoke test:
bash scripts/run_fig4d.sh configs/fig4d.yaml
.venv/bin/knill-bench-v2 resume results/<fig4d-run>
.venv/bin/knill-bench-v2 plot-fig4d results/<fig4d-run> --output fig4d.png
```

`prepare` creates `{UTC-timestamp}_{experiment-name}/config.yaml` and one
`metadata.json`, with pending points and no physical sampling. Fig.4(d) `run`
uses d preparation rounds on both resources, eight full Knill stages and
noisy final readout. It streams one logical-error Parquet file per d/p and
records actual shot/error counts. The explicit production p grid is approximate;
the saved-data plot uses 95% Agresti-Coull intervals. Factory `run` reports
the B2 boundary before output creation. Parent metadata marks complete points.

Hex is pinned to completed H5 `4278d29`; its source/version is untouched.
See [TEST.md](TEST.md) for regression results and
[the package map](src/knill_bench/DOCS.md) and [v2 contract](docs/auxiliary_v2.md)
for APIs, exact schemas, seeds, provenance, crash recovery and limits.
