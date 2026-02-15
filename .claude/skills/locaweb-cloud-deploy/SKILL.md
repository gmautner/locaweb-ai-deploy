---
name: locaweb-cloud-deploy
description: >
  Deploy containerized web applications to Locaweb Cloud using reusable GitHub Actions workflows
  from gmautner/locaweb-ai-deploy. Use this skill when an agent or user needs to: (1) set up a
  repository for deployment to Locaweb Cloud, (2) create or modify GitHub Actions deploy/teardown
  caller workflows, (3) configure secrets and environment variables for Locaweb Cloud deployment,
  (4) write or adapt a Dockerfile for the platform, (5) understand deployment outputs like IPs and
  URLs, (6) set up DNS for custom domains, (7) scale VMs, workers, or disk sizes, (8) tear down
  deployed environments, (9) troubleshoot deployment issues. Triggers on keywords: Locaweb, deploy,
  teardown, CloudStack, Kamal, nip.io, Locaweb Cloud, env_name, preview, production environment.
---

# Locaweb Cloud Deploy

Deploy web applications to Locaweb Cloud by calling reusable workflows from `gmautner/locaweb-ai-deploy`. The platform provisions CloudStack VMs, networks, disks, and firewall rules, then deploys containers via Kamal 2 with zero-downtime proxy.

## Workflow Overview

```
Caller repo                          gmautner/locaweb-ai-deploy
+-----------------------+            +-----------------------------+
| .github/workflows/    |  calls     | .github/workflows/          |
|   deploy.yml        -------->      |   deploy.yml (provisions    |
|   teardown.yml      -------->      |     infra + deploys app)    |
+-----------------------+            |   teardown.yml (destroys    |
| Dockerfile (root)     |            |     all resources)          |
| Source code           |            +-----------------------------+
+-----------------------+
```

## Quick Start: First Deployment

Follow this sequence for a new repository:

1. **Prepare the application** (Dockerfile + health check) -- see [Dockerfile Requirements](#dockerfile-requirements)
2. **Configure GitHub repo secrets** -- see [Secrets Setup](#secrets-setup)
3. **Create a preview deploy workflow** (no domain, triggered on push) -- see [references/workflows.md](references/workflows.md)
4. **Push and verify** via the nip.io URL from workflow outputs
5. **When mature, add a production workflow** with a custom domain -- see [references/workflows.md](references/workflows.md)

## Dockerfile Requirements

- Single `Dockerfile` at repository root
- Web app **must listen on port 80** (hardcoded in platform proxy config)
- Default `CMD`/entrypoint serves the web application
- If using workers, the same image must support a separate command passed via `workers_cmd` input
- Health check endpoint at `GET /up` returning HTTP 200 when healthy; return 200 even when database is not configured (check if `POSTGRES_HOST` env var is empty/absent)
- If connecting to a database, read connection from env vars: `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`

Example minimal Dockerfile:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 80
CMD ["gunicorn", "--bind", "0.0.0.0:80", "--workers", "2", "app:app"]
```

## Secrets Setup

Configure these in the caller repository's GitHub Settings > Secrets and variables > Actions.

### Mandatory secrets (always required)

| Secret | Description | How to generate |
|--------|-------------|-----------------|
| `CLOUDSTACK_API_KEY` | CloudStack API key | Provided by Locaweb Cloud account admin |
| `CLOUDSTACK_SECRET_KEY` | CloudStack secret key | Provided by Locaweb Cloud account admin |
| `SSH_PRIVATE_KEY` | Ed25519 SSH private key for VM access | See command below |

Generate the SSH key:

```bash
ssh-keygen -t ed25519 -f locaweb-deploy-key -N "" -C "locaweb-deploy"
# Copy the ENTIRE contents of locaweb-deploy-key (private key) into the SSH_PRIVATE_KEY secret
# The public key is derived automatically at deploy time
```

### Database secrets (required when `db_enabled: true`)

| Secret | Description | Notes |
|--------|-------------|-------|
| `POSTGRES_USER` | PostgreSQL username | e.g. `myapp_user` |
| `POSTGRES_PASSWORD` | PostgreSQL password | Generate a strong random password |

**Use different passwords for different environments.** Generate random passwords:

```bash
# Generate a 32-character random password
openssl rand -base64 32
```

If deploying multiple environments (preview + production), use suffixed secrets:
- `POSTGRES_USER` / `POSTGRES_PASSWORD` for preview
- `POSTGRES_USER_PROD` / `POSTGRES_PASSWORD_PROD` for production
- Pass the correct one in each workflow's `secrets:` block

### Custom environment variables

See [references/env-vars.md](references/env-vars.md) for detailed configuration of application env vars and secrets.

## Deployment Outputs and URLs

After a deploy workflow completes, extract information from:

1. **Workflow outputs**: `web_ip`, `worker_ips` (JSON array), `db_ip`, `db_internal_ip`
2. **GitHub Actions step summary**: visible in the workflow run UI, shows IP table and app URL
3. **`provision-output` artifact**: JSON file retained for 90 days

### Determining the app URL

- **No domain (preview)**: `http://<web_ip>.nip.io` -- works immediately, no DNS needed, no HTTPS
- **With domain**: `https://<domain>` -- requires DNS A record pointing to `web_ip`, automatic SSL via Let's Encrypt

### DNS Configuration for Custom Domains

The web VM's public IP is not known until the first deployment completes. To set up a custom domain:

1. **Deploy without a domain first** (leave `domain` empty). The app will be accessible at `http://<web_ip>.nip.io`.
2. **Note the `web_ip`** from the workflow output or step summary.
3. **Create a DNS A record** pointing the domain to that IP:
   ```
   Type: A
   Name: myapp.example.com (or @ for apex)
   Value: <web_ip from step 2>
   TTL: 300
   ```
4. **Re-run the deploy workflow** with the `domain` input set. kamal-proxy will provision a Let's Encrypt certificate automatically.

Let's Encrypt HTTP-01 challenge requires the domain to resolve to the server before the certificate can be issued. The IP is stable across re-deployments to the same environment -- it only changes if the environment is torn down and recreated.

## Scaling

See [references/scaling.md](references/scaling.md) for VM plans, worker scaling, and disk size configuration.

## Teardown

See [references/teardown.md](references/teardown.md) for tearing down environments, inferring zone/env_name from existing workflows, and reading last run outputs.

## Platform Constraints

- **Postgres only**: No Redis, Kafka, or other services. Use Postgres for queues (e.g., `SKIP LOCKED` pattern), pub/sub (`LISTEN`/`NOTIFY`), job scheduling, caching, and any other patterns. If the application framework expects Redis or similar, find a Postgres-backed alternative or implement the pattern directly on Postgres. Search the web or use specialized skills for Postgres-based alternatives to Redis, Kafka, etc.
- **Single web VM**: No horizontal web scaling. Scale vertically with larger `web_plan`.
- **No TLS without a domain**: nip.io URLs are HTTP only. Use a custom domain for HTTPS.
- **Single PostgreSQL instance**: No read replicas or multiple databases.
- **No cron/scheduled jobs**: Use Postgres-based scheduling or the worker process to poll.

## Development Cycle Without Local Environment

When the developer cannot run the language runtime or database locally:

1. Commit and push changes
2. Wait for the deploy workflow to complete (triggered on push for preview)
3. Browse the nip.io preview URL to verify
4. Repeat

**Recommendation**: Start with a single `preview` environment triggered on push, without a domain. This avoids DNS configuration during development. When the app is mature, add a second workflow for `production` with a custom domain.

## References

- **[references/workflows.md](references/workflows.md)** -- Complete caller workflow examples (deploy + teardown) with all inputs documented
- **[references/env-vars.md](references/env-vars.md)** -- Environment variables and secrets configuration
- **[references/scaling.md](references/scaling.md)** -- VM plans, worker scaling, disk sizes
- **[references/teardown.md](references/teardown.md)** -- Teardown process, inferring parameters, reading outputs
