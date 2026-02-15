# Setup and Deploy Procedures

All setup steps are idempotent -- safe to re-run across agent sessions. Check for existing resources before creating new ones.

## Table of Contents

### Setup
- [GitHub Repository Setup](#github-repository-setup)
- [SSH Key Generation](#ssh-key-generation)
- [CloudStack Credentials](#cloudstack-credentials)
- [Postgres Credentials](#postgres-credentials)
- [Creating GitHub Secrets](#creating-github-secrets)

### Development Routine
- [Deploy Cycle](#deploy-cycle)
- [App Verification Cycle](#app-verification-cycle)
- [SSH Debugging](#ssh-debugging)

## GitHub Repository Setup

Check if a git remote is already configured:

```bash
git remote -v
```

**If no remote is configured**, ask the user:
- Does an existing GitHub repository already exist for this project?
- Or should a new one be created?

**Existing repo**: Ask the user for the URL, then add it:

```bash
git remote add origin https://github.com/<owner>/<repo>.git
```

**New repo**: Create with the GitHub CLI:

```bash
gh repo create <repo-name> --private --source=. --remote=origin
# Use --public instead of --private if the user prefers a public repo
```

Verify the remote is configured:

```bash
git remote -v
```

## SSH Key Generation

Check if an SSH key already exists for this repo:

```bash
test -f ~/.ssh/<repo-name> && echo "Key exists" || echo "Key missing"
```

If the key does not exist, generate a new Ed25519 SSH key locally:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/<repo-name> -N "" -C "<repo-name>-deploy"
chmod 600 ~/.ssh/<repo-name>
```

If the key already exists, reuse it -- do not overwrite.

This key will be:
- Stored as the `SSH_PRIVATE_KEY` GitHub secret (the private key)
- Used locally to SSH into deployed VMs for debugging
- The public key is derived automatically by the deploy workflow at runtime

## CloudStack Credentials

First check if CloudStack secrets are already set in the repo:

```bash
gh secret list
```

If `CLOUDSTACK_API_KEY` and `CLOUDSTACK_SECRET_KEY` appear in the list, skip this step.

Otherwise, ask the user to provide their CloudStack API credentials. These are issued by the Locaweb Cloud account administrator.

Required values:
- `CLOUDSTACK_API_KEY`
- `CLOUDSTACK_SECRET_KEY`

## Postgres Credentials

Check if Postgres secrets are already set in the repo:

```bash
gh secret list
```

If `POSTGRES_USER` and `POSTGRES_PASSWORD` already appear, skip this step.

Otherwise, ask the user for their preferred PostgreSQL username (e.g., `myapp_user`, `app`, or anything they choose).

Generate a random password for **each** environment:

```bash
# Preview password
openssl rand -base64 32

# Production password (different from preview)
openssl rand -base64 32
```

For multiple environments, use suffixed secret names:
- `POSTGRES_USER` / `POSTGRES_PASSWORD` for preview
- `POSTGRES_USER_PROD` / `POSTGRES_PASSWORD_PROD` for production

The caller workflow passes the correct pair in each environment's `secrets:` block.

## Creating GitHub Secrets

First list existing secrets to avoid overwriting them:

```bash
gh secret list
gh variable list
```

Only create secrets that are **not already present**. Use `gh secret set` directly -- do not ask the user to do it manually in the GitHub UI.

```bash
# CloudStack credentials (skip if already set)
gh secret set CLOUDSTACK_API_KEY --body "<value from user>"
gh secret set CLOUDSTACK_SECRET_KEY --body "<value from user>"

# SSH private key (skip if already set)
gh secret set SSH_PRIVATE_KEY < ~/.ssh/<repo-name>

# Postgres credentials for preview (skip if already set)
gh secret set POSTGRES_USER --body "<username chosen by user>"
gh secret set POSTGRES_PASSWORD --body "<generated password>"

# Postgres credentials for production (skip if already set)
gh secret set POSTGRES_USER_PROD --body "<username chosen by user>"
gh secret set POSTGRES_PASSWORD_PROD --body "<generated password>"
```

For app-specific environment variables:

```bash
# Clear (non-secret) env vars
gh variable set ENV_VARS --body "APP_ENV=preview
LOG_LEVEL=debug"

# Secret env vars
gh secret set SECRET_ENV_VARS --body "API_KEY=<value>
SMTP_PASSWORD=<value>"
```

Verify all secrets are set:

```bash
gh secret list
gh variable list
```

## Deploy Cycle

After committing workflows and pushing:

### 1. Monitor the workflow run

```bash
# Watch the latest run
gh run watch

# Or list runs and watch a specific one
gh run list --limit=5
gh run watch <run-id>
```

### 2. If the workflow fails

Read the error:

```bash
# View the failed run's logs
gh run view <run-id> --log-failed
```

Common failure causes:
- **Missing secrets**: `gh secret list` to verify all required secrets exist
- **Dockerfile issues**: Build failures, wrong port, missing health check
- **Permission errors**: Ensure `permissions: contents: read, packages: write` in the caller workflow
- **Input errors**: Invalid zone, plan name, or type mismatches

Fix the issue, commit, and push. The preview workflow (triggered on push) will start a new run automatically.

### 3. Repeat until successful

Continue the cycle: read error -> fix -> commit/push -> watch run. Do not give up after one failure -- iterate.

### 4. On success, extract deployment info

```bash
# Get the web IP from the latest successful run
gh run view <run-id>

# Or download the provision-output artifact
gh run download <run-id> --name provision-output --dir /tmp/provision-output
cat /tmp/provision-output/provision-output.json
```

The app URL is `http://<web_ip>.nip.io` (for preview without a domain).

## App Verification Cycle

After the workflow succeeds, verify the application is working:

### 1. Browse the app

Open `http://<web_ip>.nip.io` in a browser or fetch with curl:

```bash
# Health check
curl -s -o /dev/null -w "%{http_code}" http://<web_ip>.nip.io/up

# Home page
curl -s http://<web_ip>.nip.io/
```

For browser-based verification, use Playwright:

```bash
# Install (one-time, cached for future runs)
npm install playwright
npx playwright install chromium
```

Then use Playwright to navigate pages, take screenshots, fill forms, and verify the app behaves correctly in a real browser.

### 2. If the app doesn't respond or behaves incorrectly

SSH into the VMs to debug. Use the SSH key generated earlier and the public IPs from the workflow output.

See [SSH Debugging](#ssh-debugging) below for detailed commands.

### 3. Fix and redeploy

Fix the source code, commit, push. The preview workflow runs automatically. Watch the run, then verify the app again.

### 4. Repeat until the app works

Continue the cycle: browse -> SSH debug -> fix source -> commit/push -> deploy -> browse.

## SSH Debugging

Use the locally saved SSH key and the public IPs from the workflow output to connect to VMs.

```bash
# SSH into web VM
ssh -i ~/.ssh/<repo-name> root@<web_ip>

# SSH into database VM
ssh -i ~/.ssh/<repo-name> root@<db_ip>

# SSH into a worker VM
ssh -i ~/.ssh/<repo-name> root@<worker_ip>
```

### Useful debug commands on the VMs

```bash
# List running containers
docker ps

# View web app logs
docker logs $(docker ps -q --filter "label=service=<repo-name>") --tail 100

# Follow logs in real time
docker logs $(docker ps -q --filter "label=service=<repo-name>") -f

# Check if the app responds locally on port 80
curl -s localhost:80/up

# View kamal-proxy logs (web VM only)
docker logs kamal-proxy --tail 50

# Check Postgres container logs (database VM only)
docker logs $(docker ps -q --filter "ancestor=postgres:16") --tail 100

# Check disk mounts
df -h /data/blobs    # web VM
df -h /data/db       # database VM

# Check container environment variables
docker exec $(docker ps -q --filter "label=service=<repo-name>") env
```
