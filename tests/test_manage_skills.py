import json
import os
import subprocess
from unittest.mock import Mock, patch

import pytest

from manage_skills import (
    context_output,
    install_skill,
    list_skills,
    read_skill_list,
    sync_skill,
    write_skill_list,
)


# -- read_skill_list --

def test_read_skill_list_missing_file(tmp_path):
    with patch('manage_skills.get_skill_list_path', return_value=str(tmp_path / 'nonexistent.md')):
        assert read_skill_list() == []


def test_read_skill_list_empty_file(tmp_path):
    p = tmp_path / 'skill-list.md'
    p.write_text('')
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        assert read_skill_list() == []


def test_read_skill_list_no_table(tmp_path):
    p = tmp_path / 'skill-list.md'
    p.write_text('# Skills\n\nNo table here.\n')
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        assert read_skill_list() == []


def test_read_skill_list_valid_4_column_table(tmp_path):
    p = tmp_path / 'skill-list.md'
    p.write_text(
        '| name | url | local_path | load_at_startup |\n'
        '|------|-----|------------|-----------------|\n'
        '| skill1 | https://github.com/u/skill1 | /path/skill1 | true |\n'
        '| skill2 | https://github.com/u/skill2 | /path/skill2 | false |\n'
    )
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        result = read_skill_list()
    assert result == [
        {'name': 'skill1', 'url': 'https://github.com/u/skill1', 'local_path': '/path/skill1', 'load_at_startup': True},
        {'name': 'skill2', 'url': 'https://github.com/u/skill2', 'local_path': '/path/skill2', 'load_at_startup': False},
    ]


def test_read_skill_list_old_3_column_table_defaults_load_at_startup_false(tmp_path):
    p = tmp_path / 'skill-list.md'
    p.write_text(
        '| name | url | local_path |\n'
        '|------|-----|------------|\n'
        '| skill1 | https://github.com/u/skill1 | /path/skill1 |\n'
    )
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        result = read_skill_list()
    assert result[0]['load_at_startup'] is False


# -- write_skill_list / round-trip --

def test_write_read_round_trip(tmp_path):
    p = tmp_path / 'skill-list.md'
    skills = [
        {'name': 'a', 'url': 'https://example.com/a', 'local_path': '/tmp/a', 'load_at_startup': True},
        {'name': 'b', 'url': 'https://example.com/b', 'local_path': '/tmp/b', 'load_at_startup': False},
    ]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        result = read_skill_list()
    assert result == skills


# -- context_output --

def test_context_output_includes_startup_skills_only(tmp_path, capsys):
    skill1_dir = tmp_path / 'skill1'
    skill1_dir.mkdir()
    (skill1_dir / 'SKILL.md').write_text('Skill one content')

    skill2_dir = tmp_path / 'skill2'
    skill2_dir.mkdir()
    (skill2_dir / 'SKILL.md').write_text('Skill two content')

    p = tmp_path / 'skill-list.md'
    skills = [
        {'name': 'skill1', 'url': 'u1', 'local_path': str(skill1_dir), 'load_at_startup': True},
        {'name': 'skill2', 'url': 'u2', 'local_path': str(skill2_dir), 'load_at_startup': False},
    ]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
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

    p = tmp_path / 'skill-list.md'
    skills = [
        {'name': 's1', 'url': 'u1', 'local_path': str(tmp_path / 's1'), 'load_at_startup': True},
        {'name': 's2', 'url': 'u2', 'local_path': str(tmp_path / 's2'), 'load_at_startup': True},
    ]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        context_output()

    ctx = json.loads(capsys.readouterr().out)['hookSpecificOutput']['additionalContext']
    assert '\n\n---\n\n' in ctx


def test_context_output_missing_skill_md_warns_stderr_and_skips(tmp_path, capsys):
    p = tmp_path / 'skill-list.md'
    skills = [
        {'name': 'ghost', 'url': 'u', 'local_path': str(tmp_path / 'ghost'), 'load_at_startup': True},
    ]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        context_output()

    captured = capsys.readouterr()
    assert 'ghost' in captured.err
    assert json.loads(captured.out)['hookSpecificOutput']['additionalContext'] == ''


def test_context_output_valid_json_structure(tmp_path, capsys):
    p = tmp_path / 'skill-list.md'
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list([])
        context_output()

    data = json.loads(capsys.readouterr().out)
    assert data['hookSpecificOutput']['hookEventName'] == 'SessionStart'
    assert 'additionalContext' in data['hookSpecificOutput']


# -- install_skill --

def test_install_skill_clones_and_symlinks(tmp_path):
    p = tmp_path / 'skill-list.md'
    skills_home = str(tmp_path / 'skills')

    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('manage_skills.get_skills_home', return_value=skills_home), \
         patch('subprocess.run') as mock_run, \
         patch('os.symlink') as mock_symlink, \
         patch('os.makedirs'):

        install_skill('https://github.com/user/myskill', name='myskill', local_path='/tmp/myskill')

        mock_run.assert_called_once_with(
            ['git', 'clone', 'https://github.com/user/myskill', '/tmp/myskill'],
            check=True
        )
        mock_symlink.assert_called_once_with('/tmp/myskill', os.path.join(skills_home, 'myskill'))


def test_install_skill_derives_name_from_url(tmp_path):
    p = tmp_path / 'skill-list.md'
    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('manage_skills.get_skills_home', return_value=str(tmp_path / 'skills')), \
         patch('subprocess.run'), \
         patch('os.symlink'), \
         patch('os.makedirs'):

        install_skill('https://github.com/user/myskill.git', local_path='/tmp/myskill')

    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        result = read_skill_list()
    assert result[0]['name'] == 'myskill'


def test_install_skill_records_load_at_startup(tmp_path):
    p = tmp_path / 'skill-list.md'
    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('manage_skills.get_skills_home', return_value=str(tmp_path / 'skills')), \
         patch('subprocess.run'), \
         patch('os.symlink'), \
         patch('os.makedirs'):

        install_skill('https://github.com/user/myskill', name='myskill', local_path='/tmp/myskill', load_at_startup=True)

    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        result = read_skill_list()
    assert result[0]['load_at_startup'] is True


# -- sync_skill --

def test_sync_skill_all(tmp_path):
    p = tmp_path / 'skill-list.md'
    skills = [
        {'name': 'a', 'url': 'u1', 'local_path': '/tmp/a', 'load_at_startup': False},
        {'name': 'b', 'url': 'u2', 'local_path': '/tmp/b', 'load_at_startup': False},
    ]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)

    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(stdout='Already up to date.', stderr='')
        sync_skill()

    assert mock_run.call_count == 2
    mock_run.assert_any_call(['git', '-C', '/tmp/a', 'pull'], capture_output=True, text=True, check=True)
    mock_run.assert_any_call(['git', '-C', '/tmp/b', 'pull'], capture_output=True, text=True, check=True)


def test_sync_skill_named(tmp_path):
    p = tmp_path / 'skill-list.md'
    skills = [
        {'name': 'a', 'url': 'u1', 'local_path': '/tmp/a', 'load_at_startup': False},
        {'name': 'b', 'url': 'u2', 'local_path': '/tmp/b', 'load_at_startup': False},
    ]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)

    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(stdout='Already up to date.', stderr='')
        sync_skill('a')

    mock_run.assert_called_once_with(['git', '-C', '/tmp/a', 'pull'], capture_output=True, text=True, check=True)


def test_sync_skill_unknown_name_prints_not_found(tmp_path, capsys):
    p = tmp_path / 'skill-list.md'
    skills = [{'name': 'a', 'url': 'u', 'local_path': '/tmp/a', 'load_at_startup': False}]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)

    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run') as mock_run:
        sync_skill('unknown')

    mock_run.assert_not_called()
    captured = capsys.readouterr()
    assert 'unknown' in captured.out
    assert 'not found' in captured.out


def test_sync_skill_error_does_not_raise(tmp_path, capsys):
    p = tmp_path / 'skill-list.md'
    skills = [{'name': 'a', 'url': 'u', 'local_path': '/tmp/a', 'load_at_startup': False}]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)

    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'git', stderr='fetch failed')):
        sync_skill('a')  # must not raise

    assert 'Error' in capsys.readouterr().out


# -- list_skills --

def test_list_skills_empty(tmp_path, capsys):
    p = tmp_path / 'skill-list.md'
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        list_skills()
    assert 'No skills found.' in capsys.readouterr().out


def test_list_skills_prints_table(tmp_path, capsys):
    p = tmp_path / 'skill-list.md'
    skills = [{'name': 'mything', 'url': 'https://x.com/y', 'local_path': '/tmp/y', 'load_at_startup': True}]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        list_skills()
    out = capsys.readouterr().out
    assert 'mything' in out
    assert 'name' in out
