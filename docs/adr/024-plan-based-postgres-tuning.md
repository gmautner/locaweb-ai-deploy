# ADR-024: Plan-Based PostgreSQL Parameter Tuning

**Status:** Accepted
**Date:** 2026-02-17

## Context

The `supabase/postgres` image ships with conservative PostgreSQL defaults (e.g. `shared_buffers=128MB`, `effective_cache_size=128MB`). The Kamal accessory config previously hardcoded `--shared_buffers=256MB` regardless of the selected `db_plan`. With plans ranging from 1 GiB (micro) to 64 GiB (4xlarge), a static 256MB is suboptimal for larger plans and tight for micro.

Since the DB VM is dedicated to PostgreSQL with no other significant workloads, we can apply aggressive tuning heuristics based on total VM RAM.

## Decision

Auto-tune five PostgreSQL parameters based on the `db_plan` input using standard PostgreSQL tuning heuristics:

| Parameter | Formula | Rationale |
|-----------|---------|-----------|
| `shared_buffers` | 25% of RAM | Standard recommendation for dedicated DB servers |
| `effective_cache_size` | 75% of RAM | OS page cache + shared_buffers; tells the query planner how much memory is available for caching |
| `work_mem` | RAM / max_connections / 4 (min 2MB) | Per-operation sort/hash memory; conservative divisor accounts for multiple active operations per connection |
| `maintenance_work_mem` | RAM / 16 (capped at 2GB) | For VACUUM, CREATE INDEX; cap prevents excessive memory use |
| `max_connections` | 100 (<=4GB), 200 (<=16GB), 400 (>=32GB) | More RAM supports more concurrent backends |

### Resulting values

| Plan | RAM | shared_buffers | effective_cache_size | work_mem | maintenance_work_mem | max_connections |
|------|-----|----------------|----------------------|----------|----------------------|-----------------|
| micro | 1 GiB | 256MB | 768MB | 2MB | 64MB | 100 |
| small | 2 GiB | 512MB | 1536MB | 5MB | 128MB | 100 |
| medium | 4 GiB | 1GB | 3GB | 10MB | 256MB | 100 |
| large | 8 GiB | 2GB | 6GB | 10MB | 512MB | 200 |
| xlarge | 16 GiB | 4GB | 12GB | 20MB | 1GB | 200 |
| 2xlarge | 32 GiB | 8GB | 24GB | 20MB | 2GB | 400 |
| 4xlarge | 64 GiB | 16GB | 48GB | 40MB | 2GB | 400 |

The parameters are passed as PostgreSQL startup flags in the Kamal accessory `cmd` field (e.g. `--shared_buffers=1GB --effective_cache_size=3GB ...`).

## Consequences

- PostgreSQL performance scales automatically with the chosen VM plan size.
- No manual tuning is needed when changing `db_plan`.
- The `INPUT_DB_PLAN` environment variable must be passed to the config generation step in the deploy workflow.
- The formulas use integer arithmetic with sensible minimums/caps, so edge cases (very small or very large plans) produce safe values.
- Custom PostgreSQL tuning beyond these parameters still requires modifying the config generation script.
