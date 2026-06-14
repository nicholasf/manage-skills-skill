import sys

from lib import env_path, read_env, read_skill_list, write_env


def run(args):
    action = args.url  # env's first positional is parsed into the url slot
    if action == 'set':
        if not args.extra:
            print("Error: env set requires KEY=value")
            sys.exit(1)
        _env_set(args.extra)
    elif action == 'list':
        _env_list()
    elif action == 'init':
        _env_init()
    else:
        print("Usage: manage_skills env <set KEY=value | list | init>")
        sys.exit(1)


def _env_set(key_value):
    if '=' not in key_value:
        print("Error: expected KEY=value")
        sys.exit(1)
    key, _, value = key_value.partition('=')
    key = key.strip()
    if not key:
        print("Error: key must not be empty")
        sys.exit(1)
    entries = read_env()
    entries[key] = value
    write_env(entries)
    print(f"Set {key}")


def _env_list():
    entries = read_env()
    if not entries:
        print("No entries in .env")
        return
    print(f"# {env_path()}")
    for key in sorted(entries):
        print(key)


def _env_init():
    skills = read_skill_list()
    if not skills:
        print("No skills installed.")
        return

    import os
    existing = read_env()
    added = []
    for skill in skills:
        example = os.path.join(skill['local_path'], '.env.example')
        if not os.path.exists(example):
            continue
        with open(example, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, _, value = line.partition('=')
                    key = key.strip()
                    if key and key not in existing:
                        existing[key] = value.strip()
                        added.append(key)

    if not added:
        print("Nothing new to add.")
        return

    write_env(existing)
    for key in added:
        print(f"Added {key}")
