# ADR-002: Use ghcr.io with GITHUB_TOKEN for Container Registry

## Status

Accepted

## Context

Container images built in the CI/CD pipeline need to be stored in a registry so that Kamal can pull them onto the target VMs during deployment. Several registry options were evaluated:

- **Docker Hub:** The default public registry. Requires a Docker Hub account and access token. Free tier has rate limits and limited private repository support.
- **AWS ECR:** A managed registry tightly integrated with AWS. Requires AWS credentials, IAM configuration, and ECR repository creation. Adds an AWS dependency to a project that otherwise runs on CloudStack.
- **Self-hosted registry:** Full control, but requires provisioning, TLS configuration, storage management, and authentication setup. Significant operational burden.
- **GitHub Container Registry (ghcr.io):** Integrated with GitHub. Authenticated using the `GITHUB_TOKEN` that GitHub Actions provides automatically to every workflow run. No additional accounts or credentials needed.

## Decision

Use GitHub Container Registry (`ghcr.io`) as the container image registry, authenticated with the automatic `GITHUB_TOKEN` provided by GitHub Actions.

Images are pushed with the tag pattern `ghcr.io/<owner>/<repo>:<tag>` and pulled by Kamal on the target VMs using the same token.

## Consequences

**Positive:**

- Zero registry setup. No accounts to create, no repositories to provision, no access policies to configure.
- Automatic token rotation. The `GITHUB_TOKEN` is scoped to the workflow run and expires after the job completes. No long-lived credentials to rotate or leak.
- Images are tied to the GitHub repository, providing a natural association between source code and built artifacts.
- Simpler secrets management overall -- one fewer secret to configure and maintain.

**Negative:**

- Images are hosted on GitHub infrastructure. If GitHub experiences an outage, deployments cannot pull images.
- The `GITHUB_TOKEN` has repository-scoped permissions. Cross-repository image sharing requires additional PAT configuration.
- ghcr.io storage and bandwidth are subject to GitHub's pricing and limits for the organization or user account.
