import os
from unittest.mock import Mock, patch

import pytest

from lib import (
    check_registry_drift,
    find_cycle,
    format_drift_report,
    get_skill_list_path,
    is_project_mode,
    read_skill_dependencies,
    read_skill_list,
    write_skill_list,
)


# -- get_skill_list_path --

def test_get_skill_list_path_returns_local_when_exists(tmp_path):
    local = tmp_path / 'skills.md'
    local.write_text('')
    with patch('os.getcwd', return_value=str(tmp_path)):
        result = get_skill_list_path()
    assert result == str(local)


def test_get_skill_list_path_falls_back_to_global(tmp_path):
    with patch('os.getcwd', return_value=str(tmp_path)), \
         patch('lib.get_global_skills_path', return_value='/global/skills.md'):
        result = get_skill_list_path()
    assert result == '/global/skills.md'


# -- read_skill_list --

def test_read_skill_list_missing_file(tmp_path):
    with patch('lib.get_skill_list_path', return_value=str(tmp_path / 'nonexistent.md')):
        assert read_skill_list() == []


def test_read_skill_list_empty_file(tmp_path):
    p = tmp_path / 'skills.md'
    p.write_text('')
    with patch('lib.get_skill_list_path', return_value=str(p)):
        assert read_skill_list() == []


def test_read_skill_list_no_table(tmp_path):
    p = tmp_path / 'skills.md'
    p.write_text('# Skills\n\nNo table here.\n')
    with patch('lib.get_skill_list_path', return_value=str(p)):
        assert read_skill_list() == []


def test_read_skill_list_valid_5_column_table(tmp_path):
    p = tmp_path / 'skills.md'
    p.write_text(
        '| name | url | local_path | load_at_startup | version |\n'
        '|------|-----|------------|-----------------|--------|\n'
        '| skill1 | https://github.com/u/skill1 | /path/skill1 | true | abc1234 |\n'
        '| skill2 | https://github.com/u/skill2 | /path/skill2 | false |  |\n'
    )
    with patch('lib.get_skill_list_path', return_value=str(p)):
        result = read_skill_list()
    assert result == [
        {'name': 'skill1', 'url': 'https://github.com/u/skill1', 'local_path': '/path/skill1', 'load_at_startup': True, 'version': 'abc1234'},
        {'name': 'skill2', 'url': 'https://github.com/u/skill2', 'local_path': '/path/skill2', 'load_at_startup': False, 'version': ''},
    ]


def test_read_skill_list_old_4_column_table_defaults_version_empty(tmp_path):
    p = tmp_path / 'skills.md'
    p.write_text(
        '| name | url | local_path | load_at_startup |\n'
        '|------|-----|------------|-----------------|\n'
        '| skill1 | https://github.com/u/skill1 | /path/skill1 | false |\n'
    )
    with patch('lib.get_skill_list_path', return_value=str(p)):
        result = read_skill_list()
    assert result[0]['version'] == ''


def test_read_skill_list_old_3_column_table_defaults_load_at_startup_false(tmp_path):
    p = tmp_path / 'skills.md'
    p.write_text(
        '| name | url | local_path |\n'
        '|------|-----|------------|\n'
        '| skill1 | https://github.com/u/skill1 | /path/skill1 |\n'
    )
    with patch('lib.get_skill_list_path', return_value=str(p)):
        result = read_skill_list()
    assert result[0]['load_at_startup'] is False
    assert result[0]['version'] == ''


# -- write_skill_list / round-trip --

def test_write_read_round_trip(tmp_path):
    p = tmp_path / 'skills.md'
    skills = [
        {'name': 'a', 'url': 'https://example.com/a', 'local_path': '/tmp/a', 'load_at_startup': True, 'version': 'abc1234'},
        {'name': 'b', 'url': 'https://example.com/b', 'local_path': '/tmp/b', 'load_at_startup': False, 'version': ''},
    ]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        result = read_skill_list()
    assert result == skills


def test_write_skill_list_includes_version_column(tmp_path):
    p = tmp_path / 'skills.md'
    skills = [{'name': 'x', 'url': 'u', 'local_path': '/tmp/x', 'load_at_startup': False, 'version': 'deadbeef'}]
    with patch('lib.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
    assert 'deadbeef' in p.read_text()
    assert 'git_sha1' in p.read_text()


# -- read_skill_dependencies --

def test_read_skill_dependencies_with_depends_on(tmp_path):
    skill_dir = tmp_path / 'myskill'
    skill_dir.mkdir()
    (skill_dir / 'SKILL.md').write_text(
        '---\n'
        'name: myskill\n'
        'depends_on:\n'
        '  - load-topology-skill\n'
        '  - other-skill\n'
        '---\n'
        '\n'
        '# My Skill\n'
    )
    assert read_skill_dependencies(str(skill_dir)) == ['load-topology-skill', 'other-skill']


def test_read_skill_dependencies_no_frontmatter(tmp_path):
    skill_dir = tmp_path / 'myskill'
    skill_dir.mkdir()
    (skill_dir / 'SKILL.md').write_text('# My Skill\n\nNo frontmatter here.\n')
    assert read_skill_dependencies(str(skill_dir)) == []


def test_read_skill_dependencies_frontmatter_without_depends_on(tmp_path):
    skill_dir = tmp_path / 'myskill'
    skill_dir.mkdir()
    (skill_dir / 'SKILL.md').write_text(
        '---\n'
        'name: myskill\n'
        'description: Does a thing.\n'
        '---\n'
        '\n'
        '# My Skill\n'
    )
    assert read_skill_dependencies(str(skill_dir)) == []


def test_read_skill_dependencies_missing_skill_md(tmp_path):
    skill_dir = tmp_path / 'myskill'
    skill_dir.mkdir()
    assert read_skill_dependencies(str(skill_dir)) == []


# -- find_cycle --

def test_find_cycle_empty_graph():
    assert find_cycle({}) is None


def test_find_cycle_no_cycle_linear():
    assert find_cycle({'a': ['b'], 'b': ['c'], 'c': []}) is None


def test_find_cycle_direct_cycle():
    cycle = find_cycle({'a': ['b'], 'b': ['a']})
    assert cycle is not None
    assert cycle[0] == cycle[-1]
    assert set(cycle) >= {'a', 'b'}


def test_find_cycle_indirect_cycle():
    cycle = find_cycle({'a': ['b'], 'b': ['c'], 'c': ['a']})
    assert cycle is not None
    assert cycle[0] == cycle[-1]
    assert set(cycle) >= {'a', 'b', 'c'}


def test_find_cycle_diamond_no_cycle():
    assert find_cycle({'a': ['b', 'c'], 'b': ['d'], 'c': ['d'], 'd': []}) is None


# -- is_project_mode --

def test_is_project_mode_true_when_skills_md_present(tmp_path):
    (tmp_path / 'skills.md').write_text('')
    with patch('os.getcwd', return_value=str(tmp_path)):
        assert is_project_mode() is True


def test_is_project_mode_false_without_skills_md(tmp_path):
    with patch('os.getcwd', return_value=str(tmp_path)):
        assert is_project_mode() is False


# -- check_registry_drift --

def _skill(name, local_path, url='u'):
    return {'name': name, 'url': url, 'local_path': str(local_path), 'load_at_startup': False, 'version': ''}


def test_check_registry_drift_missing_local_path(tmp_path):
    skills = [_skill('ghost', tmp_path / 'missing')]
    drifted = check_registry_drift(skills)
    assert len(drifted) == 1
    assert drifted[0]['name'] == 'ghost'
    assert 'does not exist' in drifted[0]['issues'][0]


def test_check_registry_drift_url_mismatch(tmp_path, monkeypatch):
    local = tmp_path / 'skill'
    local.mkdir()
    skills_home = tmp_path / 'skills-home'
    skills_home.mkdir()
    os.symlink(local, skills_home / 'skill')
    monkeypatch.setenv('SKILLS_HOME', str(skills_home))

    skills = [_skill('skill', local, url='git@github.com:x/old-name.git')]
    with patch('subprocess.run', return_value=Mock(stdout='git@github.com:x/new-name.git\n')):
        drifted = check_registry_drift(skills)

    assert len(drifted) == 1
    assert 'does not match git remote' in drifted[0]['issues'][0]


def test_check_registry_drift_missing_symlink(tmp_path, monkeypatch):
    local = tmp_path / 'skill'
    local.mkdir()
    skills_home = tmp_path / 'skills-home'
    skills_home.mkdir()
    monkeypatch.setenv('SKILLS_HOME', str(skills_home))

    skills = [_skill('skill', local)]
    with patch('subprocess.run', return_value=Mock(stdout='u\n')):
        drifted = check_registry_drift(skills)

    assert any('missing symlink' in issue for issue in drifted[0]['issues'])


def test_check_registry_drift_symlink_points_elsewhere(tmp_path, monkeypatch):
    local = tmp_path / 'skill'
    local.mkdir()
    other = tmp_path / 'other'
    other.mkdir()
    skills_home = tmp_path / 'skills-home'
    skills_home.mkdir()
    os.symlink(other, skills_home / 'skill')
    monkeypatch.setenv('SKILLS_HOME', str(skills_home))

    skills = [_skill('skill', local)]
    with patch('subprocess.run', return_value=Mock(stdout='u\n')):
        drifted = check_registry_drift(skills)

    assert any('points elsewhere' in issue for issue in drifted[0]['issues'])


def test_check_registry_drift_missing_command_symlink(tmp_path, monkeypatch):
    local = tmp_path / 'skill'
    local.mkdir()
    (local / 'command.md').write_text('# Skill')
    skills_home = tmp_path / 'skills-home'
    skills_home.mkdir()
    os.symlink(local, skills_home / 'skill')
    monkeypatch.setenv('SKILLS_HOME', str(skills_home))
    monkeypatch.setenv('HOME', str(tmp_path))

    skills = [_skill('skill', local)]
    with patch('subprocess.run', return_value=Mock(stdout='u\n')):
        drifted = check_registry_drift(skills)

    assert any('command symlink' in issue for issue in drifted[0]['issues'])


def test_check_registry_drift_clean(tmp_path, monkeypatch):
    local = tmp_path / 'skill'
    local.mkdir()
    (local / 'command.md').write_text('# Skill')
    skills_home = tmp_path / 'skills-home'
    skills_home.mkdir()
    os.symlink(local, skills_home / 'skill')
    monkeypatch.setenv('SKILLS_HOME', str(skills_home))
    monkeypatch.setenv('HOME', str(tmp_path))
    commands_dir = tmp_path / '.claude' / 'commands'
    commands_dir.mkdir(parents=True)
    os.symlink(local / 'command.md', commands_dir / 'skill.md')

    skills = [_skill('skill', local)]
    with patch('subprocess.run', return_value=Mock(stdout='u\n')):
        drifted = check_registry_drift(skills)

    assert drifted == []


# -- format_drift_report --

def test_format_drift_report_empty():
    assert format_drift_report([]) == ''


def test_format_drift_report_lists_name_and_issues():
    drifted = [{'name': 'skill', 'issues': ['issue one', 'issue two']}]
    report = format_drift_report(drifted)
    assert 'skill' in report
    assert 'issue one' in report
    assert 'issue two' in report
