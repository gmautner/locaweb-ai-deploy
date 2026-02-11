# Project Instructions for Claude

## Documentation Sync

This project maintains three design documents that must be kept in sync as the project evolves:

- `docs/PRD.md` -- Product Requirements Document (goals, requirements, deployment scenarios)
- `docs/architecture.md` -- Architecture Design Document (system design, components, network, security)
- `docs/adr/` -- Architectural Decision Records (individual decisions with context and consequences)

When making changes to the codebase that affect architecture, requirements, or design decisions:

1. Update the relevant document(s) to reflect the change.
2. If a new architectural decision is made, create a new ADR in `docs/adr/` and add it to `docs/adr/index.md`.
3. If an existing ADR is superseded, update its status to "Superseded by ADR-NNN".
4. Keep the "TODOs" and "Future Considerations" sections in the PRD up to date with the latest implementation details.

## External Context Sources

When working on this project, use the following references to get context on the key technologies:

### CloudStack

- **API Docs:** https://cloudstack.apache.org/api/
- **CloudStack Docs:** https://docs.cloudstack.apache.org/
- If needed, clone https://github.com/apache/cloudstack-documentation and https://github.com/apache/cloudstack locally to `~/` to inspect source code and internal workings.

### Kamal

- **Docs:** https://kamal-deploy.org/docs
- If needed, clone https://github.com/basecamp/kamal locally to `~/` to inspect source code and internal workings.

### GitHub Actions

- **Workflow Syntax Reference:** https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
