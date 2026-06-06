#!/usr/bin/env python3

import json
import os
import sys
import subprocess
import argparse


def get_skills_home():
    return os.environ.get('SKILLS_HOME', os.path.expanduser('~/.agents/skills'))


def get_skill_list_path():
    return os.path.join(get_skills_home(), 'skill-list.md')


def read_skill_list():
    skill_list_path = get_skill_list_path()
    if not os.path.exists(skill_list_path):
        return []

    with open(skill_list_path, 'r') as f:
        lines = f.readlines()

    table_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith('| name |'):
            table_start = i
            break

    if table_start is None:
        return []

    skills = []
    for line in lines[table_start + 2:]:  # skip header and separator
        if not line.strip() or line.strip().startswith('|---'):
            continue
        parts = [p.strip() for p in line.split('|') if p.strip()]
        if len(parts) < 3:
            continue
        skills.append({
            'name': parts[0],
            'url': parts[1],
            'local_path': parts[2],
            'load_at_startup': parts[3].lower() == 'true' if len(parts) > 3 else False
        })

    return skills


def write_skill_list(skills):
    skill_list_path = get_skill_list_path()
    with open(skill_list_path, 'w') as f:
        f.write('| name | url | local_path | load_at_startup |\n')
        f.write('|------|-----|------------|-----------------|\n')
        for skill in skills:
            load_at_startup = 'true' if skill.get('load_at_startup', False) else 'false'
            f.write(f"| {skill['name']} | {skill['url']} | {skill['local_path']} | {load_at_startup} |\n")


def build_dependency_graph(skills):
    graph = {}
    for skill in skills:
        graph[skill['name']] = read_skill_dependencies(skill['local_path'])
    return graph


def find_cycle(graph):
    """Return a list of skill names forming a cycle (e.g. ['a', 'b', 'a']), or None if clean."""
    colours = {}

    def dfs(node, path):
        colours[node] = 'grey'
        for neighbour in graph.get(node, []):
            if colours.get(neighbour) == 'grey':
                idx = path.index(neighbour)
                return path[idx:] + [neighbour]
            if neighbour not in colours:
                result = dfs(neighbour, path + [neighbour])
                if result is not None:
                    return result
        colours[node] = 'black'
        return None

    for node in graph:
        if node not in colours:
            result = dfs(node, [node])
            if result is not None:
                return result

    return None


def install_skill(url, name=None, local_path=None, load_at_startup=False, skip_clone=False):
    if not name:
        name = url.split('/')[-1].replace('.git', '')

    if not local_path:
        user = url.split('/')[-2] if len(url.split('/')) >= 2 else 'unknown'
        local_path = os.path.expanduser(f'~/code/github/{user}/{name}')

    if skip_clone:
        if not os.path.isdir(local_path):
            print(f"Error: --skip-clone specified but '{local_path}' does not exist.")
            sys.exit(1)
    else:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        subprocess.run(['git', 'clone', url, local_path], check=True)

    dependencies = read_skill_dependencies(local_path)
    if dependencies:
        graph = build_dependency_graph(read_skill_list())
        graph[name] = dependencies
        cycle = find_cycle(graph)
        if cycle:
            print(f"Error: installing '{name}' would create a dependency cycle: {' → '.join(cycle)}")
            sys.exit(1)

    skills_home = get_skills_home()
    symlink_path = os.path.join(skills_home, name)
    os.makedirs(skills_home, exist_ok=True)
    os.symlink(local_path, symlink_path)

    skills = read_skill_list()
    skills.append({
        'name': name,
        'url': url,
        'local_path': local_path,
        'load_at_startup': load_at_startup
    })
    write_skill_list(skills)

    print(f"Installed skill '{name}' from {url}")
    print(f"Local path: {local_path}")
    print(f"Symlink: {symlink_path}")
    print(f"Load at startup: {load_at_startup}")

    if dependencies:
        installed_names = {s['name'] for s in read_skill_list()}
        missing = [d for d in dependencies if d not in installed_names]
        for dep in missing:
            print(f"Warning: dependency '{dep}' is not installed. Run: manage_skills.py install <url> --name {dep}")


def sync_skill(name=None):
    skills = read_skill_list()

    if not skills:
        print("No skills found.")
        return

    if name:
        skill = next((s for s in skills if s['name'] == name), None)
        if not skill:
            print(f"Skill '{name}' not found.")
            return
        skill_list = [skill]
    else:
        skill_list = skills

    for skill in skill_list:
        print(f"Syncing {skill['name']}...")
        try:
            result = subprocess.run(
                ['git', '-C', skill['local_path'], 'pull'],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"  Success: {result.stdout.strip()}")
        except subprocess.CalledProcessError as e:
            print(f"  Error: {e.stderr.strip()}")


def list_skills():
    skills = read_skill_list()

    if not skills:
        print("No skills found.")
        return

    print("| name | url | local_path | load_at_startup | dependencies |")
    print("|------|-----|------------|-----------------|--------------|")
    for skill in skills:
        load_at_startup = 'true' if skill.get('load_at_startup', False) else 'false'
        dependencies = read_skill_dependencies(skill['local_path'])
        deps_display = ', '.join(dependencies) if dependencies else '—'
        print(f"| {skill['name']} | {skill['url']} | {skill['local_path']} | {load_at_startup} | {deps_display} |")


def read_skill_dependencies(local_path):
    skill_md = os.path.join(local_path, 'SKILL.md')
    if not os.path.exists(skill_md):
        return []

    with open(skill_md, 'r') as f:
        lines = f.readlines()

    if not lines or lines[0].strip() != '---':
        return []

    frontmatter_end = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            frontmatter_end = i
            break

    if frontmatter_end == -1:
        return []

    dependencies = []
    in_depends_on = False
    for line in lines[1:frontmatter_end]:
        stripped = line.strip()
        if stripped.startswith('depends_on:'):
            in_depends_on = True
            continue
        if in_depends_on:
            if stripped.startswith('- '):
                dependencies.append(stripped[2:].strip())
            elif stripped and not stripped.startswith('#'):
                in_depends_on = False

    return dependencies


def check_dependencies():
    skills = read_skill_list()
    if not skills:
        print("No skills installed.")
        return

    graph = build_dependency_graph(skills)
    cycle = find_cycle(graph)
    if cycle:
        print(f"Dependency cycle detected: {' → '.join(cycle)}")
        sys.exit(1)
    else:
        print("No dependency cycles found.")


def context_output():
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


def main():
    parser = argparse.ArgumentParser(
        prog='manage_skills',
        description='Install, sync, list, and load skills from git URLs into SKILLS_HOME.'
    )
    parser.add_argument('subcommand', nargs='?', help='Subcommand to run')
    parser.add_argument('--name', help='Name of the skill')
    parser.add_argument('--path', help='Local path to clone the skill to')
    parser.add_argument('--load-at-startup', action='store_true', default=False,
                        help='Load this skill at Claude Code session start')
    parser.add_argument('--skip-clone', action='store_true', default=False,
                        help='Register an already-cloned local repo without git cloning')
    parser.add_argument('url', nargs='?', help='URL of the skill repository')

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        return

    if args.subcommand == 'install':
        if not args.url:
            print("Error: URL is required for install command.")
            sys.exit(1)
        install_skill(args.url, args.name, args.path, args.load_at_startup, args.skip_clone)

    elif args.subcommand == 'sync':
        sync_skill(args.url or args.name)

    elif args.subcommand == 'list':
        list_skills()

    elif args.subcommand == 'context':
        context_output()

    elif args.subcommand == 'check':
        check_dependencies()

    else:
        print(f"Unknown subcommand: {args.subcommand}")
        sys.exit(1)


if __name__ == '__main__':
    main()
