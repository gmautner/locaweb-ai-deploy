# ADR-019: Consolidated Dotenv Format for Custom Container Environment Variables

## Status

Accepted (supersedes ADR-013)

## Context

ADR-013 established a convention where individual GitHub secrets and variables with a `KAMAL_` prefix were discovered at deploy time via `toJSON(secrets)` and `toJSON(vars)`, with the prefix stripped before injection into the container.

This approach has two problems for cross-repo reusability:

1. **`toJSON(secrets)` exposes all repository secrets** to the processing step, not just the ones intended for the container.
2. **Reusable workflows (`workflow_call`) cannot pass arbitrary undeclared secrets.** The caller must enumerate every secret in the workflow definition. Individual `KAMAL_`-prefixed secrets cannot be forwarded dynamically across repository boundaries.

The deploy workflow is being prepared as a reusable workflow that external repositories can invoke. A mechanism is needed that works both internally (via `workflow_dispatch`) and externally (via `workflow_call`).

## Decision

Replace the individual `KAMAL_`-prefixed GitHub secrets and variables with two consolidated entries:

- **`SECRET_ENV_VARS`** (GitHub Secret) — dotenv-formatted key=value pairs for secret container env vars.
- **`ENV_VARS`** (GitHub Variable) — dotenv-formatted key=value pairs for clear container env vars.

Example `SECRET_ENV_VARS`:
```
REDIS_URL=redis://localhost:6379
STRIPE_KEY=sk_live_xxx
```

Example `ENV_VARS`:
```
APP_ENV=production
LOG_LEVEL=info
```

Parsing uses the `python-dotenv` library, which follows standard dotenv conventions (quoting, comments, escaping) and matches the format Kamal itself uses for `.kamal/secrets` via the Ruby `dotenv` gem.

When the workflow is invoked externally via `workflow_call`, the caller passes `SECRET_ENV_VARS` as a declared secret and `env_vars` as a declared input. Internally, the workflow reads from `secrets.SECRET_ENV_VARS` and `vars.ENV_VARS` respectively, with a fallback expression (`inputs.env_vars || vars.ENV_VARS`) to support both invocation modes.

## Consequences

**Positive:**

- Only container-intended values are passed to the processing step — no more `toJSON(secrets)` exposing all repository secrets.
- Works identically for internal (`workflow_dispatch`) and external (`workflow_call`) invocation.
- Standard dotenv format is familiar and handles edge cases (quoted values, `#` comments, `=` in values) correctly.
- Adding or removing container env vars requires editing a single secret/variable, not creating/deleting individual entries.

**Negative:**

- Editing a multi-line secret in GitHub's web UI is less convenient than editing individual secrets.
- Adds a `pip install python-dotenv` step to the workflow.
- Breaking change: existing repositories using the old `KAMAL_`-prefixed convention must migrate to the new format.
