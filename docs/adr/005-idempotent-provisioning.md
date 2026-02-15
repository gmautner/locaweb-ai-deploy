# ADR-005: Idempotent Provisioning with Name-Based Lookup

## Status

Accepted

## Context

The provisioning script may be executed multiple times for the same deployment:

- GitHub Actions workflows can be manually re-triggered.
- Failed workflows are often retried.
- Developers may run the provisioning step locally during debugging.

Without idempotency, each run would create duplicate VMs, IP addresses, volumes, and firewall rules, leading to resource sprawl and wasted CloudStack quota.

## Decision

Every CloudStack resource is looked up by name before creation. If a resource with the expected name already exists, its ID is reused and no new resource is created.

The naming convention is `<repo-name>-<repo-id>-<role>`, where:

- `<repo-name>` is the GitHub repository name (e.g., `my-rails-app`).
- `<repo-id>` is the numeric GitHub repository ID (ensuring uniqueness across forks).
- `<role>` is the resource's function (e.g., `web`, `worker-1`, `db`, `network`).

For example: `my-rails-app-123456-web`, `my-rails-app-123456-worker-1`, `my-rails-app-123456-db`.

## Consequences

**Positive:**

- Safe to re-run the provisioning script at any time without creating duplicate resources.
- Enables incremental changes. Scaling workers from 1 to 3 creates only the two missing VMs; the existing one is reused.
- Simplifies workflow retry logic -- no need for cleanup between attempts.
- The naming convention makes resources identifiable in the CloudStack UI.

**Negative:**

- Requires strict naming consistency. If the naming convention changes, old resources become orphaned (not found by the new lookup) and new duplicates are created.
- Name-based lookup relies on the CloudStack `list` API filtering correctly by name. Some resource types have different filtering behavior.
- Resources cannot be renamed without being recreated. A repository rename would orphan all existing resources.
- ~~The naming convention will need to be refactored when multi-environment support is introduced, since the same repository will have distinct deployments per environment (e.g., staging vs. production) requiring environment-aware resource names.~~ Addressed by [ADR-021](021-environment-name-support.md): the naming convention is now `{repo-name}-{unique-id}-{env-name}`.
