# Manage Skills

Invoke the manage-skills Python CLI based on the user's subcommand.

The script is at:
```
${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py
```

## Subcommands

### `install <url> [--name <name>] [--path <local_path>]`

```bash
python3 "${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py" install <url> [--name <name>] [--path <local_path>]
```

Clones the repository, creates a symlink in `$SKILLS_HOME`, records the entry in `skill-list.md`, checks for dependency cycles, and creates `~/.claude/commands/<name>.md` if the skill has a `command.md`. Present the confirmation output to the user.

### `sync [name]`

```bash
python3 "${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py" sync [name]
```

Pulls the latest changes for a named skill or all skills. Present the per-skill result to the user.

### `list`

```bash
python3 "${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py" list
```

Reads `skill-list.md` and prints the table with a dependencies column. Render it clearly for the user.

### `check`

```bash
python3 "${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py" check
```

Validates all installed skills for dependency cycles. Reports any cycle found as a path (e.g. `a → b → a`).

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
