# ADR-022: Per-Environment Secret and SSH Key Isolation

## Status

Accepted

## Context

With multi-environment support (ADR-021), each `env_name` creates fully isolated CloudStack infrastructure (separate networks, VMs, disks, IPs). However, the secret management layer initially didn't match this isolation model — production secrets used an arbitrary `_PROD` abbreviation, and SSH keys were shared across all environments.

Two problems emerged:

1. **Inconsistent naming**: The `_PROD` suffix was an abbreviation that didn't match the actual `env_name` value (`production`). If a user chose a different environment name (e.g., `staging`), there was no clear convention for how to suffix their secrets.
2. **Shared SSH keys**: A single SSH key pair was used across all environments, meaning anyone with access to preview VMs could also access production VMs.
3. **Teardown destroys the keypair**: The teardown script deletes the SSH keypair registered in CloudStack as its final step. With a shared key, tearing down one environment (e.g., preview) would remove the keypair still in use by other environments (e.g., production), breaking SSH access and future Kamal deployments to those environments.

## Decision

Adopt a consistent, environment-scoped naming convention for secrets and SSH keys:

### Secret naming

- **Preview environment** (default `env_name`): secrets use **unsuffixed** names — `SSH_PRIVATE_KEY`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.
- **Additional environments**: secrets are suffixed with the environment name **uppercased** — e.g., `SSH_PRIVATE_KEY_PRODUCTION`, `POSTGRES_USER_PRODUCTION`, `POSTGRES_PASSWORD_PRODUCTION`.
- **Global secrets** shared across all environments (CloudStack credentials) have no suffix — `CLOUDSTACK_API_KEY`, `CLOUDSTACK_SECRET_KEY`.
- **Custom secrets** (`SECRET_ENV_VARS`) follow the same pattern — e.g., `API_KEY` for preview, `API_KEY_PRODUCTION` for production.

### SSH key isolation

Each environment gets its own SSH key pair:

- **Preview**: `~/.ssh/<repo-name>` → stored as `SSH_PRIVATE_KEY`
- **Additional environments**: `~/.ssh/<repo-name>-<env_name>` → stored as `SSH_PRIVATE_KEY_<ENV_NAME>` (e.g., `~/.ssh/myapp-production` → `SSH_PRIVATE_KEY_PRODUCTION`)

### Caller workflow mapping

The reusable workflow always receives standard, unsuffixed secret names (`SSH_PRIVATE_KEY`, `POSTGRES_USER`, `POSTGRES_PASSWORD`). The caller workflow is responsible for mapping its environment-specific secrets to these standard names:

```yaml
# Production caller maps suffixed secrets to standard names
secrets:
  SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY_PRODUCTION }}
  POSTGRES_USER: ${{ secrets.POSTGRES_USER_PRODUCTION }}
  POSTGRES_PASSWORD: ${{ secrets.POSTGRES_PASSWORD_PRODUCTION }}
```

## Consequences

**Positive:**

- Secret naming is self-documenting and predictable — the suffix is always the environment name uppercased.
- SSH key isolation ensures that compromising one environment's key does not grant access to other environments.
- The pattern scales to any number of environments without hardcoded abbreviations.
- The reusable workflow remains environment-agnostic — it only sees standard secret names.

**Negative:**

- Users managing multiple environments must create and store more secrets (one SSH key and one set of Postgres credentials per environment).
- **Breaking change from `_PROD`**: Repositories that adopted the earlier `_PROD` naming must rename their secrets to `_PRODUCTION` (or whichever `env_name` they use).
