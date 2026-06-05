---
name: manage-skills
description: Install, sync, and list skills from git URLs into SKILLS_HOME.
---

# Manage Skills

Invoke the manage-skills Python CLI based on the user's subcommand.

The script is at:
```
${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py
```

## Subcommands

### `/manage-skills install <url> [--name <name>] [--path <local_path>]`

Run:
```bash
python3 "${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py" install <url> [--name <name>] [--path <local_path>]
```

Clones the repository, creates a symlink in SKILLS_HOME, and records the entry in skill-list.md. Present the confirmation output to the user.

### `/manage-skills sync [name]`

Run:
```bash
python3 "${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py" sync [name]
```

Pulls the latest changes for a named skill or all skills. Present the per-skill result to the user.

### `/manage-skills list`

Run:
```bash
python3 "${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py" list
```

Reads skill-list.md and prints the table. Render it clearly for the user.

### `/manage-skills` (no args)

Run:
```bash
python3 "${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py"
```

Prints usage. Display it to the user.
