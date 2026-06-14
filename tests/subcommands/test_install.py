import os
from unittest.mock import Mock, call, patch

import pytest

from lib import read_skill_list, write_skill_list
from subcommands.install import _install_skill as install_skill


def test_install_skill_clones_and_symlinks(tmp_path):
    p = tmp_path / 'skills.md'
    skills_home = str(tmp_path / 'skills')

    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('subcommands.install.get_skills_home', return_value=skills_home), \
         patch('os.path.isdir', return_value=False), \
         patch('subprocess.run') as mock_run, \
         patch('os.symlink') as mock_symlink, \
         patch('os.path.lexists', return_value=False), \
         patch('os.makedirs'):

        install_skill('https://github.com/user/myskill', name='myskill', local_path='/tmp/myskill')

        mock_run.assert_called_once_with(
            ['git', 'clone', 'https://github.com/user/myskill', '/tmp/myskill'],
            check=True
        )
        mock_symlink.assert_called_once_with('/tmp/myskill', os.path.join(skills_home, 'myskill'))


def test_install_skill_with_version_checkouts_and_resolves_sha(tmp_path):
    p = tmp_path / 'skills.md'
    skills_home = str(tmp_path / 'skills')
    full_sha = 'a' * 40

    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('subcommands.install.get_skills_home', return_value=skills_home), \
         patch('subprocess.run', side_effect=[Mock(), Mock(), Mock(), Mock(stdout=full_sha + '\n')]) as mock_run, \
         patch('os.symlink'), \
         patch('os.path.lexists', return_value=False), \
         patch('os.makedirs'):

        install_skill('https://github.com/user/myskill', name='myskill', local_path='/tmp/myskill', version='v1.0')

        calls = mock_run.call_args_list
        assert calls[0] == call(['git', 'clone', 'https://github.com/user/myskill', '/tmp/myskill'], check=True)
        assert calls[1] == call(['git', '-C', '/tmp/myskill', 'fetch', 'origin'], check=True, capture_output=True)
        assert calls[2] == call(['git', '-C', '/tmp/myskill', 'checkout', 'v1.0'], check=True, capture_output=True)
        assert calls[3] == call(['git', '-C', '/tmp/myskill', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True)

    with patch('lib.get_skill_list_path', return_value=str(p)):
        result = read_skill_list()
    assert result[0]['version'] == full_sha


def test_install_skill_skips_clone_if_already_on_disk(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    skills_home = str(tmp_path / 'skills')

    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('subcommands.install.get_skills_home', return_value=skills_home), \
         patch('os.path.isdir', return_value=True), \
         patch('subprocess.run') as mock_run, \
         patch('os.symlink'), \
         patch('os.makedirs'):

        install_skill('https://github.com/user/myskill', name='myskill', local_path='/tmp/myskill')

    mock_run.assert_not_called()
    assert 'skipping clone' in capsys.readouterr().out


def test_install_skill_derives_name_from_url(tmp_path):
    p = tmp_path / 'skills.md'
    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('subcommands.install.get_skills_home', return_value=str(tmp_path / 'skills')), \
         patch('subprocess.run'), \
         patch('os.symlink'), \
         patch('os.path.lexists', return_value=False), \
         patch('os.makedirs'):

        install_skill('https://github.com/user/myskill.git', local_path='/tmp/myskill')

    with patch('lib.get_skill_list_path', return_value=str(p)):
        result = read_skill_list()
    assert result[0]['name'] == 'myskill'


def test_install_skill_records_load_at_startup(tmp_path):
    p = tmp_path / 'skills.md'
    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('subcommands.install.get_skills_home', return_value=str(tmp_path / 'skills')), \
         patch('subprocess.run'), \
         patch('os.symlink'), \
         patch('os.path.lexists', return_value=False), \
         patch('os.makedirs'):

        install_skill('https://github.com/user/myskill', name='myskill', local_path='/tmp/myskill', load_at_startup=True)

    with patch('lib.get_skill_list_path', return_value=str(p)):
        result = read_skill_list()
    assert result[0]['load_at_startup'] is True


def test_install_skill_creates_skills_dir_symlink_when_project(tmp_path):
    p = tmp_path / 'skills.md'
    p.write_text('| name | url | local_path | load_at_startup | version |\n|------|-----|------------|-----------------|--------|\n')
    skills_home = str(tmp_path / 'skills_home')

    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('subcommands.install.get_skills_home', return_value=skills_home), \
         patch('os.getcwd', return_value=str(tmp_path)), \
         patch('subprocess.run'), \
         patch('os.symlink') as mock_symlink, \
         patch('os.path.lexists', return_value=False), \
         patch('os.makedirs'):

        install_skill('https://github.com/user/myskill', name='myskill', local_path='/tmp/myskill')

    symlink_targets = [c[0] for c in mock_symlink.call_args_list]
    assert ('/tmp/myskill', os.path.join(str(tmp_path), '.skills', 'myskill')) in symlink_targets


def test_install_skill_aborts_on_cycle(tmp_path):
    b_dir = tmp_path / 'b-skill'
    b_dir.mkdir()
    (b_dir / 'SKILL.md').write_text('---\ndepends_on:\n  - a-skill\n---\n# B\n')

    a_dir = tmp_path / 'a-skill'
    a_dir.mkdir()
    (a_dir / 'SKILL.md').write_text('---\ndepends_on:\n  - b-skill\n---\n# A\n')

    p = tmp_path / 'skills.md'
    skills = [{'name': 'b-skill', 'url': 'u', 'local_path': str(b_dir), 'load_at_startup': False, 'version': ''}]

    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('subcommands.install.get_skills_home', return_value=str(tmp_path / 'skills')):
        write_skill_list(skills)
        with pytest.raises(SystemExit):
            install_skill('https://github.com/u/a-skill', name='a-skill', local_path=str(a_dir), skip_clone=True)
