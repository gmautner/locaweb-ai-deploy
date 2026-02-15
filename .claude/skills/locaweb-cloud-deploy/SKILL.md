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

## Platform Constraints (Read First)

These constraints apply to **every** application deployed to this platform. Communicate these upfront when starting any deployment work:

- **Single Dockerfile at repo root**, web app **must listen on port 80**
- **Health check at `GET /up`** returning HTTP 200 when healthy
- **Postgres only**: No Redis, Kafka, or other services. Use Postgres for queues (`SKIP LOCKED`), pub/sub (`LISTEN`/`NOTIFY`), job scheduling, caching, and any other patterns. If the app framework expects Redis or similar, find or implement a Postgres-backed alternative.
- **Single web VM**: No horizontal web scaling. Scale vertically with larger `web_plan`. Prefer runtimes and frameworks that scale well vertically.
- **No TLS without a domain**: nip.io URLs are HTTP only. Use a custom domain for HTTPS.
- **Single PostgreSQL instance**: No read replicas or multiple databases.
- **Workers use the same Docker image** with a different command (`workers_cmd`).

If the application's current design conflicts with any of these (e.g., depends on Redis, listens on port 3000, uses multiple Dockerfiles), resolve the conflict **before** proceeding with deployment setup.

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

## Setup Procedure

Follow these steps in order. Each step is idempotent -- safe to re-run across agent sessions. See [references/setup-and-deploy.md](references/setup-and-deploy.md) for detailed commands and procedures for each step.

### Step 1: Prepare the application

- Ensure a single `Dockerfile` at repo root, listening on port 80
- Implement `GET /up` health check returning 200
- If using a database: read connection from `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`. The app **must fail clearly** (not silently degrade) if these vars are expected but missing.
- If using workers: ensure the same Docker image supports a separate command for the worker process

### Step 2: Set up the GitHub repository

- Check if a git remote is configured (`git remote -v`)
- If no remote: ask the user whether to use an existing GitHub repo or create a new one
  - Existing repo: ask for the URL, add as remote
  - New repo: create with `gh repo create`

### Step 3: Generate SSH key

- If `~/.ssh/<repo-name>` already exists, skip generation and reuse the existing key
- Otherwise, generate an Ed25519 SSH key locally at `~/.ssh/<repo-name>` with no passphrase
- Set permissions to 0600

### Step 4: Collect CloudStack credentials

- Check if `CLOUDSTACK_API_KEY` and `CLOUDSTACK_SECRET_KEY` are already set in the repo (`gh secret list`)
- If not set: ask the user to provide them

### Step 5: Set up Postgres credentials

- Check if `POSTGRES_USER` and `POSTGRES_PASSWORD` are already set in the repo (`gh secret list`)
- If not set: choose a `POSTGRES_USER` (e.g., `myapp_user`) and generate a random password for each environment
- Use suffixed secret names per environment: `POSTGRES_USER`/`POSTGRES_PASSWORD` for preview, `POSTGRES_USER_PROD`/`POSTGRES_PASSWORD_PROD` for production

### Step 6: Create GitHub secrets

- Use `gh secret list` to check which secrets already exist in the repo
- Only create secrets that are missing: `CLOUDSTACK_API_KEY`, `CLOUDSTACK_SECRET_KEY`, `SSH_PRIVATE_KEY` (from the generated key), `POSTGRES_USER`, `POSTGRES_PASSWORD` (if database is enabled)
- If the app has custom env vars or secrets, create `SECRET_ENV_VARS` and configure `ENV_VARS` via `gh variable set`

### Step 7: Create caller workflows

- Start with a preview deploy workflow (triggered on push, no domain)
- Create matching teardown workflow
- See [references/workflows.md](references/workflows.md) for templates and input reference

### Step 8: Add production environment (when ready)

- Suggest the user for authorization to create a production environment when ready
- Create a production deploy workflow (triggered on `v*` tags, with custom domain)
- See [DNS Configuration](#dns-configuration-for-custom-domains) for the domain setup procedure
- Use separate Postgres credentials for production

## Development Routine

After setup is complete, use this cycle to deploy and iterate on the application. See [references/setup-and-deploy.md](references/setup-and-deploy.md) for detailed commands.

### Commit, push, and deploy

- Commit and push. Follow the GitHub Actions workflow run.
- If the workflow fails: read the error from the run logs, fix the issue, commit/push, repeat
- Continue until the workflow succeeds

### Verify the running application

- Browse the app at `http://<web_ip>.nip.io` (get `web_ip` from the workflow run summary)
- Use Playwright for browser-based verification (see [references/setup-and-deploy.md](references/setup-and-deploy.md) for setup)
- If the app doesn't work: SSH into the VMs to check logs (use the locally saved SSH key and the public IPs from the workflow output), diagnose, fix source code, commit/push, and repeat the deploy cycle
- Continue until the app works correctly

## Dockerfile Requirements

- Single `Dockerfile` at repository root
- Web app **must listen on port 80** (hardcoded in platform proxy config)
- Default `CMD`/entrypoint serves the web application
- If using workers, the same image must support a separate command passed via `workers_cmd` input
- Health check endpoint at `GET /up` returning HTTP 200 when healthy
- If connecting to a database, read connection from env vars: `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL`. The app must **fail with a clear error** if it needs the database but these variables are missing -- do not silently skip database functionality.

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

## Development Cycle Without Local Environment

When the developer cannot run the language runtime or database locally:

1. Commit and push changes
2. Wait for the deploy workflow to complete (triggered on push for preview)
3. Browse the nip.io preview URL to verify
4. Repeat

**Recommendation**: Start with a single `preview` environment triggered on push, without a domain. This avoids DNS configuration during development. When the app is mature, add a second workflow for `production` with a custom domain.

## References

- **[references/setup-and-deploy.md](references/setup-and-deploy.md)** -- Detailed commands for each setup step, development routine, and SSH debugging
- **[references/workflows.md](references/workflows.md)** -- Complete caller workflow examples (deploy + teardown) with all inputs documented
- **[references/env-vars.md](references/env-vars.md)** -- Environment variables and secrets configuration
- **[references/scaling.md](references/scaling.md)** -- VM plans, worker scaling, disk sizes
- **[references/teardown.md](references/teardown.md)** -- Teardown process, inferring parameters, reading outputs
