#!/usr/bin/env python3
"""Resolve the latest supabase/postgres image tag for major version 17.

Queries Docker Hub for supabase/postgres tags, filters to 4-component numeric
tags (a.b.c.d) under major version 17, and prints the full image reference
(e.g. supabase/postgres:17.6.1.084) to stdout.

Exit codes:
  0 - Success
  1 - No eligible tag found or Docker Hub unreachable
"""
import re
import sys

import requests

REPO = "supabase/postgres"
TAG_URL = f"https://hub.docker.com/v2/repositories/{REPO}/tags"
TAG_RE = re.compile(r"^17\.\d+\.\d+\.\d+$")


def parse_version(tag):
    return tuple(int(p) for p in tag.split("."))


def main():
    try:
        resp = requests.get(TAG_URL, params={"page_size": 50}, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"Error fetching tags from Docker Hub: {exc}", file=sys.stderr)
        sys.exit(1)

    tags = [
        t["name"]
        for t in resp.json().get("results", [])
        if TAG_RE.match(t["name"])
    ]

    if not tags:
        print("No eligible supabase/postgres 17.x.x.x tag found", file=sys.stderr)
        sys.exit(1)

    best = max(tags, key=parse_version)
    print(f"{REPO}:{best}")


if __name__ == "__main__":
    main()
