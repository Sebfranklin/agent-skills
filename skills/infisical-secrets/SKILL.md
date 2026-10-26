---
name: infisical-secrets
description: Read vault secrets into the app or a config file WITHOUT an agent ever seeing a key. Use when a provider key, API token, or credential lives in Infisical and must reach auth.json, an env var, or a running process. Covers the guard wrapper, the user-run injection pattern, and what is forbidden.
---

# Infisical Secrets on This Machine

Goal: a secret travels **vault → process memory → destination file**, and the agent
never reads, prints, or logs the value. Not "the agent is careful" — the agent has
no access path.

## The hard rule

The agent never runs anything that decrypts or prints secret values:

- `infisical secrets`, `infisical sm secrets`, `infisical export`, `infisical sm export`
- `infisical run`, `infisical sm run`, `infisical inject`, `infisical scan`, `infisical import`
- `age -d`, `gpg -d`, `openssl ... -d`
- `cat`/`head`/`less` on `*.env`, `*.env.*`, `.dev.vars`, `auth.json`
- `printenv`, `env`, `export -p`

No exception for debugging, verification, or "just showing it once".

## What is installed

- CLI: `infisical` v0.44.2 at `~/.npm-global/bin/infisical`
- Project: `76f86766-bacb-41bd-8285-9c1d2a01939d`, linked per repo via `.infisical.json`
- Real binary: `~/.npm-global/bin/infisical.real` (run inside proot Alpine — the bare
  binary crashes `SIGSYS` on Termux/bionic for network ops)

## The guard wrapper

`~/.npm-global/bin/infisical` is a bash wrapper, not the binary. It blocks
`secrets|export|run|inject|scan|import` and exits **126** with:

```
[blocked] infisical '<cmd>' can expose secret values.
```

This guard is **global**, so it blocks the user too. That is intended. The user
bypasses it with:

```bash
INFISICAL_UNGUARDED=1 infisical <cmd>
```

Known gap: `sm secrets` / `sm export` were not originally matched by the pattern.
If touching that wrapper, keep `sm` subcommands in the blocked set.

## The injection pattern (agent writes the script, user runs it)

Never ask the user to paste a key into chat. Write a small script that reads from
the environment and write only success/failure to stdout. The user runs it with the
bypass; the agent never executes the infisical half.

Working example: `~/.pi/agent/set-xkiro-key.py`

```bash
INFISICAL_UNGUARDED=1 infisical run --path=/ -- python3 ~/.pi/agent/set-xkiro-key.py
```

Rules that make this safe:

1. **Read by name from `os.environ`**, never from argv or stdin. argv lands in shell
   history; stdin can echo.
2. **Never print the value.** Print the variable *name* and `len(key)` only.
3. **Write atomically**: temp file, `chmod 600`, `os.replace`.
4. **Be name-tolerant.** The vault's variable name is not knowable in advance, so
   accept an exact-name list first, then any env var whose name contains the
   provider token (e.g. `XKIRO`).
5. **Fail loudly and specifically** when nothing is found, printing the command to
   retry with.

### Template

```python
import json, os, sys

PROVIDER = "xkiro"                      # auth.json key
SUBSTR   = "XKIRO"                      # match any env var containing this
AUTH     = os.path.expanduser("~/.pi/agent/auth.json")

def find_key():
    for name, value in os.environ.items():
        if SUBSTR in name.upper() and value:
            return name, value
    return None, None

name, key = find_key()
if not key:
    sys.exit(f"No env var containing {SUBSTR} is set. Retry via infisical run.")

auth = json.load(open(AUTH))
auth[PROVIDER] = {"type": "api_key", "key": key}
tmp = AUTH + ".tmp"
with open(tmp, "w") as fh:
    json.dump(auth, fh, indent=2)
os.chmod(tmp, 0o600)
os.replace(tmp, AUTH)
print(f"{PROVIDER} written (from ${name}, len={len(key)})")
```

## After the user injects: verify without reading the key

Check presence and shape, never value:

```bash
python3 -c "import json;a=json.load(open('$HOME/.pi/agent/auth.json'));print(list(a.keys()))"
timeout 60 pi -p "say ok" --model <provider>/<model>
```

A real completion proves the key works. `No API key found for <provider>` means the
write did not land — check the variable name and `--path`.

## Pitfalls seen in practice

- **`--path=/` may be wrong.** Secrets often live at `/provider` or `/Learnty_App`.
  A wrong path yields no variable, not an error.
- **The wrapper blocks the user's own command.** Always include the
  `INFISICAL_UNGUARDED=1` prefix in instructions to them.
- **`~/` is NOT your home inside the proot container.** The infisical wrapper runs
  the real binary through `proot-distro login alpine`, so inside that container
  `$HOME` is `/root` and `os.path.expanduser("~")` points at
  `/data/data/com.termux/files/usr/var/lib/proot-distro/containers/alpine/rootfs/root`.
  A script that hardcodes `~/.pi/agent/auth.json` therefore writes **inside the
  container**, not into Termux, and silently succeeds. Symptom: the script prints
  `key written to /root/.pi/agent/auth.json` and Pi still says `No API key found`.
  Fix: use an absolute Termux path in the script
  (`/data/data/com.termux/files/home/.pi/agent/auth.json`), or merge the container
  copy back afterwards and delete it.
- **`/models` succeeding does not mean inference works.** A key can return 200 on
  `GET /v1/models` and still be rejected on `POST /v1/chat/completions` with
  `Invalid or disabled ClientApiKey`. Always verify with a real completion, not a
  model list.
- **`agent-proxy` is not a working broker here.** Verified: zero proxied services,
  and `bubblewrap` is unavailable in Termux so sandboxing degrades to `--no-sandbox`.
  Do not propose it as a secrets-isolation solution.
- **Never write a dotenv to disk** as a "convenience". If a `.env` must exist for a
  tool, the user creates it and deletes it, or it goes to `/dev/shm`.
- **Rotate on any leak.** A value printed once is compromised even if deleted from
  the transcript.

## Verification checklist

- [ ] Agent ran no `infisical secrets|export|run|inject` command
- [ ] No secret value appears in transcript, logs, or committed files
- [ ] Destination file is mode 600
- [ ] A real API call with the configured provider succeeds
- [ ] Gitleaks pre-commit hook present in any repo touched
