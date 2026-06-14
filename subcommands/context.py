import json
import os
import sys

from lib import read_skill_list


def run(args):
    _context_output()


def _context_output():
    skills = read_skill_list()
    startup_skills = [s for s in skills if s.get('load_at_startup', False)]

    context_parts = []
    for skill in startup_skills:
        skill_md_path = os.path.join(skill['local_path'], 'SKILL.md')
        if not os.path.exists(skill_md_path):
            print(f"Warning: SKILL.md not found for skill '{skill['name']}'", file=sys.stderr)
            continue
        with open(skill_md_path, 'r') as f:
            context_parts.append(f.read().strip())

    additional_context = '\n\n---\n\n'.join(context_parts)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": additional_context
        }
    }))
