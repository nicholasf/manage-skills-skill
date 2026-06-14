import sys

from lib import build_dependency_graph, find_cycle, read_skill_list


def run(args):
    _check_dependencies()


def _check_dependencies():
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
