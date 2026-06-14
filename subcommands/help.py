SUBCOMMANDS = [
    ('install <url>', 'Clone and register a skill from a git URL'),
    ('sync [name]',   'Pull latest changes for all skills, or a named skill'),
    ('list',          'List all installed skills with their metadata'),
    ('check',         'Check installed skills for dependency cycles'),
    ('init',          'Initialise a per-project skills.md in the current directory'),
    ('env set KEY=V', 'Set an environment variable in .env'),
    ('env list',      'List environment variable keys in .env'),
    ('env init',      'Seed .env from each skill\'s .env.example'),
    ('help',          'Show this help message'),
]


def run(args):
    print("manage_skills — install and manage Claude Code skills\n")
    print("Usage: manage_skills.py <subcommand> [options]\n")
    print("Subcommands:")
    width = max(len(name) for name, _ in SUBCOMMANDS)
    for name, description in SUBCOMMANDS:
        print(f"  {name:<{width}}  {description}")
    print()
    print("Options (install / sync):")
    print("  --name NAME            Override the skill name")
    print("  --path PATH            Override the local clone path")
    print("  --load-at-startup      Load SKILL.md content at every session start")
    print("  --skip-clone           Register an already-cloned repo without running git clone")
    print("  --version SHA1|TAG     Pin the skill to a specific git ref")
    print()
    print("Options (list):")
    print("  --json                 Output as JSON instead of a table")
    print("  --for-claude-startup   Filter to skills marked load_at_startup;")
    print("                         combined with --json emits the SessionStart hook payload")
