# Reproducibility Guide — DERF

## Requirements
- Python 3.10+ (tested on 3.14.4)
- No external dependencies (stdlib only)

## Verify the Core Mechanism
```bash
python derf_poc.py              # Basic demonstration
python derf_gate.py             # Comprehensive test suite (9/9 tests)
python derf_benchmark.py        # Performance benchmarks (10/10 scenarios)
python derf_alt_impl.py         # Alternative Warshall implementation + comparison
python derf_mutation_test.py    # Mutation testing (10 mutations, ≥90% detected)
```

## Expected Output (last lines)
- `derf_poc.py`: `Pipeline success : True` / `Evidence written to: .../derf_evidence.json`
- `derf_gate.py`: `GATE VERDICT: PASS`
- `derf_benchmark.py`: `Correctness rate    : 100.0% (10/10)`
- `derf_alt_impl.py`: `Replication agree: True`
- `derf_mutation_test.py`: `Mutation score: 90%` or higher

## Verification Time
All scripts complete in under 5 seconds on a standard machine.

## Evidence Files Generated
| File | Contents |
|------|----------|
| `derf_evidence.json` | PoC pipeline evidence |
| `derf_gate_results.json` | Gate PASS/FAIL + timings + versioning |
| `derf_benchmark_results.json` | 10 scenarios + scalability + memory |
| `derf_replication_evidence.json` | Matrix vs DAG agreement |
| `derf_mutation_results.json` | Mutation score + per-mutation catch |

## Author
Agim Haxhijaha · ORCID 0009-0002-3234-7765 · Independent Researcher

## REALITY_FORGE additions (v2.2.0)

```bash
python derf_realworld.py
python derf_stress.py
```

Expect EXIT 0 and JSON evidence/results beside the scripts. Deploy reference: `derf_deploy_manifest.json`.

## INVENTION_CRYSTALLIZATION (v2.3.0)

```bash
from derf import DERFEngine
python derf_quickstart.py
python derf_integration_test.py
```
