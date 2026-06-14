from unittest.mock import patch

from lib import write_skill_list
from subcommands.list import _list_skills as list_skills


def test_list_skills_empty(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    with patch('lib.get_skill_list_path', return_value=str(p)):
        list_skills()
    assert 'No skills found.' in capsys.readouterr().out


def test_list_skills_prints_table(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    skills = [{'name': 'mything', 'url': 'https://x.com/y', 'local_path': '/tmp/y', 'load_at_startup': True, 'version': 'abc1234'}]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        list_skills()
    out = capsys.readouterr().out
    assert 'mything' in out
    assert 'git_sha1' in out
