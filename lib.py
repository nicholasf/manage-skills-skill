import json
import os
import subprocess
import sys


def get_skills_home():
    return os.environ.get('SKILLS_HOME', os.path.expanduser('~/.agents/skills'))


def get_global_skills_path():
    return os.path.join(get_skills_home(), 'skills.md')


def get_skill_list_path():
    local = os.path.join(os.getcwd(), 'skills.md')
    if os.path.exists(local):
        return local
    return get_global_skills_path()


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
    for line in lines[table_start + 2:]:
        if not line.strip() or line.strip().startswith('|---'):
            continue
        parts = [p.strip() for p in line.split('|') if p.strip()]
        if len(parts) < 3:
            continue
        skills.append({
            'name': parts[0],
            'url': parts[1],
            'local_path': parts[2],
            'load_at_startup': parts[3].lower() == 'true' if len(parts) > 3 else False,
            'version': parts[4] if len(parts) > 4 else '',
        })

    return skills


def write_skill_list(skills):
    skill_list_path = get_skill_list_path()
    with open(skill_list_path, 'w') as f:
        f.write('| name | url | local_path | load_at_startup | git_sha1 |\n')
        f.write('|------|-----|------------|-----------------|----------|\n')
        for skill in skills:
            load_at_startup = 'true' if skill.get('load_at_startup', False) else 'false'
            version = skill.get('version', '')
            f.write(f"| {skill['name']} | {skill['url']} | {skill['local_path']} | {load_at_startup} | {version} |\n")


def _read_skill_frontmatter(local_path):
    skill_md = os.path.join(local_path, 'SKILL.md')
    if not os.path.exists(skill_md):
        return None, []

    with open(skill_md, 'r') as f:
        lines = f.readlines()

    if not lines or lines[0].strip() != '---':
        return None, []

    frontmatter_end = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            frontmatter_end = i
            break

    if frontmatter_end == -1:
        return None, []

    name = None
    dependencies = []
    in_depends_on = False
    for line in lines[1:frontmatter_end]:
        stripped = line.strip()
        if stripped.startswith('name:'):
            name = stripped[len('name:'):].strip()
            in_depends_on = False
        elif stripped.startswith('depends_on:'):
            in_depends_on = True
        elif in_depends_on:
            if stripped.startswith('- '):
                dependencies.append(stripped[2:].strip())
            elif stripped and not stripped.startswith('#'):
                in_depends_on = False

    return name, dependencies


def read_skill_name(local_path):
    name, _ = _read_skill_frontmatter(local_path)
    return name


def read_skill_dependencies(local_path):
    _, dependencies = _read_skill_frontmatter(local_path)
    return dependencies


def build_dependency_graph(skills):
    graph = {}
    for skill in skills:
        graph[skill['name']] = read_skill_dependencies(skill['local_path'])
    return graph


def find_cycle(graph):
    """Return a list of skill names forming a cycle, or None if clean."""
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


def resolve_sha1(local_path):
    result = subprocess.run(
        ['git', '-C', local_path, 'rev-parse', 'HEAD'],
        capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _git_remote_url(local_path):
    try:
        result = subprocess.run(
            ['git', '-C', local_path, 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return None


def check_registry_drift(skills):
    """Compare each registered skill against reality on disk.

    Returns a list of {'name': ..., 'issues': [...]} for any skill whose
    local_path, git remote, or symlinks no longer match skills.md — e.g.
    after the underlying repo or directory was renamed.
    """
    skills_home = get_skills_home()
    commands_dir = os.path.expanduser('~/.claude/commands')
    drifted = []

    for skill in skills:
        issues = []
        local_path = skill['local_path']

        if not os.path.isdir(local_path):
            issues.append(f"local_path does not exist: {local_path}")
            drifted.append({'name': skill['name'], 'issues': issues})
            continue

        actual_url = _git_remote_url(local_path)
        if actual_url and actual_url != skill['url']:
            issues.append(f"registered url ({skill['url']}) does not match git remote ({actual_url})")

        symlink_path = os.path.join(skills_home, skill['name'])
        if not os.path.islink(symlink_path):
            issues.append(f"missing symlink: {symlink_path}")
        elif os.path.realpath(symlink_path) != os.path.realpath(local_path):
            issues.append(f"symlink {symlink_path} points elsewhere")

        command_md = os.path.join(local_path, 'command.md')
        if os.path.exists(command_md):
            command_name = read_skill_name(local_path) or skill['name']
            command_symlink = os.path.join(commands_dir, f'{command_name}.md')
            if not os.path.islink(command_symlink):
                issues.append(f"missing command symlink: {command_symlink}")
            elif os.path.realpath(command_symlink) != os.path.realpath(command_md):
                issues.append(f"command symlink {command_symlink} points elsewhere")

        if issues:
            drifted.append({'name': skill['name'], 'issues': issues})

    return drifted


def format_drift_report(drifted):
    """Human-readable multi-line drift report, or '' if drifted is empty."""
    if not drifted:
        return ''
    lines = ['Skill registry drift detected:']
    for entry in drifted:
        lines.append(f"- {entry['name']}:")
        for issue in entry['issues']:
            lines.append(f"    {issue}")
    return '\n'.join(lines)


def wire_command(name, local_path):
    command_md = os.path.join(local_path, 'command.md')
    if not os.path.exists(command_md):
        return
    skill_name = read_skill_name(local_path)
    command_name = skill_name if skill_name else name
    commands_dir = os.path.expanduser('~/.claude/commands')
    os.makedirs(commands_dir, exist_ok=True)
    # Remove stale symlink under either the old or new name
    for candidate in set([name, command_name]):
        stale = os.path.join(commands_dir, f'{candidate}.md')
        if os.path.lexists(stale):
            os.remove(stale)
    symlink_path = os.path.join(commands_dir, f'{command_name}.md')
    os.symlink(command_md, symlink_path)
    print(f'Command: {symlink_path} → {command_md}')


def wire_skills_dir(name, local_path):
    """Create .skills/<name> symlink when in per-project mode."""
    if not os.path.exists(os.path.join(os.getcwd(), 'skills.md')):
        return
    skills_dir = os.path.join(os.getcwd(), '.skills')
    os.makedirs(skills_dir, exist_ok=True)
    symlink_path = os.path.join(skills_dir, name)
    if os.path.lexists(symlink_path):
        os.remove(symlink_path)
    os.symlink(local_path, symlink_path)
    print(f'Skills dir: {symlink_path} → {local_path}')


def is_project_mode():
    return os.path.exists(os.path.join(os.getcwd(), 'skills.md'))


def env_path():
    if is_project_mode():
        return os.path.join(os.getcwd(), '.env')
    return os.path.join(get_skills_home(), '.env')


def read_env():
    path = env_path()
    if not os.path.exists(path):
        return {}
    entries = {}
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, _, value = line.partition('=')
                entries[key.strip()] = value.strip()
    return entries


def write_env(entries):
    path = env_path()
    with open(path, 'w') as f:
        for key, value in sorted(entries.items()):
            f.write(f'{key}={value}\n')
