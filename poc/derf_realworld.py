#!/usr/bin/env python3
"""
DERF Real-World Scenario — GDPR patient-data contamination in a genomics AI pipeline.

Modeled on the class of incidents where a foundational training corpus is found to
contain identifiable patient records that must be purged (GDPR Art. 17/19), while
papers, models, and clinical decision aids already depend on that corpus.

Author: Agim Haxhijaha, ORCID 0009-0002-3234-7765

DISCLAIMER: Scenario is illustrative research fiction inspired by real incident
classes (retraction + downstream AI contamination). Not a claim about any named
institution's actual wrongdoing. Not production software.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from derf_poc import Agent, EpistemicGraph, KnowledgeItem

AUTHOR = "Agim Haxhijaha"
ORCID = "0009-0002-3234-7765"
OUT = Path(__file__).with_name("derf_realworld_evidence.json")


def build_genomics_gdpr_scenario() -> tuple[EpistemicGraph, str, dict[str, Any]]:
    """
    Contamination origin: SURROGATE-GENOME-CORPUS-2019 found to contain
    re-identifiable clinical genomes without lawful basis for secondary use.
    """
    g = EpistemicGraph()
    meta = {
        "incident_class": "GDPR_Art17_erasure_cascade_in_AI_training_graph",
        "modeled_on": (
            "Public incident class: foundational dataset contamination / "
            "retraction with slow manual downstream notification (months)."
        ),
        "fields": ["genomics", "clinical_trials", "epidemiology", "hospital_CDS"],
        "contamination_type": (
            "Training corpus contains patient SNPs linkable to EHR identifiers; "
            "Art. 17 erasure + Art. 19 recipient notification required."
        ),
    }

    biobank = Agent("inst_biobank_nordic", "Nordic Clinical Biobank", depends_on=[])
    biobank.knowledge["DS_SURROGATE_GENOME_CORPUS_2019"] = KnowledgeItem(
        "DS_SURROGATE_GENOME_CORPUS_2019",
        "inst_biobank_nordic",
        "Release of 48k 'de-identified' genomes for secondary research use",
        source_ids=[],
    )
    biobank.knowledge["DS_QC_CERTIFICATE"] = KnowledgeItem(
        "DS_QC_CERTIFICATE",
        "inst_biobank_nordic",
        "QC certificate: call-rate >98%, batch-effect corrected",
        source_ids=[],
    )
    g.add_agent(biobank)

    geno_lab = Agent(
        "inst_genomics_lab",
        "Academic Genomics Lab (variant association)",
        depends_on=["inst_biobank_nordic"],
    )
    geno_lab.knowledge["PAPER_GWAS_CARDIO_2021"] = KnowledgeItem(
        "PAPER_GWAS_CARDIO_2021",
        "inst_genomics_lab",
        "GWAS: 12 loci associated with cardiomyopathy risk (n=48k)",
        source_ids=["DS_SURROGATE_GENOME_CORPUS_2019", "DS_QC_CERTIFICATE"],
        derived=True,
    )
    geno_lab.knowledge["MODEL_POLYGENIC_CARDIO_V3"] = KnowledgeItem(
        "MODEL_POLYGENIC_CARDIO_V3",
        "inst_genomics_lab",
        "Polygenic risk model trained on Surrogate Genome Corpus 2019",
        source_ids=["DS_SURROGATE_GENOME_CORPUS_2019", "PAPER_GWAS_CARDIO_2021"],
        derived=True,
    )
    g.add_agent(geno_lab)

    trial = Agent(
        "inst_trial_site_eu",
        "EU Multi-Centre Cardiology Trial",
        depends_on=["inst_genomics_lab"],
    )
    trial.knowledge["PROTOCOL_AMEND_PRSMATCH"] = KnowledgeItem(
        "PROTOCOL_AMEND_PRSMATCH",
        "inst_trial_site_eu",
        "Protocol amendment: enrich arm using polygenic risk score V3",
        source_ids=["MODEL_POLYGENIC_CARDIO_V3", "PAPER_GWAS_CARDIO_2021"],
        derived=True,
    )
    trial.knowledge["INTERIM_ANALYSIS_Q3"] = KnowledgeItem(
        "INTERIM_ANALYSIS_Q3",
        "inst_trial_site_eu",
        "Interim efficacy analysis conditioned on PRS strata from V3",
        source_ids=["PROTOCOL_AMEND_PRSMATCH", "MODEL_POLYGENIC_CARDIO_V3"],
        derived=True,
    )
    g.add_agent(trial)

    hospital = Agent(
        "inst_hospital_cds",
        "Tertiary Hospital Clinical Decision Support",
        depends_on=["inst_genomics_lab", "inst_trial_site_eu"],
    )
    hospital.knowledge["CDS_RULE_CARDIO_PRS"] = KnowledgeItem(
        "CDS_RULE_CARDIO_PRS",
        "inst_hospital_cds",
        "CDS rule: escalate cardiology referral if PRS-V3 > 90th percentile",
        source_ids=["MODEL_POLYGENIC_CARDIO_V3", "INTERIM_ANALYSIS_Q3"],
        derived=True,
    )
    hospital.knowledge["PATIENT_COHORT_FLAGGED_1847"] = KnowledgeItem(
        "PATIENT_COHORT_FLAGGED_1847",
        "inst_hospital_cds",
        "1,847 patients flagged for accelerated pathway via CDS rule",
        source_ids=["CDS_RULE_CARDIO_PRS"],
        derived=True,
    )
    g.add_agent(hospital)

    epi = Agent(
        "inst_epi_surveillance",
        "National Epidemiology Surveillance Unit",
        depends_on=["inst_genomics_lab"],
    )
    epi.knowledge["BRIEF_POP_RISK_MAP"] = KnowledgeItem(
        "BRIEF_POP_RISK_MAP",
        "inst_epi_surveillance",
        "Regional cardiomyopathy risk map derived from GWAS paper + model V3",
        source_ids=["PAPER_GWAS_CARDIO_2021", "MODEL_POLYGENIC_CARDIO_V3"],
        derived=True,
    )
    g.add_agent(epi)

    meta_agent = Agent(
        "inst_meta_analysis",
        "Consortium Meta-Analysis Group",
        depends_on=["inst_genomics_lab", "inst_epi_surveillance"],
    )
    meta_agent.knowledge["META_CARDIO_2024"] = KnowledgeItem(
        "META_CARDIO_2024",
        "inst_meta_analysis",
        "Meta-analysis incorporating GWAS paper and surveillance brief",
        source_ids=["PAPER_GWAS_CARDIO_2021", "BRIEF_POP_RISK_MAP"],
        derived=True,
    )
    g.add_agent(meta_agent)

    # Clean independent branch (should survive)
    lab_clean = Agent("inst_imaging_lab", "Cardiac Imaging Lab (independent)", depends_on=[])
    lab_clean.knowledge["MRI_PHENOTYPE_ATLAS"] = KnowledgeItem(
        "MRI_PHENOTYPE_ATLAS",
        "inst_imaging_lab",
        "MRI phenotype atlas from consented imaging cohort (no genome corpus)",
        source_ids=[],
    )
    g.add_agent(lab_clean)

    origin = "DS_SURROGATE_GENOME_CORPUS_2019"
    return g, origin, meta


def manual_baseline_today(closure_size: int, institutions: int) -> dict[str, Any]:
    """What typically happens without DERF-style causal closure."""
    return {
        "method": "manual_retraction_notices_and_email_trees",
        "typical_latency_days": "60-180",
        "downstream_miss_rate_estimate": "0.30-0.60",
        "institutions_notified_first_wave": max(1, institutions // 3),
        "closure_items_typically_missed": max(1, int(closure_size * 0.35)),
        "clinical_cds_rules_often_left_active": True,
        "art19_recipient_enumeration": "incomplete_without_provenance_graph",
    }


def run() -> dict[str, Any]:
    graph, origin, meta = build_genomics_gdpr_scenario()
    before = {
        "agents": len(graph.agents),
        "items": len(graph.items),
        "roles": {a.agent_id: a.role for a in graph.agents.values()},
    }

    graph.mark_retracted(origin)
    closure = graph.compute_causal_closure({origin})
    excision = graph.barrier_ordered_excision(closure)
    replay = graph.replay_from_frontier()
    reinject = graph.attempt_recontamination(
        origin,
        alternate_path=["PAPER_GWAS_CARDIO_2021", "MODEL_POLYGENIC_CARDIO_V3"],
    )
    frontier = sorted(graph.clean_frontier())
    surviving_clinical = [
        iid for iid in frontier if "CDS" in iid or "MRI" in iid or "PATIENT" in iid
    ]

    derf_outcome = {
        "contamination_origin": origin,
        "causal_closure_size": len(closure),
        "causal_closure_items": sorted(closure),
        "excision_order": excision,
        "replay": {
            "frontier_size": replay["frontier_size"],
            "replayed_count": len(replay["replayed"]),
            "unrecoverable_count": len(replay["unrecoverable"]),
            "unrecoverable": replay["unrecoverable"],
        },
        "recontamination_blocked": reinject["blocked"],
        "recontamination_reasons": reinject["rejection_reasons"],
        "clean_frontier": frontier,
        "clinical_artifacts_on_clean_frontier": surviving_clinical,
        "institutions_in_closure": sorted(
            {
                graph.items[iid].agent_id
                for iid in closure
                if iid in graph.items
            }
        ),
    }

    manual = manual_baseline_today(len(closure), len(graph.agents))
    advantage = {
        "derf_excises_full_closure_immediately": True,
        "manual_latency_days": manual["typical_latency_days"],
        "derf_blocks_reinjection_via_paper_model_path": reinject["blocked"],
        "manual_often_misses_cds_rules": manual["clinical_cds_rules_often_left_active"],
        "art19_recipient_set_from_closure": derf_outcome["institutions_in_closure"],
        "what_existing_approaches_miss": (
            "Retraction notices stop at the paper; CDS rules, trial interim "
            "analyses, and meta-analyses that transitively depend on the corpus "
            "remain active for months without a causal closure engine."
        ),
    }

    evidence = {
        "framework": "DERF",
        "script": "derf_realworld.py",
        "author": AUTHOR,
        "orcid": ORCID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scenario": meta,
        "graph_before": before,
        "derf_pipeline": derf_outcome,
        "manual_baseline_today": manual,
        "comparative_advantage": advantage,
        "pass": (
            origin in closure
            and "CDS_RULE_CARDIO_PRS" in closure
            and "PATIENT_COHORT_FLAGGED_1847" in closure
            and "MRI_PHENOTYPE_ATLAS" not in closure
            and reinject["blocked"] is True
            and len(excision) == len(closure)
        ),
    }
    return evidence


def main() -> int:
    evidence = run()
    OUT.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(f"DERF real-world: pass={evidence['pass']} closure={evidence['derf_pipeline']['causal_closure_size']}")
    print(f"Wrote {OUT.name}")
    return 0 if evidence["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
