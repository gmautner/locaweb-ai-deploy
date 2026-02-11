#!/usr/bin/env python3
"""Create .kamal/secrets and process KAMAL_-prefixed GitHub entries.

Reads from environment:
  ALL_SECRETS      - JSON of all GitHub secrets (from toJSON(secrets))
  ALL_VARS         - JSON of all GitHub variables (from toJSON(vars))
  INPUT_DB_ENABLED - Whether database is enabled

Outputs:
  .kamal/secrets                   - Kamal secrets file with $VAR references
  /tmp/kamal_custom_secrets.env    - Sourceable env file with resolved custom secret values
  /tmp/kamal_custom_vars.json      - Custom clear vars for the config generation step
  /tmp/kamal_custom_secrets.json   - Custom secret names for the config generation step
"""
import json
import os
import shlex

secrets = json.loads(os.environ.get('ALL_SECRETS', '{}'))
variables = json.loads(os.environ.get('ALL_VARS', '{}'))
db_enabled = os.environ.get('INPUT_DB_ENABLED') == 'true'

# Collect KAMAL_-prefixed secrets (strip prefix for the target name)
custom_secrets = {}
for k, v in secrets.items():
    if k.startswith('KAMAL_'):
        stripped = k[len('KAMAL_'):]
        custom_secrets[stripped] = v

# Collect KAMAL_-prefixed variables (strip prefix for the target name)
custom_vars = {}
for k, v in variables.items():
    if k.startswith('KAMAL_'):
        stripped = k[len('KAMAL_'):]
        custom_vars[stripped] = v

# Build .kamal/secrets with $VAR references (no cleartext values)
lines = [
    'KAMAL_REGISTRY_PASSWORD=$KAMAL_REGISTRY_PASSWORD',
]
if db_enabled:
    lines.append('POSTGRES_USER=$POSTGRES_USER')
    lines.append('POSTGRES_PASSWORD=$POSTGRES_PASSWORD')
    lines.append('DATABASE_URL=$DATABASE_URL')
for name in custom_secrets:
    lines.append(f'{name}=${name}')
with open('.kamal/secrets', 'w') as f:
    f.write('\n'.join(lines) + '\n')

# Write a sourceable env file with resolved custom secret values
# for the deploy step to export before running kamal
with open('/tmp/kamal_custom_secrets.env', 'w') as f:
    for name, value in custom_secrets.items():
        f.write(f'export {name}={shlex.quote(value)}\n')

# Write custom vars and secret names for the config generation step
with open('/tmp/kamal_custom_vars.json', 'w') as f:
    json.dump(custom_vars, f)
with open('/tmp/kamal_custom_secrets.json', 'w') as f:
    json.dump(list(custom_secrets.keys()), f)

if custom_vars:
    print(f'Custom clear env vars: {", ".join(custom_vars.keys())}')
if custom_secrets:
    print(f'Custom secret env vars: {", ".join(custom_secrets.keys())}')
