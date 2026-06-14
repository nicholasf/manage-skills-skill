from unittest.mock import patch

from subcommands.init import _init_project as init_project


def test_init_project_creates_skills_md_and_skills_dir(tmp_path):
    with patch('os.getcwd', return_value=str(tmp_path)):
        init_project()
    assert (tmp_path / 'skills.md').exists()
    assert (tmp_path / '.skills').is_dir()


def test_init_project_skills_md_has_correct_headers(tmp_path):
    with patch('os.getcwd', return_value=str(tmp_path)):
        init_project()
    content = (tmp_path / 'skills.md').read_text()
    assert 'version' in content
    assert 'name' in content


def test_init_project_noop_if_skills_md_exists(tmp_path, capsys):
    (tmp_path / 'skills.md').write_text('existing')
    with patch('os.getcwd', return_value=str(tmp_path)):
        init_project()
    assert (tmp_path / 'skills.md').read_text() == 'existing'
    assert 'already exists' in capsys.readouterr().out
