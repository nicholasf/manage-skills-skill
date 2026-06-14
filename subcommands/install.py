import os
import subprocess
import sys

from lib import (
    build_dependency_graph, find_cycle, get_skills_home, read_skill_dependencies,
    read_skill_list, resolve_sha1, wire_command, wire_skills_dir, write_skill_list,
)


def run(args):
    if not args.url:
        print("Error: URL is required for install command.")
        sys.exit(1)
    _install_skill(args.url, args.name, args.path, args.load_at_startup, args.skip_clone, args.version)


def _install_skill(url, name=None, local_path=None, load_at_startup=False, skip_clone=False, version=None):
    if not name:
        name = url.split('/')[-1].replace('.git', '')

    if not local_path:
        user = url.split('/')[-2] if len(url.split('/')) >= 2 else 'unknown'
        local_path = os.path.expanduser(f'~/code/github/{user}/{name}')

    if skip_clone:
        if not os.path.isdir(local_path):
            print(f"Error: --skip-clone specified but '{local_path}' does not exist.")
            sys.exit(1)
    elif os.path.isdir(local_path):
        print(f"Already cloned at {local_path}, skipping clone.")
    else:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        subprocess.run(['git', 'clone', url, local_path], check=True)

    if version:
        subprocess.run(['git', '-C', local_path, 'fetch', 'origin'], check=True, capture_output=True)
        subprocess.run(['git', '-C', local_path, 'checkout', version], check=True, capture_output=True)
        version = resolve_sha1(local_path)

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
    if os.path.lexists(symlink_path):
        os.remove(symlink_path)
    os.symlink(local_path, symlink_path)

    wire_skills_dir(name, local_path)

    skills = read_skill_list()
    skills.append({
        'name': name,
        'url': url,
        'local_path': local_path,
        'load_at_startup': load_at_startup,
        'version': version or '',
    })
    write_skill_list(skills)

    wire_command(name, local_path)

    print(f"Installed skill '{name}' from {url}")
    print(f"Local path: {local_path}")
    print(f"Symlink: {symlink_path}")
    print(f"Load at startup: {load_at_startup}")
    if version:
        print(f"Version: {version}")

    if dependencies:
        installed_names = {s['name'] for s in read_skill_list()}
        missing = [d for d in dependencies if d not in installed_names]
        for dep in missing:
            print(f"Warning: dependency '{dep}' is not installed. Run: manage_skills.py install <url> --name {dep}")
