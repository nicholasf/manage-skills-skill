import json
import os
import sys

from lib import check_registry_drift, format_drift_report, read_skill_dependencies, read_skill_list


def run(args):
    if args.json and args.for_claude_startup:
        _startup_payload()
    elif args.for_claude_startup:
        _list_startup_table()
    elif args.json:
        _list_skills_json()
    else:
        _list_skills_table()


def _list_skills_table():
    skills = read_skill_list()
    if not skills:
        print("No skills found.")
        return
    print("| name | url | local_path | load_at_startup | git_sha1 | dependencies |")
    print("|------|-----|------------|-----------------|----------|--------------|")
    for skill in skills:
        load_at_startup = 'true' if skill.get('load_at_startup', False) else 'false'
        dependencies = read_skill_dependencies(skill['local_path'])
        deps_display = ', '.join(dependencies) if dependencies else '—'
        version = skill.get('version', '') or '—'
        print(f"| {skill['name']} | {skill['url']} | {skill['local_path']} | {load_at_startup} | {version} | {deps_display} |")


def _list_startup_table():
    skills = [s for s in read_skill_list() if s.get('load_at_startup', False)]
    if not skills:
        print("No skills marked load_at_startup.")
        return
    print("| name | url | local_path | git_sha1 | dependencies |")
    print("|------|-----|------------|----------|--------------|")
    for skill in skills:
        dependencies = read_skill_dependencies(skill['local_path'])
        deps_display = ', '.join(dependencies) if dependencies else '—'
        version = skill.get('version', '') or '—'
        print(f"| {skill['name']} | {skill['url']} | {skill['local_path']} | {version} | {deps_display} |")


def _list_skills_json():
    skills = read_skill_list()
    output = [
        {**skill, 'dependencies': read_skill_dependencies(skill['local_path'])}
        for skill in skills
    ]
    print(json.dumps(output, indent=2))


def _startup_payload():
    all_skills = read_skill_list()
    skills = [s for s in all_skills if s.get('load_at_startup', False)]
    context_parts = []
    for skill in skills:
        skill_md_path = os.path.join(skill['local_path'], 'SKILL.md')
        if not os.path.exists(skill_md_path):
            print(f"Warning: SKILL.md not found for skill '{skill['name']}'", file=sys.stderr)
            continue
        with open(skill_md_path, 'r') as f:
            context_parts.append(f.read().strip())

    drifted = check_registry_drift(all_skills)
    for entry in drifted:
        for issue in entry['issues']:
            print(f"Warning: drift in skill '{entry['name']}': {issue}", file=sys.stderr)

    context_body = '\n\n---\n\n'.join(context_parts)
    drift_report = format_drift_report(drifted)
    if drift_report:
        context_body = f"{drift_report}\n\n---\n\n{context_body}" if context_body else drift_report

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context_body
        }
    }))
