# knill_bench

Reproducible physical Stim memory experiments comparing repeated surface-code syndrome extraction with three Knill strategies. The package uses the requested Hex checkout and user-owned LOM/surface-sim forks. It keeps circuit identity, decoder choice, classical work, and live hardware resources separate.

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
