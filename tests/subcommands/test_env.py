from unittest.mock import patch

import pytest

from lib import write_skill_list
from subcommands.env import _env_init as env_init, _env_list as env_list, _env_set as env_set


def test_env_set_creates_file(tmp_path, capsys):
    with patch('lib.get_skills_home', return_value=str(tmp_path)), \
         patch('lib.is_project_mode', return_value=False):
        env_set('POND_HERMES_KEY=abc123')
    env_file = tmp_path / '.env'
    assert env_file.exists()
    assert 'POND_HERMES_KEY=abc123' in env_file.read_text()
    assert 'Set POND_HERMES_KEY' in capsys.readouterr().out


def test_env_set_updates_existing_key(tmp_path):
    env_file = tmp_path / '.env'
    env_file.write_text('POND_HERMES_KEY=old\n')
    with patch('lib.get_skills_home', return_value=str(tmp_path)), \
         patch('lib.is_project_mode', return_value=False):
        env_set('POND_HERMES_KEY=new')
    assert 'POND_HERMES_KEY=new' in env_file.read_text()
    assert 'POND_HERMES_KEY=old' not in env_file.read_text()


def test_env_set_missing_equals_exits(tmp_path):
    with patch('lib.get_skills_home', return_value=str(tmp_path)), \
         patch('lib.is_project_mode', return_value=False):
        with pytest.raises(SystemExit):
            env_set('NO_EQUALS')


def test_env_set_empty_key_exits(tmp_path):
    with patch('lib.get_skills_home', return_value=str(tmp_path)), \
         patch('lib.is_project_mode', return_value=False):
        with pytest.raises(SystemExit):
            env_set('=value')


def test_env_set_writes_to_local_env_in_project_mode(tmp_path, capsys):
    with patch('lib.is_project_mode', return_value=True), \
         patch('os.getcwd', return_value=str(tmp_path)):
        env_set('MY_KEY=localval')
    local_env = tmp_path / '.env'
    assert local_env.exists()
    assert 'MY_KEY=localval' in local_env.read_text()


def test_env_set_global_unaffected_in_project_mode(tmp_path, capsys):
    global_dir = tmp_path / 'global'
    global_dir.mkdir()
    local_dir = tmp_path / 'project'
    local_dir.mkdir()
    with patch('lib.is_project_mode', return_value=True), \
         patch('os.getcwd', return_value=str(local_dir)), \
         patch('lib.get_skills_home', return_value=str(global_dir)):
        env_set('PROJECT_KEY=projectval')
    assert not (global_dir / '.env').exists()
    assert 'PROJECT_KEY=projectval' in (local_dir / '.env').read_text()


def test_env_list_prints_keys_not_values(tmp_path, capsys):
    env_file = tmp_path / '.env'
    env_file.write_text('POND_HERMES_KEY=secret\nGOLLUM_HERMES_KEY=other\n')
    with patch('lib.get_skills_home', return_value=str(tmp_path)), \
         patch('lib.is_project_mode', return_value=False):
        env_list()
    out = capsys.readouterr().out
    assert 'POND_HERMES_KEY' in out
    assert 'GOLLUM_HERMES_KEY' in out
    assert 'secret' not in out
    assert 'other' not in out


def test_env_list_empty(tmp_path, capsys):
    with patch('lib.get_skills_home', return_value=str(tmp_path)), \
         patch('lib.is_project_mode', return_value=False):
        env_list()
    assert 'No entries' in capsys.readouterr().out


def test_env_list_shows_path_header(tmp_path, capsys):
    env_file = tmp_path / '.env'
    env_file.write_text('KEY=val\n')
    with patch('lib.get_skills_home', return_value=str(tmp_path)), \
         patch('lib.is_project_mode', return_value=False):
        env_list()
    assert str(tmp_path) in capsys.readouterr().out


def test_env_init_scaffolds_from_example(tmp_path, capsys):
    skill_dir = tmp_path / 'ask-remote-agent-skill'
    skill_dir.mkdir()
    (skill_dir / '.env.example').write_text('POND_HERMES_KEY=\nGOLLUM_HERMES_KEY=\n')

    p = tmp_path / 'skills.md'
    skills = [{'name': 'ask-remote-agent-skill', 'url': 'u', 'local_path': str(skill_dir), 'load_at_startup': False, 'version': ''}]
    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('lib.get_skills_home', return_value=str(tmp_path)), \
         patch('lib.is_project_mode', return_value=False):
        write_skill_list(skills)
        env_init()

    out = capsys.readouterr().out
    assert 'Added POND_HERMES_KEY' in out
    assert 'Added GOLLUM_HERMES_KEY' in out
    assert (tmp_path / '.env').exists()


def test_env_init_skips_existing_keys(tmp_path, capsys):
    skill_dir = tmp_path / 'myskill'
    skill_dir.mkdir()
    (skill_dir / '.env.example').write_text('POND_HERMES_KEY=\n')

    env_file = tmp_path / '.env'
    env_file.write_text('POND_HERMES_KEY=existing\n')

    p = tmp_path / 'skills.md'
    skills = [{'name': 'myskill', 'url': 'u', 'local_path': str(skill_dir), 'load_at_startup': False, 'version': ''}]
    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('lib.get_skills_home', return_value=str(tmp_path)), \
         patch('lib.is_project_mode', return_value=False):
        write_skill_list(skills)
        env_init()

    assert 'Nothing new' in capsys.readouterr().out
    assert 'POND_HERMES_KEY=existing' in env_file.read_text()


def test_env_init_no_skills(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('lib.get_skills_home', return_value=str(tmp_path)), \
         patch('lib.is_project_mode', return_value=False):
        env_init()
    assert 'No skills' in capsys.readouterr().out


def test_env_init_scaffolds_to_local_env_in_project_mode(tmp_path, capsys):
    project_dir = tmp_path / 'project'
    project_dir.mkdir()
    skill_dir = tmp_path / 'myskill'
    skill_dir.mkdir()
    (skill_dir / '.env.example').write_text('PROJECT_KEY=\n')

    p = project_dir / 'skills.md'
    skills = [{'name': 'myskill', 'url': 'u', 'local_path': str(skill_dir), 'load_at_startup': False, 'version': ''}]
    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('lib.is_project_mode', return_value=True), \
         patch('os.getcwd', return_value=str(project_dir)):
        write_skill_list(skills)
        env_init()

    assert 'Added PROJECT_KEY' in capsys.readouterr().out
    assert (project_dir / '.env').exists()


def test_env_init_local_can_overlap_global(tmp_path, capsys):
    """A key already in the global .env can still be added to the local one."""
    project_dir = tmp_path / 'project'
    project_dir.mkdir()
    global_dir = tmp_path / 'global'
    global_dir.mkdir()
    (global_dir / '.env').write_text('SHARED_KEY=global_val\n')

    skill_dir = tmp_path / 'myskill'
    skill_dir.mkdir()
    (skill_dir / '.env.example').write_text('SHARED_KEY=\n')

    p = project_dir / 'skills.md'
    skills = [{'name': 'myskill', 'url': 'u', 'local_path': str(skill_dir), 'load_at_startup': False, 'version': ''}]
    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('lib.is_project_mode', return_value=True), \
         patch('lib.get_skills_home', return_value=str(global_dir)), \
         patch('os.getcwd', return_value=str(project_dir)):
        write_skill_list(skills)
        env_init()

    assert 'Added SHARED_KEY' in capsys.readouterr().out
    assert (project_dir / '.env').exists()
