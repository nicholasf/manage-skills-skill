from unittest.mock import patch

import pytest

from lib import write_skill_list
from subcommands.check import _check_dependencies as check_dependencies


def test_check_dependencies_detects_cycle(tmp_path, capsys):
    a_dir = tmp_path / 'a-skill'
    a_dir.mkdir()
    (a_dir / 'SKILL.md').write_text('---\ndepends_on:\n  - b-skill\n---\n')

    b_dir = tmp_path / 'b-skill'
    b_dir.mkdir()
    (b_dir / 'SKILL.md').write_text('---\ndepends_on:\n  - a-skill\n---\n')

    p = tmp_path / 'skills.md'
    skills = [
        {'name': 'a-skill', 'url': 'u1', 'local_path': str(a_dir), 'load_at_startup': False, 'version': ''},
        {'name': 'b-skill', 'url': 'u2', 'local_path': str(b_dir), 'load_at_startup': False, 'version': ''},
    ]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        with pytest.raises(SystemExit):
            check_dependencies()

    assert 'cycle' in capsys.readouterr().out.lower()


def test_check_dependencies_clean(tmp_path, capsys):
    a_dir = tmp_path / 'a-skill'
    a_dir.mkdir()
    (a_dir / 'SKILL.md').write_text('---\ndepends_on:\n  - b-skill\n---\n')

    b_dir = tmp_path / 'b-skill'
    b_dir.mkdir()
    (b_dir / 'SKILL.md').write_text('---\nname: b-skill\n---\n')

    p = tmp_path / 'skills.md'
    skills = [
        {'name': 'a-skill', 'url': 'u1', 'local_path': str(a_dir), 'load_at_startup': False, 'version': ''},
        {'name': 'b-skill', 'url': 'u2', 'local_path': str(b_dir), 'load_at_startup': False, 'version': ''},
    ]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        check_dependencies()

    assert 'No dependency cycles' in capsys.readouterr().out
