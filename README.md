# Agent Skills

A working set of agent skills: folders of plain instructions an AI coding agent
loads only when a task needs them. Written for [Pi](https://github.com/earendil-works/pi),
works in Claude Code, Codex, Cursor, Gemini CLI and anything else that reads a
`SKILL.md`.

## Install everything

```bash
npx skills add https://github.com/Sebfranklin/agent-skills
```

## Install one

```bash
npx skills add https://github.com/Sebfranklin/agent-skills --skill ffmpeg
```

Add `-g` to install for all projects instead of the current one.

## Manual install

No `npx` needed. Copy any folder into your agent's skills directory:

```bash
git clone https://github.com/Sebfranklin/agent-skills
cp -r agent-skills/skills/* ~/.agents/skills/     # Pi, generic
cp -r agent-skills/skills/* ~/.claude/skills/     # Claude Code
```

Start a new agent session afterwards so it picks the skills up.

## What is in here

| Skill | Use it for |
|---|---|
| `agentrouter` | Wiring and debugging an AgentRouter gateway provider. Diagnoses 401, 402, 503 and 400 by status code. |
| `ffmpeg` | Video and audio conversion, resizing, compression, audio extraction. |
| `find-skills` | Discovering and installing more skills from the ecosystem. |
| `frontend-design` | Picking a deliberate visual direction before writing styling code. |
| `here-now` | Publishing files or a static site to a live URL in one command. |
| `image-manipulation-image-magick` | Image resizing, format conversion, batch processing, metadata. |
| `infisical-secrets` | Getting a vault secret into an app without the agent ever seeing the key. |
| `motion-director` | Motion design, animation direction, programmatic video. |
| `pdf-to-markdown` | Converting PDFs to clean Markdown offline, with no context bloat. |
| `strip-ai-metadata` | Removing C2PA, IPTC, XMP and EXIF AI provenance tags before upload. |

## Notes on two of them

`infisical-secrets` describes a guard wrapper and injection scripts specific to
one machine. Read the paths before using it; the pattern transfers, the literal
paths do not.

`here-now` is a copy of the vendor skill and can lag the published version. The
vendor ships its own installer:

```bash
npx skills add heredotnow/skill --skill here-now -g
```

Use that when you want the current one.

## Adding your own

A skill is a folder with a `SKILL.md`. The frontmatter needs two fields:

```markdown
---
name: my-skill
description: When to use this, phrased so an agent can match it to a task.
---

# My Skill

Instructions here.
```

Put scripts or assets beside `SKILL.md` and reference them by relative path.
Commit, and anyone can install it with the command at the top of this file.

## Licence

Each skill keeps its own licence where one exists. `frontend-design` is
Anthropic's, under the terms in its `LICENSE.txt`. The rest are personal notes.
