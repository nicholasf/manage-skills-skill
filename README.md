# manage-skills-skill

A skill that manages other skills. It follows the pnpm model: a global store at `$SKILLS_HOME` holds cloned skill repos, and per-project `skills.md` files declare which skills a project needs at which versions. Projects get `.skills/` symlinks into the global store, so the repos are cloned once and shared across projects.

Unlike pnpm, there is no separate manifest and lockfile — `skills.md` is both, and it's designed to be committed. Versions are pinned as full SHA1s resolved at install time, so teammates and machines get identical skill code.

The other difference from a package manager is the shared secrets layer: skills often need API keys or node credentials that must never be committed. `$SKILLS_HOME/.env` holds these machine-local secrets, scaffolded from each skill's `.env.example`, so skills can find their credentials without hardcoding anything.

Skills marked `load_at_startup` have their `SKILL.md` injected automatically at the start of each Claude Code session. The `context` subcommand, wired into Claude Code's `SessionStart` hook, resolves which `skills.md` to read: it checks the working directory for a local `skills.md` first, and falls back to `$SKILLS_HOME/skills.md` if none is found. This means projects with a committed `skills.md` get their own skill set, while any directory without one gets the global default — no per-project setup required to get started.

---

## Examples

**Install a skill from GitHub:**
```
/manage-skills install https://github.com/nicholasf/ask-remote-agent-skill
```

**Install and pin to an exact SHA1 or tag:**
```
/manage-skills install https://github.com/nicholasf/ask-remote-agent-skill --version abc1234
```
The full SHA1 is resolved via `git rev-parse` and stored. Future `sync` calls will re-checkout that exact commit rather than pulling.

**Install and load the skill's context at every session start:**
```
/manage-skills install https://github.com/nicholasf/ask-remote-agent-skill --load-at-startup
```

**Pull the latest for all unpinned skills; re-checkout pinned SHA1s:**
```
/manage-skills sync
```

**Re-pin an installed skill to a new SHA1 or tag:**
```
/manage-skills sync ask-remote-agent-skill --version abc1234
```

**Initialise per-project skill management in the current directory:**
```
/manage-skills init
```
Creates `skills.md` and `.skills/` in the current directory. Subsequent `install` calls write to the local `skills.md` instead of the global one and symlink into `.skills/`.

**Show all installed skills with their pinned versions and dependencies:**
```
/manage-skills list
```

**Validate the dependency graph for cycles:**
```
/manage-skills check
```

**Set a secret used by one or more skills:**
```
/manage-skills env set POND_HERMES_KEY=your-bearer-token
```

**Show all secret key names (values are never printed):**
```
/manage-skills env list
```

**Scaffold missing keys from each skill's `.env.example`:**
```
/manage-skills env init
```

**Wire up the `context` subcommand in Claude Code's `SessionStart` hook (`settings.json`):**
```json
{
  "type": "command",
  "command": "python3 \"${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py\" context",
  "statusMessage": "Loading skills..."
}
```
At session start, `context` checks the working directory for a local `skills.md`, falls back to `$SKILLS_HOME/skills.md`, and injects the `SKILL.md` of every `load_at_startup` skill into the session context.

---

## How it works

```
$SKILLS_HOME/
  manage-skills-skill/   ← real repo
  ask-remote-agent-skill → ~/code/.../ask-remote-agent-skill  (symlink)
  load-topology-skill    → ~/code/.../load-topology-skill     (symlink)
  skills.md              ← global registry
  .env                   ← secrets (gitignored)
```

`install` clones the repo, creates a symlink in `$SKILLS_HOME`, records the entry in `skills.md`, checks for dependency cycles, and wires up the slash command by symlinking `command.md` into `~/.claude/commands/<name>.md`.

### Versioning

The `version` column in `skills.md` stores a full SHA1. `install --version` and `sync --version` check out the given ref and resolve it to a full SHA1 via `git rev-parse`. Skills without a version track the latest main branch and are updated by `sync`. Since the skills are git repos, any ref git understands — SHA1, tag, or branch name — works.

### Per-project skills

Run `init` inside a project to create a local `skills.md` and `.skills/` directory. Once a local `skills.md` exists, all subcommands read and write to it instead of the global one. The local `skills.md` can be committed so teammates get the same skill set and versions.

```
my-project/
  skills.md     ← per-project registry (commit this)
  .skills/
    ask-remote-agent-skill → $SKILLS_HOME/ask-remote-agent-skill  (symlink)
```

The global `$SKILLS_HOME/skills.md` remains the default when no local `skills.md` is present.

---

## Shared secrets — `.env`

The `.env` layer is a convenience, not managed infrastructure. Individual skills are responsible for reading their own credentials — manage-skills just puts the file in the right place.

In global mode, that file is `$SKILLS_HOME/.env`. In a project with a local `skills.md`, it is `./.env` next to the registry. The `env` subcommands (`set`, `list`, `init`) always operate on whichever file is active. `env list` prints the path at the top so there is no ambiguity.

```bash
# $SKILLS_HOME/.env  (or ./.env in a project)
# Convention: <NODE>_<SERVICE>_<VAR>
POND_HERMES_KEY=your-bearer-token
GOLLUM_HERMES_KEY=your-bearer-token
```

A project `.env` can deliberately carry the same key as the global one with a different value — this is a deliberate overlap, not a collision. The skill reads whichever file it finds; switching between global and per-project mode changes which file that is.

For a concrete example, [ask-remote-agent-skill](https://github.com/nicholasf/ask-remote-agent-skill) stores a bearer token for its agent handle in `.env`. Different projects can point at different agent endpoints by overlapping that key locally.

---

## Setup

Clone this repo, then run:

```bash
bash bootstrap.sh
```

Creates `$SKILLS_HOME` (default `~/.agents/skills`), symlinks this repo into it, and initialises `skills.md`. Add `SKILLS_HOME` to your shell rc file to use a different location.

### Session startup

Add this to your Claude Code `settings.json` `SessionStart` hook to load skills automatically:

```json
{
  "type": "command",
  "command": "python3 \"${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py\" context",
  "statusMessage": "Loading skills..."
}
```

Skills with `load_at_startup: true` in `skills.md` will have their full `SKILL.md` injected into each session's context. When a local `skills.md` exists in the project being opened, it takes precedence over the global one.

---

## Subcommands

**`install <url> [--name <name>] [--path <local_path>] [--version <sha1-or-tag>] [--load-at-startup]`**
Clone, symlink, register, and wire up a skill. Use `--version` to pin to a SHA1 or tag. Use `--path` to point at a local clone instead of cloning fresh.

**`sync [name] [--version <sha1-or-tag>]`**
Pull latest for unpinned skills; re-checkout pinned SHA1s. With `--version`, re-pin the named skill to a new ref.

**`init`**
Initialise a per-project `skills.md` and `.skills/` in the current directory.

**`list`**
Print the skill registry with version and dependency columns.

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
