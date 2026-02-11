# ADR-011: Teardown-and-Redeploy as Recovery Strategy

## Status

Accepted

## Context

Deployments can fail in ways that leave the target VMs in an inconsistent state:

- A `kamal setup` failure may leave a partially configured accessory (e.g., a PostgreSQL container that started but did not complete initialization).
- A failed container swap may leave the old container stopped but not removed, and the new container not started.
- Docker daemon issues, disk full conditions, or interrupted SSH connections can leave containers in unexpected states.

Several recovery approaches were considered:

- **Manual SSH cleanup:** SSH into the affected VM and manually remove containers, volumes, and configurations. This requires deep knowledge of Docker internals and the specific failure mode.
- **Kamal accessory commands:** Use `kamal accessory reboot` or `kamal app remove` to clean up specific components. This sometimes works but can fail if the state is sufficiently broken.
- **Full teardown and redeploy:** Destroy all CloudStack resources (VMs, IPs, volumes) and re-provision from scratch.

## Decision

The standard recovery procedure is to run the Teardown workflow to destroy all CloudStack infrastructure, then re-run the Deploy workflow from scratch.

Operators should not go below the Kamal abstraction layer. No manual `docker rm`, `docker volume rm`, or SSH-based cleanup. If Kamal cannot recover the deployment, the environment is torn down and rebuilt.

## Consequences

**Positive:**

- Clean-slate approach eliminates all state-related issues. There is no accumulated cruft, no orphaned containers, no corrupted volumes.
- Simple mental model for operators: if it is broken, tear it down and rebuild.
- Avoids accumulating workarounds, one-off cleanup scripts, and undocumented manual steps.
- The idempotent provisioning design (ADR-005) means teardown and redeploy follows the same path as a fresh deployment.
- Recovery time is bounded by CloudStack provisioning speed (typically a few minutes for VM creation).

**Negative:**

- Destroys all state, including database data on attached volumes. Data must be backed up externally before teardown if it needs to be preserved.
- Costs time to re-provision VMs, re-install Docker, and re-deploy the application. Not suitable for situations where downtime must be minimized.
- Does not build operational knowledge about failure modes. Operators may not learn why a deployment failed if the evidence is destroyed.
- Wasteful of CloudStack resources if failures are frequent -- each cycle creates and destroys VMs and IP allocations.
