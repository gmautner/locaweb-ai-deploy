# ADR-017: Disaster Recovery via Snapshots

**Status:** Accepted
**Date:** 2026-02-12

## Context

The provisioning script had no mechanism to create volumes from snapshots. When a deployment is lost (teardown, VM failure, or intentional migration), the data on the blob and database disks is gone even though snapshots exist.

We needed a way to recover a deployment from existing snapshots without requiring manual CloudStack API interaction.

### Cross-zone replication

CloudStack's `createSnapshot` and `createSnapshotPolicy` APIs accept a `zoneids` parameter for cross-zone replication, and there is a `copySnapshot` API. However, Locaweb Cloud does not support cross-zone snapshot copying (`copySnapshot` returns error 530). This means snapshots are only available in the zone where the original volume existed. If cross-zone support is added in the future, the recovery code will work without changes — it simply looks for snapshots in the target zone.

## Decision

Add a `recover` boolean input to the deploy workflow. When enabled, the provisioning script:

1. Runs pre-flight checks: verifies no existing deployment (network or volumes) in the target zone, and that required snapshots exist in BackedUp state.
2. Creates data volumes from the latest available snapshots (both MANUAL and RECURRING types are considered) instead of blank disks.
3. Tags and attaches the recovered volumes to the new VMs.
4. Creates new snapshot policies on the recovered volumes for ongoing protection.

The recovery flow reuses the existing provisioning pipeline for all non-disk resources (network, VMs, IPs, firewall rules). Only the disk creation step differs.

No changes to userdata scripts were needed because both `web_vm.sh` and `db_vm.sh` already check `blkid` before formatting, so recovered volumes (which already have ext4 filesystems with data) are not wiped.

The `find_network` and `find_volume` helpers were made zone-aware (accepting an optional `zone_id` parameter) as a general improvement that benefits both normal and recovery flows.

## Consequences

### Positive

- Disaster recovery is a single workflow dispatch with `recover=true` after teardown/loss.
- Pre-flight checks prevent accidental data loss by refusing to recover over an existing deployment.
- Recovered deployments get their own snapshot policies, maintaining the same data protection as fresh deployments.
- No changes to the application or userdata scripts were required.
- If cross-zone snapshot support is added to Locaweb Cloud in the future, the recovery code works for cross-zone recovery without changes.

### Negative

- Currently limited to same-zone recovery due to Locaweb Cloud not supporting cross-zone snapshot operations.
- The existing deployment must be torn down before recovery can proceed (pre-flight checks enforce this).
- Manual snapshots must be created for immediate recovery testing since daily snapshots run on a schedule (06:00 UTC).

### Neutral

- Zone-aware `find_network` and `find_volume` are backward-compatible (zone_id defaults to None, preserving existing behavior).
