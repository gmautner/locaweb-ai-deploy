# ADR-004: CloudMonkey CLI for CloudStack API Interaction

## Status

Accepted

## Context

The provisioning workflow needs to interact with the Apache CloudStack API to create and manage virtual machines, networks, volumes, firewall rules, and IP addresses. Several approaches were considered:

- **Terraform:** A mature infrastructure-as-code tool with a CloudStack provider. However, Terraform requires persistent state management, and the state file contains sensitive information (API keys, resource IDs). Securing state storage (e.g., S3 backend with encryption, state locking) adds significant operational complexity for what is intended to be a self-contained workflow.
- **Direct HTTP API calls:** CloudStack exposes a REST-like API with HMAC-signed requests. Constructing and signing requests manually is error-prone and requires implementing the signing algorithm.
- **Apache CloudStack Python SDK (cs):** A Python library that wraps the API. Adds a Python package dependency and requires understanding the SDK's abstractions.
- **CloudMonkey CLI (cmk):** The official Apache CloudStack CLI tool. A single binary that handles API signing, provides tab completion, and outputs structured JSON. Can be called from Python as a subprocess.

## Decision

Use CloudMonkey CLI (`cmk`) with JSON output mode, invoked from Python using `subprocess` with retry logic and exponential backoff.

The Python provisioning script constructs `cmk` commands, parses the JSON output, and handles transient API errors by retrying with increasing delays.

## Consequences

**Positive:**

- Simple installation. CloudMonkey is distributed as a single binary that can be downloaded in the CI/CD environment.
- Familiar CLI interface. CloudStack administrators already know `cmk` commands, making the provisioning script readable.
- JSON output mode provides structured data that Python can parse directly with `json.loads()`.
- Retry with exponential backoff handles transient CloudStack API errors (timeouts, rate limits, async job delays) gracefully.
- No Python SDK dependency to install and maintain.

**Negative:**

- Subprocess overhead. Each API call spawns a new `cmk` process, which is slightly slower than in-process SDK calls. For the number of calls in a typical provisioning run, this is negligible.
- Error handling depends on parsing `cmk`'s exit codes and output, which may be less structured than SDK exceptions.
- The `cmk` binary version must be compatible with the CloudStack API version in use. Version mismatches can cause subtle issues.
