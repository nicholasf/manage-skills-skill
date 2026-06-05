#!/bin/bash

SKILLS_HOME="${SKILLS_HOME:-$HOME/.agents/skills}"

mkdir -p "$SKILLS_HOME"

SYMLINK_PATH="$SKILLS_HOME/manage-skills-skill"
if [ -L "$SYMLINK_PATH" ] || [ -d "$SYMLINK_PATH" ]; then
    echo "Removing existing symlink or directory: $SYMLINK_PATH"
    rm -rf "$SYMLINK_PATH"
fi
ln -s "$(pwd)" "$SYMLINK_PATH"

SKILL_LIST_PATH="$SKILLS_HOME/skill-list.md"
if [ ! -f "$SKILL_LIST_PATH" ]; then
    echo "| name | url | local_path |" > "$SKILL_LIST_PATH"
    echo "|------|-----|------------|" >> "$SKILL_LIST_PATH"
fi

echo "Bootstrap complete!"
echo "SKILLS_HOME: $SKILLS_HOME"
echo "Symlink created: $SYMLINK_PATH"
echo "Skill list file: $SKILL_LIST_PATH"
