import subprocess
from unittest.mock import Mock, call, patch

import pytest

from lib import read_skill_list, write_skill_list
from subcommands.sync import _sync_skill as sync_skill


def test_sync_skill_all(tmp_path):
    p = tmp_path / 'skills.md'
    skills = [
        {'name': 'a', 'url': 'u1', 'local_path': '/tmp/a', 'load_at_startup': False, 'version': ''},
        {'name': 'b', 'url': 'u2', 'local_path': '/tmp/b', 'load_at_startup': False, 'version': ''},
    ]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)

    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(stdout='Already up to date.', stderr='')
        sync_skill()

    assert mock_run.call_count == 4
    mock_run.assert_any_call(['git', '-C', '/tmp/a', 'pull'], capture_output=True, text=True, check=True)
    mock_run.assert_any_call(['git', '-C', '/tmp/b', 'pull'], capture_output=True, text=True, check=True)
    mock_run.assert_any_call(['git', '-C', '/tmp/a', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True)
    mock_run.assert_any_call(['git', '-C', '/tmp/b', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True)


def test_sync_skill_named(tmp_path):
    p = tmp_path / 'skills.md'
    skills = [
        {'name': 'a', 'url': 'u1', 'local_path': '/tmp/a', 'load_at_startup': False, 'version': ''},
        {'name': 'b', 'url': 'u2', 'local_path': '/tmp/b', 'load_at_startup': False, 'version': ''},
    ]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)

    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(stdout='Already up to date.', stderr='')
        sync_skill('a')

    assert mock_run.call_count == 2
    mock_run.assert_any_call(['git', '-C', '/tmp/a', 'pull'], capture_output=True, text=True, check=True)
    mock_run.assert_any_call(['git', '-C', '/tmp/a', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True)


def test_sync_skill_pinned_rechecks_out(tmp_path):
    p = tmp_path / 'skills.md'
    sha = 'b' * 40
    skills = [{'name': 'a', 'url': 'u', 'local_path': '/tmp/a', 'load_at_startup': False, 'version': sha}]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)

    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(stdout='', stderr='')
        sync_skill('a')

    calls = mock_run.call_args_list
    assert call(['git', '-C', '/tmp/a', 'fetch', 'origin'], check=True, capture_output=True) in calls
    assert call(['git', '-C', '/tmp/a', 'checkout', sha], check=True, capture_output=True) in calls
    assert call(['git', '-C', '/tmp/a', 'pull'], capture_output=True, text=True, check=True) not in calls


def test_sync_skill_with_version_arg_repins(tmp_path):
    p = tmp_path / 'skills.md'
    old_sha = 'a' * 40
    new_sha = 'c' * 40
    skills = [{'name': 'a', 'url': 'u', 'local_path': '/tmp/a', 'load_at_startup': False, 'version': old_sha}]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)

    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(stdout=new_sha + '\n', stderr='')
        sync_skill('a', version='v2.0')

    with patch('lib.get_skill_list_path', return_value=str(p)):
        result = read_skill_list()
    assert result[0]['version'] == new_sha


def test_sync_skill_version_requires_name(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list([])
        with pytest.raises(SystemExit):
            sync_skill(version='v1.0')
    assert 'requires a skill name' in capsys.readouterr().out


def test_sync_skill_unknown_name_prints_not_found(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    skills = [{'name': 'a', 'url': 'u', 'local_path': '/tmp/a', 'load_at_startup': False, 'version': ''}]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)

    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run') as mock_run:
        sync_skill('unknown')

    mock_run.assert_not_called()
    captured = capsys.readouterr()
    assert 'unknown' in captured.out
    assert 'not found' in captured.out


def test_sync_skill_error_does_not_raise(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    skills = [{'name': 'a', 'url': 'u', 'local_path': '/tmp/a', 'load_at_startup': False, 'version': ''}]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)

    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'git', stderr='fetch failed')):
        sync_skill('a')  # must not raise

    assert 'Error' in capsys.readouterr().out


def test_sync_rewires_command_and_skills_dir_for_every_skill(tmp_path):
    p = tmp_path / 'skills.md'
    skills = [
        {'name': 'a', 'url': 'u1', 'local_path': '/tmp/a', 'load_at_startup': False, 'version': ''},
        {'name': 'b', 'url': 'u2', 'local_path': '/tmp/b', 'load_at_startup': False, 'version': ''},
    ]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)

    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run') as mock_run, \
         patch('subcommands.sync.wire_command') as mock_wire_command, \
         patch('subcommands.sync.wire_skills_dir') as mock_wire_skills_dir:
        mock_run.return_value = Mock(stdout='Already up to date.', stderr='')
        sync_skill()

    assert mock_wire_command.call_args_list == [call('a', '/tmp/a'), call('b', '/tmp/b')]
    assert mock_wire_skills_dir.call_args_list == [call('a', '/tmp/a'), call('b', '/tmp/b')]


def test_sync_rewires_command_even_when_git_fails(tmp_path):
    p = tmp_path / 'skills.md'
    skills = [{'name': 'a', 'url': 'u', 'local_path': '/tmp/a', 'load_at_startup': False, 'version': ''}]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)

    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'git', stderr='fetch failed')), \
         patch('subcommands.sync.wire_command') as mock_wire_command, \
         patch('subcommands.sync.wire_skills_dir') as mock_wire_skills_dir:
        sync_skill('a')

    mock_wire_command.assert_called_once_with('a', '/tmp/a')
    mock_wire_skills_dir.assert_called_once_with('a', '/tmp/a')
