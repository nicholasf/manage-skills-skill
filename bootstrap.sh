#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_HOME="${SKILLS_HOME:-$HOME/.agents/skills}"

mkdir -p "$SKILLS_HOME"

if [ ! -f "$SKILLS_HOME/skill-list.md" ]; then
    printf '| name | url | local_path | load_at_startup |\n' > "$SKILLS_HOME/skill-list.md"
    printf '|------|-----|------------|-----------------|\n' >> "$SKILLS_HOME/skill-list.md"
fi

SYMLINK_PATH="$SKILLS_HOME/manage-skills-skill"
if [ -L "$SYMLINK_PATH" ] || [ -d "$SYMLINK_PATH" ]; then
    echo "Removing existing symlink or directory: $SYMLINK_PATH"
    rm -rf "$SYMLINK_PATH"
fi
ln -s "$SCRIPT_DIR" "$SYMLINK_PATH"

if ! grep -q "manage-skills-skill" "$SKILLS_HOME/skill-list.md"; then
    printf '| manage-skills-skill | https://github.com/nicholasf/manage-skills-skill | %s | true |\n' \
        "$SCRIPT_DIR" >> "$SKILLS_HOME/skill-list.md"
fi

echo "Bootstrap complete!"
echo "SKILLS_HOME: $SKILLS_HOME"
echo "Symlink created: $SYMLINK_PATH"
echo "Skill list: $SKILLS_HOME/skill-list.md"
