# GeomCore test-first foundation

This development branch adds the contract and hostile-input test harness for the geometry layer beneath `diagram-design`.

- 42 top-level diagram types
- 378 semantic visual elements
- 8 defect/positive cases per element = 3,024 cases
- 4 structural stress cases per diagram type = 168 cases
- total generated matrix = **3,192 cases**

Per element: positive, missing, empty payload, duplicate ID, invalid primitive kind, out-of-bounds geometry, non-finite geometry, and feature overflow. Per type: empty diagram, primitive flood, invalid variant, invalid canvas.

Additional deliberately broken semantic tests cover Sankey conservation, Waterfall arithmetic, Polar scale integrity, and Sequence complexity limits.

Run:
```bash
PYTHONPATH=geomcore/src python -m unittest discover -s geomcore/tests -p 'test_*.py' -v
```

The type manifest is the gate: future layout/compiler code is not considered complete unless every declared element remains covered.
