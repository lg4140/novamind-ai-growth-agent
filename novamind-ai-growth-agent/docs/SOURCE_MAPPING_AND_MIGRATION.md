# V1 → V2 → V3 → V4 Source Mapping and Migration

## Provenance
The **private full-release V4 archive** preserved earlier source releases, but this **public GitHub repository intentionally omits `legacy/` and nested release archives** to keep the portfolio repo reviewable and avoid redistributing obsolete examples. V4 is derived from V3 and adds `stateful.py`, `constraints.py`, `evidence.py`, `memory_service.py`, `orchestrator.py`, `telemetry.py`, `v4_cli.py` and new Streamlit UX. Existing one-step main entrypoint remains functional.

## Schema additions
`plan_sessions`, `plan_revisions`, `claim_evidence`, `reviewer_feedback`, `product_events`. `db.init_db` uses `CREATE TABLE IF NOT EXISTS`, so a local V3 database with compatible versions can create additive tables, but this is not a formally tested reversible migration. For deterministic demonstrations use a clean V4 SQLite DB file.

## Compatibility caveats
The V3 `CampaignPlan` default new `constraint_policy` is empty no-live-send; earlier serialized plans still parse if valid. `CampaignContent` adds optional `evidence_refs`; old records parse. Source type labels remain SYNTHETIC; no retroactive claim that historic metrics are real. If productization continues, use explicit transactional versioned migrations and DB backup plans.
