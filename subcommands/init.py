import os


def run(args):
    _init_project()


def _init_project():
    local_skills = os.path.join(os.getcwd(), 'skills.md')
    if os.path.exists(local_skills):
        print("skills.md already exists.")
        return
    with open(local_skills, 'w') as f:
        f.write('| name | url | local_path | load_at_startup | version |\n')
        f.write('|------|-----|------------|-----------------|--------|\n')
    skills_dir = os.path.join(os.getcwd(), '.skills')
    os.makedirs(skills_dir, exist_ok=True)
    print(f"Initialized skills.md and .skills/ in {os.getcwd()}")
