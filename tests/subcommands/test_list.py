import argparse
import json
from unittest.mock import patch

from lib import write_skill_list
from subcommands.list import (
    _list_skills_table,
    _list_skills_json,
    _list_startup_table,
    _startup_payload,
    run,
)


def make_args(**kwargs):
    defaults = {'json': False, 'for_claude_startup': False}
    return argparse.Namespace(**{**defaults, **kwargs})


# -- list (table, all skills) --

def test_list_skills_empty(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    with patch('lib.get_skill_list_path', return_value=str(p)):
        _list_skills_table()
    assert 'No skills found.' in capsys.readouterr().out


def test_list_skills_prints_table(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    skills = [{'name': 'mything', 'url': 'https://x.com/y', 'local_path': '/tmp/y', 'load_at_startup': True, 'version': 'abc1234'}]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        _list_skills_table()
    out = capsys.readouterr().out
    assert 'mything' in out
    assert 'git_sha1' in out


# -- list --json (JSON, all skills) --

def test_list_skills_json_empty(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    with patch('lib.get_skill_list_path', return_value=str(p)):
        _list_skills_json()
    assert json.loads(capsys.readouterr().out) == []


def test_list_skills_json_includes_metadata(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    skills = [{'name': 'mything', 'url': 'https://x.com/y', 'local_path': '/tmp/y', 'load_at_startup': True, 'version': 'abc1234'}]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        _list_skills_json()
    result = json.loads(capsys.readouterr().out)
    assert result[0]['name'] == 'mything'
    assert result[0]['version'] == 'abc1234'
    assert 'dependencies' in result[0]


# -- list --for-claude-startup (table, startup skills only) --

def test_list_startup_table_empty(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    skills = [{'name': 'a', 'url': 'u', 'local_path': '/tmp/a', 'load_at_startup': False, 'version': ''}]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        _list_startup_table()
    assert 'No skills marked load_at_startup' in capsys.readouterr().out


def test_list_startup_table_filters_correctly(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    skills = [
        {'name': 'included', 'url': 'u1', 'local_path': '/tmp/a', 'load_at_startup': True, 'version': ''},
        {'name': 'excluded', 'url': 'u2', 'local_path': '/tmp/b', 'load_at_startup': False, 'version': ''},
    ]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        _list_startup_table()
    out = capsys.readouterr().out
    assert 'included' in out
    assert 'excluded' not in out


# -- list --json --for-claude-startup (SessionStart payload) --

def test_startup_payload_includes_startup_skills_only(tmp_path, capsys):
    skill1_dir = tmp_path / 'skill1'
    skill1_dir.mkdir()
    (skill1_dir / 'SKILL.md').write_text('Skill one content')

    skill2_dir = tmp_path / 'skill2'
    skill2_dir.mkdir()
    (skill2_dir / 'SKILL.md').write_text('Skill two content')

    p = tmp_path / 'skills.md'
    skills = [
        {'name': 'skill1', 'url': 'u1', 'local_path': str(skill1_dir), 'load_at_startup': True, 'version': ''},
        {'name': 'skill2', 'url': 'u2', 'local_path': str(skill2_dir), 'load_at_startup': False, 'version': ''},
    ]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        _startup_payload()

    ctx = json.loads(capsys.readouterr().out)['hookSpecificOutput']['additionalContext']
    assert 'Skill one content' in ctx
    assert 'Skill two content' not in ctx


def test_startup_payload_joins_multiple_with_separator(tmp_path, capsys):
    for name in ('s1', 's2'):
        d = tmp_path / name
        d.mkdir()
        (d / 'SKILL.md').write_text(f'Content {name}')

    p = tmp_path / 'skills.md'
    skills = [
        {'name': 's1', 'url': 'u1', 'local_path': str(tmp_path / 's1'), 'load_at_startup': True, 'version': ''},
        {'name': 's2', 'url': 'u2', 'local_path': str(tmp_path / 's2'), 'load_at_startup': True, 'version': ''},
    ]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        _startup_payload()

    ctx = json.loads(capsys.readouterr().out)['hookSpecificOutput']['additionalContext']
    assert '\n\n---\n\n' in ctx


def test_startup_payload_missing_skill_md_warns_stderr_and_skips(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    skills = [
        {'name': 'ghost', 'url': 'u', 'local_path': str(tmp_path / 'ghost'), 'load_at_startup': True, 'version': ''},
    ]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        _startup_payload()

    captured = capsys.readouterr()
    assert 'ghost' in captured.err
    assert json.loads(captured.out)['hookSpecificOutput']['additionalContext'] == ''


def test_startup_payload_valid_json_structure(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list([])
        _startup_payload()

    data = json.loads(capsys.readouterr().out)
    assert data['hookSpecificOutput']['hookEventName'] == 'SessionStart'
    assert 'additionalContext' in data['hookSpecificOutput']


# -- run() dispatch --

def test_run_dispatches_to_table_by_default(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list([])
        run(make_args())
    assert 'No skills found.' in capsys.readouterr().out


def test_run_dispatches_json_flag(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list([])
        run(make_args(json=True))
    assert json.loads(capsys.readouterr().out) == []


def test_run_dispatches_for_claude_startup_flag(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list([])
        run(make_args(for_claude_startup=True))
    assert 'No skills marked load_at_startup' in capsys.readouterr().out


def test_run_dispatches_both_flags_to_startup_payload(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list([])
        run(make_args(json=True, for_claude_startup=True))
    data = json.loads(capsys.readouterr().out)
    assert data['hookSpecificOutput']['hookEventName'] == 'SessionStart'
