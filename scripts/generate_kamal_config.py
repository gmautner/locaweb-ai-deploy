#!/usr/bin/env python3
"""Generate Kamal deploy config from provisioning output and workflow inputs.

Reads from environment:
  INPUT_WORKERS_ENABLED - Whether workers are enabled
  INPUT_WORKERS_CMD     - Command for worker containers
  INPUT_DB_ENABLED      - Whether database is enabled
  INPUT_DOMAIN          - Custom domain (optional, enables SSL via Let's Encrypt)
  REPO_NAME             - Repository name
  REPO_FULL             - Full repository path (owner/name)
  REPO_OWNER            - Repository owner

Reads from files:
  /tmp/provision-output.json      - Provisioning output (IPs, etc.)
  /tmp/kamal_custom_vars.json     - Custom clear env vars from KAMAL_VARS
  /tmp/kamal_custom_secrets.json  - Custom secret env var names from KAMAL_SECRETS

Outputs:
  config/deploy.yml - Kamal deployment configuration
"""
import json
import os

import yaml

d = json.load(open('/tmp/provision-output.json'))

workers_enabled = os.environ.get('INPUT_WORKERS_ENABLED') == 'true'
workers_cmd = os.environ.get('INPUT_WORKERS_CMD', '')
db_enabled = os.environ.get('INPUT_DB_ENABLED') == 'true'
domain = os.environ.get('INPUT_DOMAIN', '').strip()
repo_name = os.environ['REPO_NAME']
repo_full = os.environ['REPO_FULL']
repo_owner = os.environ['REPO_OWNER']

web_ip = d.get('web_ip', '')
worker_ips = d.get('worker_ips', [])
db_ip = d.get('db_ip', '')
db_internal_ip = d.get('db_internal_ip', '')

config = {
    'service': repo_name,
    'image': repo_full,
    'registry': {
        'server': 'ghcr.io',
        'username': repo_owner,
        'password': ['KAMAL_REGISTRY_PASSWORD'],
    },
    'ssh': {
        'user': 'root',
        'keys': ['.kamal/ssh_key'],
    },
    'servers': {
        'web': {
            'hosts': [web_ip],
        },
    },
    'proxy': {
        'host': domain if domain else f'{web_ip}.nip.io',
        'app_port': 80,
        'forward_headers': False,
        'ssl': bool(domain),
        'healthcheck': {
            'path': '/up',
            'interval': 3,
            'timeout': 5,
        },
    },
    'env': {
        'clear': {
            'BLOB_STORAGE_PATH': '/data/blobs',
        },
    },
    'volumes': [
        '/data/blobs:/data/blobs',
    ],
    'builder': {
        'arch': 'amd64',
    },
    'readiness_delay': 15,
    'deploy_timeout': 180,
    'drain_timeout': 30,
}

if workers_enabled and worker_ips:
    config['servers']['workers'] = {
        'hosts': worker_ips,
        'cmd': workers_cmd,
        'proxy': False,
    }

if db_enabled:
    postgres_db = repo_name
    config['env']['clear']['POSTGRES_HOST'] = db_internal_ip
    config['env']['clear']['POSTGRES_DB'] = postgres_db
    config['env']['secret'] = [
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'DATABASE_URL',
    ]
    config['accessories'] = {
        'db': {
            'image': 'postgres:16',
            'host': db_ip,
            'port': '5432:5432',
            'cmd': '--shared_buffers=256MB',
            'env': {
                'clear': {
                    'POSTGRES_DB': postgres_db,
                    'PGDATA': '/var/lib/postgresql/data/pgdata',
                },
                'secret': [
                    'POSTGRES_USER',
                    'POSTGRES_PASSWORD',
                ],
            },
            'directories': [
                '/data/db:/var/lib/postgresql/data',
            ],
        },
    }

# Merge custom variables and secrets from KAMAL_VARS / KAMAL_SECRETS
custom_vars = json.load(open('/tmp/kamal_custom_vars.json'))
custom_secrets = json.load(open('/tmp/kamal_custom_secrets.json'))
for k, v in custom_vars.items():
    config['env']['clear'][k] = v
if custom_secrets:
    config['env'].setdefault('secret', [])
    config['env']['secret'].extend(custom_secrets)

os.makedirs('config', exist_ok=True)
with open('config/deploy.yml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

print('Generated config/deploy.yml:')
with open('config/deploy.yml') as f:
    print(f.read())
