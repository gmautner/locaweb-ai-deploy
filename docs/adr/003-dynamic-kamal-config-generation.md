# ADR-003: Generate Kamal Config Dynamically at Deploy Time

## Status

Accepted

## Context

Kamal reads its configuration from `config/deploy.yml`. This file must contain:

- The IP addresses of target VMs (web servers, workers, database hosts).
- The Docker image name including the registry path and tag.
- Conditional sections for workers and database accessories, depending on workflow inputs.
- Repository metadata such as the application name.

These values are not known at development time. VM IP addresses come from the CloudStack provisioning step. The image tag includes the Git SHA. Whether workers or a database are needed depends on the workflow inputs provided by the user at deploy time.

Committing a static `config/deploy.yml` to the repository would immediately drift from the actual infrastructure state.

## Decision

Generate `config/deploy.yml` dynamically at deploy time using a Python script. The script takes provisioning output (VM IPs, resource IDs) and workflow inputs (worker count, database toggle, domain) as parameters and produces the complete Kamal configuration file.

The generated config is never committed to the repository. It exists only within the GitHub Actions runner for the duration of the deployment workflow.

## Consequences

**Positive:**

- Configuration always reflects the actual infrastructure state. No drift between what is committed and what is live.
- Conditional sections (workers, database accessories) are included or omitted based on actual workflow inputs, avoiding Kamal errors from empty host lists or unused accessories.
- The generated config is visible in workflow logs, aiding debugging.
- A single source of truth: the Python generation script defines the configuration schema, and the provisioning output provides the values.

**Negative:**

- Adds complexity to the workflow. Developers must understand both the Python generation script and the resulting Kamal YAML format.
- The config cannot be inspected by simply reading the repository -- it must be generated or viewed in workflow logs.
- Changes to the Kamal config format require updating the Python script, not a YAML file. This is less intuitive for users familiar with Kamal's standard configuration approach.
