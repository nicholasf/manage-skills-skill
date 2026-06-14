#!/usr/bin/env python3

import argparse
import sys

import subcommands.check as check
import subcommands.env as env
import subcommands.help as help_cmd
import subcommands.init as init_cmd
import subcommands.install as install
import subcommands.list as list_cmd
import subcommands.sync as sync


def main():
    parser = argparse.ArgumentParser(
        prog='manage_skills',
        description='Install, sync, list, and load skills from git URLs into SKILLS_HOME.'
    )
    parser.add_argument('subcommand', nargs='?', help='Subcommand to run')
    parser.add_argument('--name', help='Name of the skill')
    parser.add_argument('--path', help='Local path to clone the skill to')
    parser.add_argument('--load-at-startup', action='store_true', default=False,
                        help='Load this skill at Claude Code session start')
    parser.add_argument('--skip-clone', action='store_true', default=False,
                        help='Register an already-cloned local repo without git cloning')
    parser.add_argument('--version', help='Git SHA1 or tag to pin the skill to')
    parser.add_argument('--json', action='store_true', default=False,
                        help='Output as JSON (list subcommand)')
    parser.add_argument('--for-claude-startup', action='store_true', default=False,
                        help='Filter to load_at_startup skills; with --json emits SessionStart hook payload')
    parser.add_argument('url', nargs='?', help='URL of the skill repository')
    parser.add_argument('extra', nargs='?', help='Extra argument (e.g. KEY=value for env set, sub-action for env)')

    args = parser.parse_args()

    if not args.subcommand:
        help_cmd.run(args)
        return

    dispatch = {
        'install': install.run,   # clone a skill repo and register it in skills.md
        'sync':    sync.run,      # pull latest changes (or re-checkout a pinned ref) for installed skills
        'list':    list_cmd.run,  # table or JSON of skills; --for-claude-startup + --json emits SessionStart payload
        'check':   check.run,     # scan the dependency graph and report any cycles
        'init':    init_cmd.run,  # create a per-project skills.md and .skills/ directory
        'env':     env.run,       # manage .env variables used by skills (set / list / init)
        'help':    help_cmd.run,  # print usage and subcommand descriptions
    }

    handler = dispatch.get(args.subcommand)
    if handler is None:
        print(f"Unknown subcommand: {args.subcommand}")
        sys.exit(1)

    handler(args)


if __name__ == '__main__':
    main()
