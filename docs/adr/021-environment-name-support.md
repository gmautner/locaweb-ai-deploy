# ADR-021: Environment Name Support for Multi-Environment Deployments

## Status

Accepted

## Context

A single repository could only have one active deployment because the network name followed the pattern `{repo-name}-{unique-id}` with no environment dimension. This prevented users from running multiple environments (preview, staging, production, feature branches) from the same repository with fully isolated infrastructure.

The PRD flagged "multi-environment support" as a future consideration, and ADR-005 noted that the naming convention would need to be refactored when this support was introduced.

## Decision

Add a mandatory `env_name` input (default `"preview"`) to both the deploy and teardown workflows. The network name pattern becomes `{repo-name}-{unique-id}-{env_name}`, and all derived resource names (VMs, disks, keypairs) follow accordingly.

Key design choices:

1. **Free-text string** for `env_name` (not a fixed choice list) -- environment names are arbitrary and chosen by the caller (e.g., `preview`, `staging`, `production`, `feature-xyz`).
2. **Per-environment concurrency groups** -- the concurrency group changes from `deploy-{repository}` to `deploy-{repository}-{env_name}`, so deploying to "staging" does not block "production".
3. **Default value `"preview"`** -- existing callers that don't pass `env_name` get `"preview"` by default.
4. **Infrastructure tests use `"test"`** -- the test suite's `ENV_NAME` defaults to `"test"`, already isolated by `github.run_id`.
5. **E2E tests exercise both default and custom env names** -- the scale-up scenario uses `"e2etest"` while other scenarios use the default `"preview"`, validating that different environments can coexist.

## Consequences

**Positive:**

- Multiple environments from the same repository are now fully isolated at the infrastructure level (separate networks, VMs, disks, IPs).
- Per-environment concurrency groups allow parallel deployments to different environments.
- The naming convention is now complete and extensible for future use cases (feature branch previews, blue/green deployments).
- E2E tests validate that the multi-environment mechanism works correctly.

**Negative:**

- **Breaking change:** Existing deployments use resource names without the `env_name` suffix. They must be torn down with the old workflow version before upgrading to the new naming convention. Resources provisioned under the old naming scheme cannot be found or managed by the new workflow.
- Callers that invoke the reusable workflows must add `env_name` to their `with:` blocks (though the default `"preview"` makes this optional for single-environment setups).
