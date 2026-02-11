# ADR-006: Static NAT (1:1) for Public IP Assignment

## Status

Accepted

## Context

CloudStack provides two mechanisms for exposing VMs to the internet:

- **Port forwarding:** Maps specific ports on a shared public IP to specific ports on backend VMs. Multiple VMs can share a single public IP with different port mappings.
- **Static NAT (1:1 mapping):** Associates one public IP exclusively with one VM. All traffic to that public IP is forwarded to the VM, and the VM's outbound traffic appears to come from that public IP.

The deployment model requires:

- SSH access (port 22) to all VMs for Kamal deployment. This is a hard requirement because Kamal operates entirely over SSH, and it runs on GitHub Actions infrastructure which is external to the Locaweb Cloud network.
- HTTP (port 80) and HTTPS (port 443) access to the web VM for application traffic.
- Workers and database VMs need only SSH access.

## Decision

Use static NAT (1:1 IP-to-VM mapping) for all VMs. Each VM receives its own dedicated public IP address. Firewall rules control which ports are accessible:

- **Web VM:** SSH (22), HTTP (80), HTTPS (443).
- **Worker VMs:** SSH (22) only.
- **Database VM:** SSH (22) only.

## Consequences

**Positive:**

- Simple networking model. Every VM is directly addressable by its own public IP. No port mapping tables to maintain.
- Kamal can SSH directly to each VM using its public IP without jump hosts or bastion servers.
- The web VM's public IP can be used directly for DNS records or nip.io addresses.
- Outbound traffic from each VM has a predictable source IP, simplifying allowlist-based integrations.

**Negative:**

- Consumes more public IP addresses. Each VM requires its own IP, which may be constrained in some CloudStack zones.
- All VMs are directly exposed to the internet (filtered by firewall rules). A more secure model would place workers and database VMs on a private network accessible only through the web VM.
- If the CloudStack zone has limited public IP availability, scaling to many workers could exhaust the IP pool.
