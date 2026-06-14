from lib import read_skill_dependencies, read_skill_list


def run(args):
    _list_skills()


def _list_skills():
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
