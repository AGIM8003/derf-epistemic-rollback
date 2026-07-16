#!/usr/bin/env python3
"""DERF Quickstart — epistemic rollback in ~20 lines."""
from derf import DERFEngine

engine = DERFEngine()
engine.add_knowledge("genomics_study_2024", sources=[])
engine.add_knowledge("clinical_trial_results", depends_on=["genomics_study_2024"])
engine.add_knowledge("treatment_protocol_v3", depends_on=["clinical_trial_results"])
engine.add_knowledge("hospital_guidelines", depends_on=["treatment_protocol_v3"])
engine.add_knowledge("imaging_atlas_independent", sources=[])

engine.mark_contaminated("genomics_study_2024", reason="Data fabrication found")
result = engine.excise(attempt_recontamination_path=["clinical_trial_results"])

print(f"Contaminated: {result.contaminated_items}")
print(f"Excised: {result.excised_items}")
print(f"Still clean: {result.clean_items}")
print(f"Replay OK: {result.replay_success}")
print(f"Recontamination blocked: {result.recontamination_blocked}")
print(f"Time: {result.execution_time_seconds:.4f}s")
