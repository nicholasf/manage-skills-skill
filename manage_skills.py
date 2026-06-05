#!/usr/bin/env python3

import os
import sys
import subprocess
import argparse
from pathlib import Path

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

    # Skip header and separator rows
    data_lines = lines[2:]

    skills = []
    for line in data_lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split('|')
        if len(parts) >= 4:
            skills.append({
                'name': parts[1].strip(),
                'url': parts[2].strip(),
                'local_path': parts[3].strip()
            })

    return skills

def write_skill_list(skills):
    skill_list_path = get_skill_list_path()
    header = "| name | url | local_path |\n"
    separator = "|------|-----|------------|\n"

    with open(skill_list_path, 'w') as f:
        f.write(header)
        f.write(separator)
        for skill in skills:
            f.write(f"| {skill['name']} | {skill['url']} | {skill['local_path']} |\n")

def install_skill(url, name=None, local_path=None):
    if not name:
        name = url.split('/')[-1].replace('.git', '')

    if not local_path:
        user = url.split('/')[-2] if len(url.split('/')) >= 2 else 'unknown'
        local_path = os.path.expanduser(f'~/code/github/{user}/{name}')

    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    subprocess.run(['git', 'clone', url, local_path], check=True)

    skills_home = get_skills_home()
    symlink_path = os.path.join(skills_home, name)
    os.makedirs(skills_home, exist_ok=True)
    os.symlink(local_path, symlink_path)

    skills = read_skill_list()
    skills.append({
        'name': name,
        'url': url,
        'local_path': local_path
    })
    write_skill_list(skills)

    print(f"Installed skill '{name}' from {url}")
    print(f"Local path: {local_path}")
    print(f"Symlink: {symlink_path}")

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

    print("| name | url | local_path |")
    print("|------|-----|------------|")
    for skill in skills:
        print(f"| {skill['name']} | {skill['url']} | {skill['local_path']} |")

def main():
    parser = argparse.ArgumentParser(
        prog='manage_skills',
        description='Install, sync, and list skills from git URLs into SKILLS_HOME.'
    )
    parser.add_argument('subcommand', nargs='?', help='Subcommand to run')
    parser.add_argument('--name', help='Name of the skill')
    parser.add_argument('--path', help='Local path to clone the skill to')
    parser.add_argument('url', nargs='?', help='URL of the skill repository')

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        return

    if args.subcommand == 'install':
        if not args.url:
            print("Error: URL is required for install command.")
            sys.exit(1)
        install_skill(args.url, args.name, args.path)

    elif args.subcommand == 'sync':
        # args.url catches a bare positional name e.g. `sync my-skill`
        sync_skill(args.url or args.name)

    elif args.subcommand == 'list':
        list_skills()

    else:
        print(f"Unknown subcommand: {args.subcommand}")
        sys.exit(1)

if __name__ == '__main__':
    main()
