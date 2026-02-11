# ADR-013: KAMAL_ Prefix Convention for Custom Environment Variables

## Status

Accepted

## Context

Applications often need custom environment variables beyond the platform-managed ones (database credentials, blob storage path). Examples include API keys for third-party services, feature flags, or configuration values like log levels.

Providing a mechanism to pass arbitrary secrets and variables into the container without modifying the workflow requires a convention that can be discovered dynamically at deploy time.

## Decision

Use a `KAMAL_` prefix convention on GitHub secrets and variables. At deploy time, the workflow inspects `toJSON(secrets)` and `toJSON(vars)`, filters for the `KAMAL_` prefix, strips the prefix, and maps the entries into the Kamal configuration:

- **GitHub Secrets with `KAMAL_` prefix** → added as `$VAR` references in `.kamal/secrets` and listed in `env.secret` in the Kamal deploy config. Their resolved values are exported into the deploy step's process environment so Kamal can resolve the references at runtime. The container receives the secret value under the stripped name.
- **GitHub Variables with `KAMAL_` prefix** → added to `env.clear` in the Kamal deploy config. The container receives the variable value under the stripped name.

Example: `KAMAL_REDIS_URL` (secret) → container gets `REDIS_URL`. `KAMAL_LOG_LEVEL` (variable) → container gets `LOG_LEVEL`.

## Consequences

**Positive:**

- Users can add arbitrary environment variables without modifying the workflow.
- Clear separation: secrets stay secret, variables stay clear.
- The `KAMAL_` prefix prevents accidental collision with GitHub's built-in secrets (`GITHUB_TOKEN`, etc.) and infrastructure secrets (`CLOUDSTACK_*`, `SSH_*`).
- No workflow changes needed when adding or removing custom variables.

**Negative:**

- The `KAMAL_` prefix is an implicit convention that users must learn.
- `toJSON(secrets)` exposes all secret values to the processing step. This is acceptable since the step already handles secret values for `.kamal/secrets`, but it means the step has access to all repository secrets, not just the ones it needs.
