import json
from unittest.mock import patch

from lib import write_skill_list
from subcommands.context import _context_output as context_output


def test_context_output_includes_startup_skills_only(tmp_path, capsys):
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
        context_output()

    ctx = json.loads(capsys.readouterr().out)['hookSpecificOutput']['additionalContext']
    assert 'Skill one content' in ctx
    assert 'Skill two content' not in ctx


def test_context_output_joins_multiple_with_separator(tmp_path, capsys):
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
        context_output()

    ctx = json.loads(capsys.readouterr().out)['hookSpecificOutput']['additionalContext']
    assert '\n\n---\n\n' in ctx


def test_context_output_missing_skill_md_warns_stderr_and_skips(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    skills = [
        {'name': 'ghost', 'url': 'u', 'local_path': str(tmp_path / 'ghost'), 'load_at_startup': True, 'version': ''},
    ]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        context_output()

    captured = capsys.readouterr()
    assert 'ghost' in captured.err
    assert json.loads(captured.out)['hookSpecificOutput']['additionalContext'] == ''


def test_context_output_valid_json_structure(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list([])
        context_output()

    data = json.loads(capsys.readouterr().out)
    assert data['hookSpecificOutput']['hookEventName'] == 'SessionStart'
    assert 'additionalContext' in data['hookSpecificOutput']


def test_context_output_uses_local_skills_md_when_present(tmp_path, capsys):
    skill_dir = tmp_path / 'myskill'
    skill_dir.mkdir()
    (skill_dir / 'SKILL.md').write_text('Local skill content')

    local_skills = tmp_path / 'skills.md'
    skills = [{'name': 'myskill', 'url': 'u', 'local_path': str(skill_dir), 'load_at_startup': True, 'version': ''}]
    with patch('lib.get_skill_list_path', return_value=str(local_skills)):
        write_skill_list(skills)
        context_output()

    ctx = json.loads(capsys.readouterr().out)['hookSpecificOutput']['additionalContext']
    assert 'Local skill content' in ctx
