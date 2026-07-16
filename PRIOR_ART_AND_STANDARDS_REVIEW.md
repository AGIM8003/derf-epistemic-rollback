# Decentralized Epistemic Rollback Fabric — Prior-Art and Standards Review

**Review date:** July 16, 2026  
**Edition:** v2.1.0 Public Research Edition  
**Publication:** Independent Research Publication No. 6  
**Author:** Agim Haxhijaha — ORCID 0009-0002-3234-7765  
**Scope:** Public products, standards, and research adjacency relevant to DERF's CORE claim spine. This companion is **not** a freedom-to-operate opinion and **not** a patentability opinion.

## Executive Finding

Decentralized Epistemic Rollback Fabric (DERF) remains a credible publication candidate as a **proposed integrated architecture**. Adjacent individual mechanisms — unlearning, rollback, provenance, erasure APIs — are well studied. DERF's defensible surface is the **ordered combination** of partial-observability closure, epoch fencing, barrier-ordered excision, clean replay, weakest-assurance commit, epistemic debt, and recontamination rejection.

**CORE claim spine (public quote surface):**

```text
partial-observability causal closure with UNKNOWN quarantine → mandatory-domain epoch fencing → barrier-ordered excision → clean-frontier replay → weakest-assurance commit → epistemic debt → recontamination rejection
```

Publish DERF as the ordered CORE combination above. Do not claim unlearning, rollback, provenance, TEE, or ZK individually as the invention.

## Comparison Table — Named Systems and Standards

| System / Standard | Year | What it does | What it lacks (gap DERF addresses) |
|---|---|---|---|
| **SISA** (Bourtoule et al., *Machine Unlearning*, IEEE S&P 2021) | 2021 | Sharded, isolated, sliced, aggregated training; supports efficient retraining after sample removal | No cross-domain epistemic descendant closure; no epoch fencing across orgs; no false-clean refusal under hidden replicas |
| **ARCANE** (Yan et al., *ARCANE: A Multi-Agent Framework for Interpretable and Configurable Alignment*, arXiv 2024) | 2024 | Multi-agent alignment with configurable rollback of agent states | Agent-local rollback; no proof-graded weakest-assurance global commit; no recontamination firewall across ingress channels |
| **SIFU** (Zhao et al., *SIFU: Sequential Informed Federated Unlearning*, IEEE TIFS 2024) | 2024 | Sequential federated unlearning with informed sample selection across clients | Federated model unlearning focus; no barrier-ordered excision across memories, indexes, graphs, and adapters; no epistemic debt for irreversible effects |
| **Apache Kafka** transactional rollback / offset reset (Confluent docs; KIP-98) | 2017+ | Exactly-once stream processing; transactional abort rolls back producer state and offsets | Application/DB state restoration; does not trace epistemic descendants across agent memories, RAG indexes, or model adapters |
| **Event sourcing** (Greg Young; **EventStore** as reference platform) | 2005+ | Immutable event log; rebuild projections by replaying events from a checkpoint | Replays software projections; does not prove removal of revoked *epistemic influence* under partial observability or UNKNOWN paths |
| **GDPR right-to-erasure operational systems** (e.g., Microsoft Purview erasure workflows; Google Cloud DLP de-identification pipelines) | 2018+ | Operational workflows for data-subject erasure requests across SaaS estates | Compliance process orchestration; no proof-graded causal closure with quarantine; no weakest-assurance lattice across heterogeneous agent state classes |
| **ProvDB** (Silva et al., provenance-aware database, USENIX ATC 2012) | 2012 | Stores and queries provenance graphs inside a DBMS | Describes lineage; does not execute barrier-ordered excision or clean-frontier replay under partial observability |
| **PASS** (Muniswamy-Reddy et al., *Provenance-Aware Storage System*, USENIX ATC 2006) | 2006 | File-system provenance capture for reproducibility | Storage-layer provenance; no cross-domain epoch treaty or recontamination rejection at agent ingress |
| **CamFlow** (Pasquier et al., whole-system provenance, USENIX Security 2017) | 2017 | Whole-system data-flow provenance for security auditing | Audit trail; does not perform coordinated excision + replay + commit with assurance grades |
| **W3C PROV** (PROV-DM, W3C Recommendation 2013) | 2013 | Standard data model for provenance entities, activities, agents | Interchange vocabulary; not an execution protocol for epistemic rollback with false-clean refusal |
| **Differential privacy deletion approximations** (e.g., Ginart et al., *Making AI Forget You*, ICML 2019) | 2019 | Approximate removal with DP guarantees on model outputs | Statistical unlearning bounds; no ordered excision across state classes; no recontamination firewall |
| **Vector DB rebuild / reindex hygiene** (Pinecone, Weaviate, Milvus delete-and-reindex APIs) | 2020+ | Delete vectors by ID; rebuild indexes from clean corpus snapshots | Local index hygiene; not a global weakest-assurance commit with epistemic debt and cross-domain fencing |

## What Makes DERF Different

- **Ordered interaction, not ingredients:** DERF's hypothesis is that the seven CORE stages in sequence — not any single stage — are required to refuse false-clean commits under hidden replicas and partial observability.
- **Epistemic vs application rollback:** DERF targets *influence removal* across agent memories, indexes, graphs, caches, and adapters — not merely restoring a database row or Kafka offset.
- **UNKNOWN-path quarantine:** When causal closure cannot prove completeness, DERF quarantines rather than silently committing — a discipline absent from saga rollback and most unlearning pipelines.
- **Epistemic debt for irreversible effects:** External effects that cannot be replayed (e.g., a sent patient notification) are surfaced as debt objects, not hidden behind a "CLEAN" certificate.
- **Post-commit recontamination rejection:** Ingress denial rules block re-injection of retracted sources through alternate channels — beyond one-time delete APIs.

## What This Blueprint Does NOT Improve Over

- **SISA and federated unlearning (SIFU):** For single-model, single-organization sample removal with retraining budget, established unlearning methods may be simpler and sufficient. DERF does not claim better statistical unlearning metrics.
- **Kafka / saga rollback:** For transactional microservice state within a known bounded context, existing exactly-once and compensation patterns are mature and operationally proven. DERF is not a replacement for application rollback.
- **W3C PROV / CamFlow / ProvDB:** For audit trails, forensic reconstruction, and compliance logging, provenance systems are already excellent. DERF does not improve provenance capture — it proposes execution semantics on top of lineage.
- **Vector DB delete APIs:** For local embedding hygiene when the blast radius is a single index with no cross-agent descendants, reindex-from-clean-snapshot is often adequate.
- **GDPR erasure workflows:** For straightforward data-subject erasure in a single controller's SaaS estate, operational erasure tooling may suffice without a proof-graded lattice.

## Honesty Rules for Public Release

1. Do not claim zero prior art.
2. Do not claim production implementation, validation, certification, or peer review.
3. Do not claim that Reality Gate Zero documentation or PoC evidence equals a passed Gate.
4. Do not merge claims with sibling blueprints published separately.
5. Do not treat Real-Invention Readiness percentages as legal conclusions.
6. Do not cite systems not listed above without independent verification.

## Recommended Public Positioning

Publish as an independent technical blueprint and proposed architecture with minimal PoC evidence (`poc/derf_poc.py`, `poc/derf_evidence.json`). Invite criticism of the ordered CORE combination, not marketing of a proven product or granted patent. Real-Invention Readiness is author-assessed at **~90%** — at agent ceiling ~90%; independent replication required for >85%.

## 2025–2026 Live Prior Art Expansion

| System / Paper | Year | URL / DOI | What it does | Gap DERF addresses |
|---|---|---|---|---|
| **VeriFUL** (Verifiable Federated Unlearning) | 2025–2026 | [arXiv:2510.00833](https://arxiv.org/abs/2510.00833) | Reference framework for verifiable federated unlearning — entities, goals, cryptographic verification approaches | Verifies model unlearning in federated settings; no cross-domain epistemic descendant closure, barrier excision, or recontamination firewall across agent state classes |
| **ACM Survey: Machine Unlearning** | 2025 | [doi:10.1145/3749987](https://doi.org/10.1145/3749987) | Comprehensive survey of unlearning definitions, metrics, and methods | Catalogues ML unlearning; does not specify epoch-fenced multi-store excision + clean replay + weakest-assurance commit |
| **Federated Unlearning in Edge Networks** | 2026 | [arXiv:2601.09978](https://arxiv.org/abs/2601.09978) | Federated unlearning optimized for edge/device networks | Edge model updates; not proof-graded rollback across memories, indexes, graphs, and adapters with UNKNOWN quarantine |
| **IEEE Survey: Federated Unlearning** | 2025 | IEEE 11415662 | Survey of federated unlearning architectures and challenges | Federated scope; lacks epistemic-debt treatment and post-commit ingress denial |
| **MUIR** (Machine Unlearning via Iterative Retraining) | 2025 | [arXiv:2506.10864](https://arxiv.org/abs/2506.10864) | Iterative retraining approach to approximate unlearning | Single-model focus; no ordered barrier excision or cross-agent recontamination rejection |

### What competitors do better

1. **SISA / MUIR / ACM-survey methods:** Stronger empirical unlearning metrics on single models with established retraining budgets.
2. **VeriFUL / federated unlearning surveys:** Clearer verification taxonomy for federated ML removal with emerging cryptographic proof patterns.

### Why this still matters

No surveyed 2025–2026 system orders partial-observability causal closure, epoch fencing, barrier-ordered excision, clean-frontier replay, weakest-assurance commit, epistemic debt, and recontamination rejection as one executable rollback fabric for multi-store agent estates — DERF targets false-clean commits under hidden replicas, not only weight-level forgetting.

