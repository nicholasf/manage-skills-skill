# manage-skills-skill

A skill that manages other skills. It's skills all the way down.

This skill organises other skills under a common location via symlinks. Skills can live anywhere on the filesystem and get symlinked into `$SKILLS_HOME`, so agents can discover them all in one place. Skills marked `load_at_startup` have their `SKILL.md` loaded automatically at the start of each Claude Code session.

## Setup

Clone this repo, then run:
```bash
bash bootstrap.sh
```

Creates `$SKILLS_HOME` (default `~/.agents/skills`), symlinks this repo into it, and initialises `skill-list.md` with manage-skills-skill as the first entry. Set `SKILLS_HOME` in your shell rc file to use a different location.

## Usage

Install a skill from a git URL:
```bash
python3 manage_skills.py install https://github.com/nicholasf/ask-foreign-agent-skill
```

Install and load at session start:
```bash
python3 manage_skills.py install https://github.com/nicholasf/ask-foreign-agent-skill \
  --name ask-foreign-agent \
  --path ~/code/github/nicholasf/ask-foreign-agent-skill \
  --load-at-startup
```

Sync all installed skills:
```bash
python3 manage_skills.py sync
```

Sync one skill:
```bash
python3 manage_skills.py sync ask-foreign-agent
```

List installed skills:
```bash
python3 manage_skills.py list
```

## Session startup

Add this to your Claude Code `settings.json` `SessionStart` hook to load skills automatically:
```json
{
  "type": "command",
  "command": "python3 \"${SKILLS_HOME:-$HOME/.agents/skills}/manage-skills-skill/manage_skills.py\" context",
  "statusMessage": "Loading skills..."
}
```

Skills with `load_at_startup: true` in `skill-list.md` will have their full `SKILL.md` injected into each session's context.

## Slash command

Once installed, `/manage-skills` is available in Claude Code. See `SKILL.md` for full details.
