#!/usr/bin/env python3
"""Write an AgentRouter API key into Pi's auth.json without ever echoing it.

Pi keys credentials by PROVIDER ID, and a custom provider declared in models.json
needs its own auth.json entry. One AgentRouter key therefore has to be written
under every provider ID you configured (e.g. "agentrouter-responses").

Usage:
    python3 set-key.py --providers agentrouter-responses
    python3 set-key.py --providers agentrouter,agentrouter-anthropic --prompt
    INFISICAL_UNGUARDED=1 infisical run --path=/ -- python3 set-key.py

Sources, in priority order:
    1. --prompt          hidden getpass prompt (no echo, no shell history)
    2. env var           AGENTROUTER_API_KEY (or any AGENT_*ROUTER* variable)

Prints only the provider IDs and len(key). Never prints the key.
"""
import argparse
import getpass
import json
import os
import sys

DEFAULT_AUTH = os.path.expanduser("~/.pi/agent/auth.json")
CANDIDATES = (
    "AGENTROUTER_API_KEY",
    "AGENTROUTER",
    "AGENTROUTER_KEY",
    "AGENT_ROUTER_API_KEY",
    "AGENT_ROUTER",
)


def find_env_key():
    for name in CANDIDATES:
        if os.environ.get(name):
            return f"${name}", os.environ[name]
    for name, value in os.environ.items():
        upper = name.upper()
        if "AGENT" in upper and "ROUTER" in upper and value:
            return f"${name}", value
    return None, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--providers", default="agentrouter-responses",
                    help="comma-separated provider IDs from models.json")
    ap.add_argument("--auth", default=DEFAULT_AUTH)
    ap.add_argument("--prompt", action="store_true", help="read the key at a hidden prompt")
    args = ap.parse_args()

    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    if not providers:
        print("no provider IDs given", file=sys.stderr)
        return 2

    source, key = find_env_key()
    if key is None and args.prompt:
        key = getpass.getpass("AgentRouter API key (hidden): ").strip()
        source = "hidden prompt"
    if not key:
        print(
            "No key found.\n"
            "  interactive: python3 set-key.py --prompt\n"
            "  vault:       INFISICAL_UNGUARDED=1 infisical run --path=/ -- python3 set-key.py\n"
            "  env:         export AGENTROUTER_API_KEY=...   (avoid; ends up in history)",
            file=sys.stderr,
        )
        return 1

    try:
        with open(args.auth) as fh:
            auth = json.load(fh)
    except FileNotFoundError:
        auth = {}

    unchanged = [p for p in providers if auth.get(p, {}).get("key") == key]
    for provider in providers:
        auth[provider] = {"type": "api_key", "key": key}

    tmp = f"{args.auth}.tmp"
    with open(tmp, "w") as fh:
        json.dump(auth, fh, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, args.auth)

    print(f"wrote {args.auth} for {', '.join(providers)} (from {source}, len={len(key)})")
    if unchanged:
        print(f"note: already current for {', '.join(unchanged)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
