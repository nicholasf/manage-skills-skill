# Manage Skills

Invoke the manage-skills Python CLI based on the user's subcommand.

The script is at:
```
${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py
```

## Subcommands

### `install <url> [--name <name>] [--path <local_path>] [--version <sha1-or-tag>]`

```bash
python3 "${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py" install <url> [--name <name>] [--path <local_path>] [--version <sha1-or-tag>]
```

Clones the repository, optionally checks out a specific SHA1 or tag (resolved to a full SHA1 and stored), creates a symlink in `$SKILLS_HOME`, records the entry in `skills.md`, checks for dependency cycles, and creates `~/.claude/commands/<name>.md` if the skill has a `command.md`. When run inside a project with a local `skills.md`, also creates a `.skills/<name>` symlink. Present the confirmation output to the user.

### `sync [name] [--version <sha1-or-tag>]`

```bash
python3 "${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py" sync [name] [--version <sha1-or-tag>]
```

Without `--version`: pulls latest for unpinned skills; re-checks out the pinned SHA1 for pinned skills.
With `--version <ref>`: re-pins the named skill to the given SHA1 or tag (resolves and stores the full SHA1). `--version` requires a skill name. Present the per-skill result to the user.

### `init`

```bash
python3 "${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py" init
```

Initialises a per-project `skills.md` and `.skills/` directory in the current working directory. After init, `install` will write to the local `skills.md` and create `.skills/<name>` symlinks. Safe to run once per project.

### `list`

```bash
python3 "${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py" list
```

Reads `skills.md` and prints the table with version and dependencies columns. Render it clearly for the user.

### `check`

```bash
python3 "${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py" check
```

Validates all installed skills for dependency cycles. Reports any cycle found as a path (e.g. `a → b → a`).

## skills.md — global and per-project

`$SKILLS_HOME/skills.md` is the global registry, used when no local `skills.md` is present. Running `init` in a project creates a local `skills.md` that takes precedence for all subcommands, including the SessionStart context hook.

The `version` column stores a full SHA1. Empty means the skill tracks the latest main branch.

## Dependency tracking

Skills declare dependencies in their `SKILL.md` frontmatter:

```yaml
depends_on:
  - other-skill-name
```

`install` checks for cycles before writing anything. `check` can be run at any time to audit the installed set. Cycles are detected with DFS (grey/black colouring).

## Command wiring

When `install` finds a `command.md` in the skill root, it creates a symlink:

```
~/.claude/commands/<name>.md → <local_path>/command.md
```

This registers the skill as a slash command in Claude Code. The symlink is created or replaced on every install.
