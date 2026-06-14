import subprocess
import sys

from lib import read_skill_list, resolve_sha1, write_skill_list


def run(args):
    _sync_skill(args.url or args.name, args.version)


def _sync_skill(name=None, version=None):
    if version and not name:
        print("Error: --version requires a skill name.")
        sys.exit(1)

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

    changed = False
    for skill in skill_list:
        print(f"Syncing {skill['name']}...")
        try:
            if version:
                subprocess.run(['git', '-C', skill['local_path'], 'fetch', 'origin'], check=True, capture_output=True)
                subprocess.run(['git', '-C', skill['local_path'], 'checkout', version], check=True, capture_output=True)
                resolved = resolve_sha1(skill['local_path'])
                skill['version'] = resolved
                changed = True
                print(f"  Pinned to {resolved[:8]}")
            elif skill.get('version'):
                subprocess.run(['git', '-C', skill['local_path'], 'fetch', 'origin'], check=True, capture_output=True)
                subprocess.run(['git', '-C', skill['local_path'], 'checkout', skill['version']], check=True, capture_output=True)
                print(f"  Pinned to {skill['version'][:8]}, re-checked out.")
            else:
                result = subprocess.run(
                    ['git', '-C', skill['local_path'], 'pull'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                print(f"  {result.stdout.strip()}")
                resolved = resolve_sha1(skill['local_path'])
                skill['version'] = resolved
                changed = True
                print(f"  Resolved to {resolved[:8]}")
        except subprocess.CalledProcessError as e:
            print(f"  Error: {e.stderr.strip() if e.stderr else str(e)}")

    if changed:
        write_skill_list(skills)
