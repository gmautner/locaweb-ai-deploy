# ADR-010: Fail-Fast Secret Validation

## Status

Accepted

## Context

GitHub Actions secrets that are not configured expand to empty strings in workflow expressions. This does not cause an immediate error -- the workflow continues executing with empty values.

The consequences of missing secrets are severe but delayed:

- A missing `POSTGRES_PASSWORD` causes the PostgreSQL container to fail at startup with a cryptic error about authentication configuration.
- A missing CloudStack API key causes the provisioning script to fail after several retries with exponential backoff, wasting minutes.
- A missing SSH private key causes Kamal to fail when attempting to connect to VMs, after provisioning has already completed.

In each case, significant time and CloudStack resources are consumed before the actual problem (a missing secret) is surfaced.

## Decision

Add an explicit validation step at the beginning of the deployment workflow that checks for the presence of all required GitHub secrets. If any required secret is missing or empty, the workflow fails immediately with a clear error message listing the missing secrets.

The validation is context-aware:

- CloudStack credentials (`CLOUDSTACK_API_URL`, `CLOUDSTACK_API_KEY`, `CLOUDSTACK_SECRET_KEY`) are always required.
- SSH key (`SSH_PRIVATE_KEY`) is always required.
- Database credentials (`POSTGRES_USER`, `POSTGRES_PASSWORD`) are validated only when the `db_enabled` workflow input is `true`.

## Consequences

**Positive:**

- Immediate feedback on misconfiguration. Operators know exactly which secrets need to be set before any resources are consumed.
- No wasted time provisioning CloudStack infrastructure only to fail at the deployment step due to missing credentials.
- Clear, human-readable error messages instead of cryptic container or API failures.
- Conditional validation avoids false positives -- database secrets are not required when no database is requested.

**Negative:**

- The validation step must be kept in sync with the actual secrets used by the workflow. Adding a new secret requirement means updating the validation.
- Cannot validate the correctness of secret values -- only their presence. A wrong password still passes validation.
