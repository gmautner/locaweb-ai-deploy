# ADR-023: Switch to supabase/postgres with Automated Tag Resolution

**Status:** Accepted
**Date:** 2026-02-17

## Context

The project used the official `postgres:16` Docker image as the database accessory. While functional, the official image ships with only the core PostgreSQL extensions. As application requirements grow, pre-installed extensions (e.g. pgvector, pg_cron, pgjwt) become valuable.

`supabase/postgres` is a PostgreSQL image maintained by Supabase that bundles a curated set of popular extensions on top of the official PostgreSQL distribution. It is well-maintained and widely used.

However, unlike the official postgres image which supports short tags like `16` or `17`, supabase/postgres only publishes 4-digit tags like `17.6.1.084`. Some tags also carry suffixes (e.g. `-orioledb`) for alternative storage engines. We need a way to automatically resolve the latest eligible tag at deploy time rather than hardcoding a specific version.

## Decision

1. **Switch the database accessory image** from `postgres:16` to `supabase/postgres` with a tag under major version 17.
2. **Automate tag resolution** with a new script (`scripts/resolve_postgres_tag.py`) that queries Docker Hub at deploy time to find the latest 4-component numeric tag matching `^17\.\d+\.\d+\.\d+$` (no suffixes).
3. **Pass the resolved image** via the `POSTGRES_IMAGE` environment variable from the workflow to the config generation script, with a fallback to `postgres:16` if unset.

## Tag Selection Rules

- **Major version:** 17 only (to track the latest PostgreSQL major version).
- **Tag format:** Exactly 4 numeric components `a.b.c.d` — no suffixes like `-orioledb`.
- **Selection:** Highest version by tuple comparison.
- **Source:** Single page of 50 most recent tags from Docker Hub API (sufficient since the highest version will be among recent pushes).

## Consequences

### Positive

- **Richer extension set**: Applications get access to pgvector, pg_cron, and dozens of other extensions without building a custom image.
- **Automatic updates**: The tag resolution script picks the latest patch version on each deploy, keeping the database image current without manual intervention.
- **Graceful fallback**: If `POSTGRES_IMAGE` is not set (e.g. when the resolve step is skipped), the config script falls back to `postgres:16`.

### Negative

- **Docker Hub dependency**: The resolve step requires Docker Hub API availability at deploy time. If Docker Hub is down, the step fails and blocks deployment.
- **No pinning**: The image tag changes between deploys as new versions are published. This is acceptable for this project but could be a concern for strict reproducibility requirements.
- **Major version bump requires code change**: Moving to PostgreSQL 18 will require updating the regex in the resolve script.

### Neutral

- The `requests` Python library is installed during the workflow step (`pip install -q requests`). This adds a small amount of time to the workflow but is negligible.
