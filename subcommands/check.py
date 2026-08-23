import sys

from lib import build_dependency_graph, check_registry_drift, find_cycle, format_drift_report, read_skill_list


def run(args):
    _check_drift()
    _check_dependencies()


def _check_drift():
    skills = read_skill_list()
    if not skills:
        return
    drifted = check_registry_drift(skills)
    if not drifted:
        print("No registry drift found.")
        return
    print(format_drift_report(drifted))


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
