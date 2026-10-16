# Saved-data analysis (schema v1)

`report.py` aggregates existing v1 tables, Wilson intervals, timing and paired
statistics, then writes optional report/plots. `plotting.py` loads v1 LERs,
validates grouping/filter choices and plots saved summaries. It does not
resimulate data. The authoritative current v1 schema is
[data/storage.py](../data/storage.py) and [the schema guide](../../../docs/data_schema.md).

B0 changes no analysis Python. V2 has exactly one/two point tables and compact
metadata, described in [the v2 guide](../../../docs/auxiliary_v2.md). Fig.4(d)
Agresti-Coull plotting belongs to B1; factory acceptance/first-rejection/cost
analysis belongs to B3. No v1 Wilson result or old d-2 protocol is advertised
as a Fig.4(d) reproduction. Truth may label errors, never select confidence.
