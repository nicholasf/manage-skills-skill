import os
from unittest.mock import Mock, patch

import pytest

from lib import write_skill_list
from subcommands.check import _check_dependencies as check_dependencies
from subcommands.check import _check_drift as check_drift
from subcommands.check import run


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


# -- _check_drift --

def test_check_drift_no_skills_prints_nothing(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    with patch('lib.get_skill_list_path', return_value=str(p)):
        check_drift()
    assert capsys.readouterr().out == ''


def test_check_drift_reports_clean(tmp_path, monkeypatch, capsys):
    local = tmp_path / 'skill'
    local.mkdir()
    skills_home = tmp_path / 'skills-home'
    skills_home.mkdir()
    os.symlink(local, skills_home / 'skill')
    monkeypatch.setenv('SKILLS_HOME', str(skills_home))

    p = tmp_path / 'skills.md'
    skills = [{'name': 'skill', 'url': 'u', 'local_path': str(local), 'load_at_startup': False, 'version': ''}]
    with patch('lib.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run', return_value=Mock(stdout='u\n')):
        write_skill_list(skills)
        check_drift()

    assert 'No registry drift found' in capsys.readouterr().out


def test_check_drift_reports_issues(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    skills = [{'name': 'ghost', 'url': 'u', 'local_path': str(tmp_path / 'missing'), 'load_at_startup': False, 'version': ''}]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        check_drift()

    out = capsys.readouterr().out
    assert 'ghost' in out
    assert 'does not exist' in out


# -- run --

def test_run_reports_drift_even_when_cycle_detected(tmp_path, capsys):
    """Drift check must run before the cycle check exits, not be skipped by it."""
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
        {'name': 'ghost', 'url': 'u3', 'local_path': str(tmp_path / 'missing'), 'load_at_startup': False, 'version': ''},
    ]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        with pytest.raises(SystemExit):
            run(None)

    out = capsys.readouterr().out
    assert 'ghost' in out
    assert 'cycle' in out.lower()
