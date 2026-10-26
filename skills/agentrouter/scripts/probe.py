#!/usr/bin/env python3
"""Raw-HTTP prober for AgentRouter. Prints status codes and error text -- never the key.

Purpose: distinguish TRANSPORT/HOST problems from MODEL-ENTITLEMENT problems.
It deliberately does NOT enumerate models: GET /v1/models is rejected by
AgentRouter's client fingerprint check (401 "unauthorized client detected") for
every non-harness client, so a 401 here means nothing about your key. Use Pi for
model discovery and real tests:

    pi --list-models agentrouter
    pi -p --no-tools --no-session --model agentrouter-responses/<model> "Say AR-OK"

Usage:
    python3 probe.py chat <model> [--api responses|completions]
    python3 probe.py anthropic <model>
    python3 probe.py host <base-url>        # connectivity/HTML-vs-API check
    python3 probe.py key                    # key length + charset only
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

AUTH = os.path.expanduser("~/.pi/agent/auth.json")
OPENAI_BASE = os.environ.get("AR_OPENAI_BASE", "https://agentrouter.org/v1")
ANTHROPIC_BASE = os.environ.get("AR_ANTHROPIC_BASE", "https://agentrouter.org")
KEY_PROVIDERS = ("agentrouter-responses", "agentrouter", "agentrouter-anthropic")


def get_key():
    with open(AUTH) as fh:
        auth = json.load(fh)
    for provider in KEY_PROVIDERS:
        entry = auth.get(provider) or {}
        if entry.get("key"):
            return provider, entry["key"]
    raise SystemExit(f"no AgentRouter key in {AUTH} (looked for {', '.join(KEY_PROVIDERS)})")


def call(url, body, extra=None):
    _, key = get_key()
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + key}
    headers.update(extra or {})
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


def explain(status, text):
    if status == 401 and "unauthorized client" in text:
        return "FINGERPRINT REJECTION -- not a key problem. Re-test with `pi -p`."
    if status == 503 and "无可用渠道" in text:
        return "AUTHENTICATED, but that model has no channel for your group. Ask the user for their console model list."
    if status == 400 and "/v1/responses" in text:
        return "MODEL NEEDS THE RESPONSES API -- set provider api to openai-responses."
    if status == 402:
        return "ACCOUNT QUOTA -- nothing to fix in config."
    if status == 200:
        return "OK"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["chat", "anthropic", "host", "key"])
    ap.add_argument("target", nargs="?")
    ap.add_argument("--api", default="responses", choices=["responses", "completions"])
    args = ap.parse_args()

    if args.mode == "key":
        provider, key = get_key()
        printable = all(33 <= ord(c) <= 126 for c in key)
        print(f"provider={provider} len={len(key)} printable_ascii={printable} "
              f"has_whitespace={any(c.isspace() for c in key)}")
        return 0

    if args.mode == "host":
        base = (args.target or OPENAI_BASE).rstrip("/")
        req = urllib.request.Request(base + "/", headers={"User-Agent": "curl/8"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                head = r.read(200).decode("utf-8", "replace")
                kind = "HTML (SPA, not an API root)" if head.lstrip().startswith("<") else "API-ish"
                print(f"{base} -> HTTP {r.status} {kind}")
        except urllib.error.HTTPError as e:
            print(f"{base} -> HTTP {e.code} {e.read()[:200].decode('utf-8', 'replace')}")
        except Exception as e:  # noqa: BLE001
            print(f"{base} -> {type(e).__name__}: {e}")
        return 0

    if not args.target:
        print(f"{args.mode} needs a model id", file=sys.stderr)
        return 2

    if args.mode == "chat":
        if args.api == "responses":
            status, text = call(OPENAI_BASE + "/responses",
                                {"model": args.target, "input": "Say OK",
                                 "max_output_tokens": 32})
        else:
            status, text = call(OPENAI_BASE + "/chat/completions",
                                {"model": args.target, "max_tokens": 16,
                                 "messages": [{"role": "user", "content": "Say OK"}]})
    else:
        _, key = get_key()
        status, text = call(ANTHROPIC_BASE + "/v1/messages",
                            {"model": args.target, "max_tokens": 16,
                             "messages": [{"role": "user", "content": "Say OK"}]},
                            {"x-api-key": key, "anthropic-version": "2023-06-01"})

    print(f"{args.mode} {args.target}: HTTP {status} {text[:300]}")
    hint = explain(status, text)
    if hint:
        print("=>", hint)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
