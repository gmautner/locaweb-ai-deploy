# ADR-009: Aliased Secrets for Environment Variable Mapping

## Status

Superseded by ADR-012

## Context

A typical web application expects database credentials in environment variables with application-specific names, such as `DB_USERNAME` and `DB_PASSWORD`. The infrastructure layer (GitHub Actions secrets, provisioning scripts) stores these same values under infrastructure-oriented names: `POSTGRES_USER` and `POSTGRES_PASSWORD`.

This naming mismatch must be resolved. Several approaches were considered:

- **Duplicate secrets:** Store the same value under both names in GitHub secrets. This works but creates maintenance burden -- two secrets must be updated when a password changes.
- **Shell-level aliasing:** Export mapped variables in a shell step before running Kamal. This works but adds fragile shell scripting outside of Kamal's configuration model.
- **Kamal 2 aliased secrets:** Kamal 2 supports the syntax `APP_NAME:SECRET_NAME` in the `env.secret` array, which exposes `SECRET_NAME`'s value as `APP_NAME` inside the container.

## Decision

Use Kamal 2's aliased secrets feature to map between application-level and infrastructure-level environment variable names. In the generated `config/deploy.yml`:

```yaml
env:
  secret:
    - DB_USERNAME:POSTGRES_USER
    - DB_PASSWORD:POSTGRES_PASSWORD
```

This makes the `POSTGRES_USER` secret available inside the container as `DB_USERNAME`, and `POSTGRES_PASSWORD` as `DB_PASSWORD`.

## Consequences

**Positive:**

- Clean separation between application-level naming conventions and infrastructure-level naming conventions.
- No duplicate secrets to maintain. Each credential is stored exactly once.
- No additional shell scripting or `.kamal/secrets` entries needed for the mapping.
- The mapping is declarative and visible in the Kamal configuration.

**Negative:**

- Requires Kamal 2. This feature is not available in Kamal 1, which limits the ability to downgrade.
- The `APP_NAME:SECRET_NAME` syntax is not immediately obvious to readers unfamiliar with Kamal 2's secret aliasing feature.
- If the application changes its expected environment variable names, the Kamal config generation script must be updated accordingly.
