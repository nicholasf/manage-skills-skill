# manage-skills-skill

A skill that manages other skills. Skills live anywhere on the filesystem and are symlinked into `$SKILLS_HOME` so agents can discover them in one place. Skills marked `load_at_startup` have their `SKILL.md` injected automatically at the start of each Claude Code session.

---

## Examples

```
/manage-skills install https://github.com/nicholasf/ask-remote-agent-skill
```
Clone and register a skill. Wires up its slash command automatically.

```
/manage-skills install https://github.com/nicholasf/ask-remote-agent-skill --load-at-startup
```
Install and load the skill's context at every session start.

```
/manage-skills sync
```
Pull the latest changes for all installed skills.

```
/manage-skills list
```
Show all installed skills and their dependencies.

```
/manage-skills check
```
Validate the dependency graph — reports any cycles.

```
/manage-skills env set POND_HERMES_KEY=your-bearer-token
```
Write or update a key in `$SKILLS_HOME/.env`.

```
/manage-skills env list
```
Show all key names in `.env` (values are not printed).

```
/manage-skills env init
```
Scaffold `.env` from the `.env.example` files of all installed skills — adds missing keys without overwriting existing ones.

---

## How it works

```
$SKILLS_HOME/
  manage-skills-skill/   ← real repo
  ask-remote-agent-skill → ~/code/.../ask-remote-agent-skill  (symlink)
  load-topology-skill    → ~/code/.../load-topology-skill     (symlink)
  skill-list.md          ← registry
  .env                   ← secrets (gitignored)
```

`install` clones the repo, creates the symlink, records it in `skill-list.md`, checks for dependency cycles, and wires up the slash command by symlinking `command.md` into `~/.claude/commands/<name>.md`.

---

## Shared secrets — `$SKILLS_HOME/.env`

Skills that need API keys or per-node credentials read them from a single shared file: `$SKILLS_HOME/.env`. This file is gitignored and machine-local — it never leaves the machine.

```bash
# $SKILLS_HOME/.env
# Convention: <NODE>_<SERVICE>_<VAR>
POND_HERMES_KEY=your-bearer-token
GOLLUM_HERMES_KEY=your-bearer-token
```

The naming convention is `<NODE>_<SERVICE>_<VAR>`. Each skill's topology column records the env var name it expects (e.g. `hermes_key_env: POND_HERMES_KEY`) so the skill knows where to look without hardcoding node names. Copy `.env.example` from [load-topology-skill](https://github.com/nicholasf/load-topology-skill) as a starting point and add entries as you install skills that need them.

---

## Setup

Clone this repo, then run:

```bash
bash bootstrap.sh
```

Creates `$SKILLS_HOME` (default `~/.agents/skills`), symlinks this repo into it, and initialises `skill-list.md`. Add `SKILLS_HOME` to your shell rc file to use a different location.

### Session startup

Add this to your Claude Code `settings.json` `SessionStart` hook to load skills automatically:

```json
{
  "type": "command",
  "command": "python3 \"${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py\" context",
  "statusMessage": "Loading skills..."
}
```

Skills with `load_at_startup: true` in `skill-list.md` will have their full `SKILL.md` injected into each session's context.

---

## Subcommands

**`install <url> [--name <name>] [--path <local_path>] [--load-at-startup]`**
Clone, symlink, register, and wire up a skill. Use `--path` to point at a local clone instead of cloning fresh.

**`sync [name]`**
Pull latest changes for a named skill or all skills.

**`list`**
Print the skill registry with dependencies.

**`check`**
Audit the dependency graph for cycles.

**`env set KEY=value`**
Write or update a key in `$SKILLS_HOME/.env`.

**`env list`**
Print all key names (not values).

**`env init`**
Scaffold `.env` from the `.env.example` files of every installed skill. Safe to run repeatedly — existing keys are never overwritten.

---

## Dependencies

Skills declare dependencies in their `SKILL.md` frontmatter:

```yaml
---
name: my-skill
depends_on:
  - load-topology-skill
---
```

`install` checks for cycles before writing anything. `check` can be run at any time. Cycles are detected with DFS and reported as a path (e.g. `a → b → a`).
