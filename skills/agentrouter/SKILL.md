---
name: agentrouter
description: Use when wiring, fixing, or debugging an AgentRouter (agentrouter.org / co.agentrouter.org) gateway provider in Pi, Codex, Claude Code, or any OpenAI/Anthropic-compatible client — especially when requests fail with HTTP 401 "unauthorized client detected", 503 "无可用渠道", 402 budget-pool exhaustion, or 400 "不支持 /v1/chat/completions 请改用 /v1/responses".
---

# AgentRouter Setup & Debugging

## Overview

AgentRouter is a model-aggregating gateway. Its failures are unusually misleading: four
different root causes produce errors that look like key problems. Diagnose by **HTTP status
code**, in the order below — the code alone identifies the layer.

**Core principle: `pi -p` is the only trustworthy client.** Every raw HTTP probe of
AgentRouter (curl, python, any library) returns
`401 unauthorized client detected, contact support for assistance at https://discord.gg/HgekCyHJqB`.
That is a **client fingerprint check**, not a key check. It fires before auth is evaluated, so
it tells you nothing about whether your key is valid. Only requests that look like a supported
CLI harness (`pi`, `claude`, `codex`) get past it.

## Diagnose by status code

| Status | Meaning | Action |
|---|---|---|
| `401 unauthorized client detected` | Fingerprint rejection, **not** a bad key | Re-test with `pi -p`. Ignore this code entirely from raw HTTP. |
| `401 Invalid API Key!` (from `co.agentrouter.org`) | Different host, different key namespace | Use `https://agentrouter.org/v1`, not the `co.` host, for the same key. |
| `503 当前分组 default 下对于模型 X 无可用渠道` | **Authenticated fine**, but model X has no upstream channel for your group | Key is GOOD. Model is wrong/offline/not entitled. Get the real list from the user's console. |
| `400 模型 X 不支持 /v1/chat/completions 接口，请改用 /v1/responses` | Model only speaks the Responses API | Switch provider `api` to `openai-responses`. |
| `402 Budget pool quota has been exhausted` | Account quota, not config | Nothing to fix in config. User must top up. |

The `503` row is the load-bearing one: **the gateway cannot name your group until it has
already authenticated your key.** If you see a 503, stop suspecting the key.

## The model list problem (why you cannot discover models programmatically)

Three independent obstacles, all of which bite:

1. **`GET /v1/models` is fingerprinted out.** Returns the 401 above for every non-harness
   client. There is no way to enumerate models with your key from a script.
2. **The docs site is a VitePress SPA and the pricing page is JS-rendered.** `curl` gets a
   shell with no model IDs; `fetch_content` reports "Page appears to be JavaScript-rendered".
   You can still read the sidebar/model prose from `https://agentrouter.org/docs/` raw HTML.
3. **Docs list ≠ your entitlements.** The docs describe what the *platform* offers
   (`deepseek-v4-flash`, `glm-5.3`, `claude-opus-5`, …). Your **account group** may have
   channels for a completely different, much smaller set. Their own docs say it:
   *"支持的模型是动态调整的，会随资源情况上下线，请始终以 console/personal 展示的列表为准"* —
   always trust the console, not the docs.

**Therefore: ask the user for their console model list at the FIRST 503.** Do not spend turns
guessing IDs against a docs page. One question ("what does console/personal show?") saves
five probe cycles.

## Setup

### 1. Write the key without exposing it

```bash
python3 skill-dir/scripts/set-key.py --prompt        # hidden getpass prompt
# or via vault:
INFISICAL_UNGUARDED=1 infisical run --path=/ -- python3 skill-dir/scripts/set-key.py
```

Pi keys credentials **by provider ID**, so a single AgentRouter key must be written under
*every* provider ID you declare in `models.json` (e.g. `agentrouter-responses`). A new
provider ID with no `auth.json` entry yields `No API key found for <id>` — that error means
"copy the key to this ID", not "the key is bad".

### 2. Provider block

`~/.pi/agent/models.json` — use the Responses API; current AgentRouter models reject
chat-completions:

```json
{
  "providers": {
    "agentrouter-responses": {
      "baseUrl": "https://agentrouter.org/v1",
      "api": "openai-responses",
      "apiKey": "$AGENTROUTER_API_KEY",
      "models": [
        { "id": "gpt-6.1-sol", "name": "GPT-6.1 Sol (AgentRouter)", "reasoning": true,
          "input": ["text"], "contextWindow": 400000, "maxTokens": 32768,
          "cacheRetention": "none" },
        { "id": "gpt-5.6-sol", "name": "GPT-5.6 Sol (AgentRouter)", "reasoning": true,
          "input": ["text"], "contextWindow": 400000, "maxTokens": 32768,
          "cacheRetention": "none" }
      ]
    }
  }
}
```

Anthropic-protocol variant for Claude models: `baseUrl: "https://agentrouter.org"` (**no**
`/v1`) with `api: "anthropic-messages"`. Mixing `/v1` into the Anthropic base URL 404s.

### 3. Verify in this exact order

```bash
pi auth check --provider agentrouter-responses --json   # expect {"status":"ready",...}
AGENTROUTER_API_KEY=dummy pi --list-models agentrouter  # models.json wired correctly?
pi -p --no-tools --no-session --model agentrouter-responses/gpt-6.1-sol "Say AR-OK"
pi -p --no-session --model agentrouter-responses/gpt-6.1-sol -t bash "Run: echo hi. Reply with only the output."
```

The last command proves tool-calling works — a text-only reply is not enough.

## Common mistakes

| Symptom | Wrong conclusion | Right action |
|---|---|---|
| Scripted `/v1/models` 401s | "key rejected" | Fingerprint. Use `pi -p`. |
| `503 无可用渠道` | "key bad / account unverified" | Key is fine. Ask user for console model list. |
| Every model 503s | "gateway is down" | Your group has a different entitlement set than the docs. |
| `400 ... 请改用 /v1/responses` | "model id wrong" | ID is right; `api` must be `openai-responses`. |
| New provider → `No API key found` | "need to re-enter key" | Add the same key under the new provider ID in `auth.json`. |
| One model 402 while others work | "config bug" | Quota pool empty for that model only. User-side. |

## Reference files

- `scripts/set-key.py` — writes the key to `auth.json` for N provider IDs, hidden prompt or env, prints only `len()`.
- `scripts/probe.py` — raw-HTTP prober; prints status + model ids/errors only, never the key. Useful to confirm the fingerprint 401 and to test hosts, **not** to enumerate models.

## Real-world timeline (the lesson, compressed)

Wired `agentrouter` with docs model IDs → all 503. Suspected account verification → wrong:
the 503 itself proved auth passed. Switched to a docs-listed `gpt-*` → `400 use /v1/responses`.
Switched API → new provider ID lacked an `auth.json` entry → `No API key found`. User then
reported their real console list (3 `gpt-*` models, no deepseek). Final: 2 of 3 models work,
third is 402 quota. **The single highest-value action was asking for the console list.**
