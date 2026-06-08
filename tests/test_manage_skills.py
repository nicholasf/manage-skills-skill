import json
import os
import subprocess
from unittest.mock import Mock, MagicMock, call, patch

import pytest

from manage_skills import (
    build_dependency_graph,
    check_dependencies,
    context_output,
    env_init,
    env_list,
    env_set,
    find_cycle,
    get_global_skills_path,
    get_skill_list_path,
    init_project,
    install_skill,
    list_skills,
    read_skill_dependencies,
    read_skill_list,
    resolve_sha1,
    sync_skill,
    write_skill_list,
    _is_project_mode,
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
         patch('manage_skills.get_global_skills_path', return_value='/global/skills.md'):
        result = get_skill_list_path()
    assert result == '/global/skills.md'


# -- read_skill_list --

def test_read_skill_list_missing_file(tmp_path):
    with patch('manage_skills.get_skill_list_path', return_value=str(tmp_path / 'nonexistent.md')):
        assert read_skill_list() == []


def test_read_skill_list_empty_file(tmp_path):
    p = tmp_path / 'skills.md'
    p.write_text('')
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        assert read_skill_list() == []


def test_read_skill_list_no_table(tmp_path):
    p = tmp_path / 'skills.md'
    p.write_text('# Skills\n\nNo table here.\n')
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        assert read_skill_list() == []


def test_read_skill_list_valid_5_column_table(tmp_path):
    p = tmp_path / 'skills.md'
    p.write_text(
        '| name | url | local_path | load_at_startup | version |\n'
        '|------|-----|------------|-----------------|--------|\n'
        '| skill1 | https://github.com/u/skill1 | /path/skill1 | true | abc1234 |\n'
        '| skill2 | https://github.com/u/skill2 | /path/skill2 | false |  |\n'
    )
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
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
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        result = read_skill_list()
    assert result[0]['version'] == ''


def test_read_skill_list_old_3_column_table_defaults_load_at_startup_false(tmp_path):
    p = tmp_path / 'skills.md'
    p.write_text(
        '| name | url | local_path |\n'
        '|------|-----|------------|\n'
        '| skill1 | https://github.com/u/skill1 | /path/skill1 |\n'
    )
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
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
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        result = read_skill_list()
    assert result == skills


def test_write_skill_list_includes_version_column(tmp_path):
    p = tmp_path / 'skills.md'
    skills = [{'name': 'x', 'url': 'u', 'local_path': '/tmp/x', 'load_at_startup': False, 'version': 'deadbeef'}]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
    assert 'deadbeef' in p.read_text()
    assert 'version' in p.read_text()


# -- context_output --

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

    p = tmp_path / 'skills.md'
    skills = [
        {'name': 's1', 'url': 'u1', 'local_path': str(tmp_path / 's1'), 'load_at_startup': True, 'version': ''},
        {'name': 's2', 'url': 'u2', 'local_path': str(tmp_path / 's2'), 'load_at_startup': True, 'version': ''},
    ]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        context_output()

    ctx = json.loads(capsys.readouterr().out)['hookSpecificOutput']['additionalContext']
    assert '\n\n---\n\n' in ctx


def test_context_output_missing_skill_md_warns_stderr_and_skips(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    skills = [
        {'name': 'ghost', 'url': 'u', 'local_path': str(tmp_path / 'ghost'), 'load_at_startup': True, 'version': ''},
    ]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        context_output()

    captured = capsys.readouterr()
    assert 'ghost' in captured.err
    assert json.loads(captured.out)['hookSpecificOutput']['additionalContext'] == ''


def test_context_output_valid_json_structure(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
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
    with patch('manage_skills.get_skill_list_path', return_value=str(local_skills)):
        write_skill_list(skills)
        context_output()

    ctx = json.loads(capsys.readouterr().out)['hookSpecificOutput']['additionalContext']
    assert 'Local skill content' in ctx


# -- install_skill --

def test_install_skill_clones_and_symlinks(tmp_path):
    p = tmp_path / 'skills.md'
    skills_home = str(tmp_path / 'skills')

    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('manage_skills.get_skills_home', return_value=skills_home), \
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

    clone_result = Mock()
    fetch_result = Mock()
    checkout_result = Mock()
    revparse_result = Mock(stdout=full_sha + '\n')

    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('manage_skills.get_skills_home', return_value=skills_home), \
         patch('subprocess.run', side_effect=[clone_result, fetch_result, checkout_result, revparse_result]) as mock_run, \
         patch('os.symlink'), \
         patch('os.path.lexists', return_value=False), \
         patch('os.makedirs'):

        install_skill('https://github.com/user/myskill', name='myskill', local_path='/tmp/myskill', version='v1.0')

        calls = mock_run.call_args_list
        assert calls[0] == call(['git', 'clone', 'https://github.com/user/myskill', '/tmp/myskill'], check=True)
        assert calls[1] == call(['git', '-C', '/tmp/myskill', 'fetch', 'origin'], check=True, capture_output=True)
        assert calls[2] == call(['git', '-C', '/tmp/myskill', 'checkout', 'v1.0'], check=True, capture_output=True)
        assert calls[3] == call(['git', '-C', '/tmp/myskill', 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True)

    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        result = read_skill_list()
    assert result[0]['version'] == full_sha


def test_install_skill_derives_name_from_url(tmp_path):
    p = tmp_path / 'skills.md'
    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('manage_skills.get_skills_home', return_value=str(tmp_path / 'skills')), \
         patch('subprocess.run'), \
         patch('os.symlink'), \
         patch('os.path.lexists', return_value=False), \
         patch('os.makedirs'):

        install_skill('https://github.com/user/myskill.git', local_path='/tmp/myskill')

    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        result = read_skill_list()
    assert result[0]['name'] == 'myskill'


def test_install_skill_records_load_at_startup(tmp_path):
    p = tmp_path / 'skills.md'
    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('manage_skills.get_skills_home', return_value=str(tmp_path / 'skills')), \
         patch('subprocess.run'), \
         patch('os.symlink'), \
         patch('os.path.lexists', return_value=False), \
         patch('os.makedirs'):

        install_skill('https://github.com/user/myskill', name='myskill', local_path='/tmp/myskill', load_at_startup=True)

    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        result = read_skill_list()
    assert result[0]['load_at_startup'] is True


def test_install_skill_creates_skills_dir_symlink_when_project(tmp_path):
    p = tmp_path / 'skills.md'
    p.write_text('| name | url | local_path | load_at_startup | version |\n|------|-----|------------|-----------------|--------|\n')
    skills_home = str(tmp_path / 'skills_home')
    skills_dir = tmp_path / '.skills'

    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('manage_skills.get_skills_home', return_value=skills_home), \
         patch('os.getcwd', return_value=str(tmp_path)), \
         patch('subprocess.run'), \
         patch('os.symlink') as mock_symlink, \
         patch('os.path.lexists', return_value=False), \
         patch('os.makedirs'):

        install_skill('https://github.com/user/myskill', name='myskill', local_path='/tmp/myskill')

    symlink_targets = [c[0] for c in mock_symlink.call_args_list]
    assert ('/tmp/myskill', os.path.join(str(tmp_path), '.skills', 'myskill')) in symlink_targets


# -- sync_skill --

def test_sync_skill_all(tmp_path):
    p = tmp_path / 'skills.md'
    skills = [
        {'name': 'a', 'url': 'u1', 'local_path': '/tmp/a', 'load_at_startup': False, 'version': ''},
        {'name': 'b', 'url': 'u2', 'local_path': '/tmp/b', 'load_at_startup': False, 'version': ''},
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
    p = tmp_path / 'skills.md'
    skills = [
        {'name': 'a', 'url': 'u1', 'local_path': '/tmp/a', 'load_at_startup': False, 'version': ''},
        {'name': 'b', 'url': 'u2', 'local_path': '/tmp/b', 'load_at_startup': False, 'version': ''},
    ]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)

    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(stdout='Already up to date.', stderr='')
        sync_skill('a')

    mock_run.assert_called_once_with(['git', '-C', '/tmp/a', 'pull'], capture_output=True, text=True, check=True)


def test_sync_skill_pinned_rechecks_out(tmp_path):
    p = tmp_path / 'skills.md'
    sha = 'b' * 40
    skills = [{'name': 'a', 'url': 'u', 'local_path': '/tmp/a', 'load_at_startup': False, 'version': sha}]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)

    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(stdout='', stderr='')
        sync_skill('a')

    calls = mock_run.call_args_list
    assert call(['git', '-C', '/tmp/a', 'fetch', 'origin'], check=True, capture_output=True) in calls
    assert call(['git', '-C', '/tmp/a', 'checkout', sha], check=True, capture_output=True) in calls
    pull_call = call(['git', '-C', '/tmp/a', 'pull'], capture_output=True, text=True, check=True)
    assert pull_call not in calls


def test_sync_skill_with_version_arg_repins(tmp_path):
    p = tmp_path / 'skills.md'
    old_sha = 'a' * 40
    new_sha = 'c' * 40
    skills = [{'name': 'a', 'url': 'u', 'local_path': '/tmp/a', 'load_at_startup': False, 'version': old_sha}]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)

    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(stdout=new_sha + '\n', stderr='')
        sync_skill('a', version='v2.0')

    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        result = read_skill_list()
    assert result[0]['version'] == new_sha


def test_sync_skill_version_requires_name(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list([])
        with pytest.raises(SystemExit):
            sync_skill(version='v1.0')
    assert 'requires a skill name' in capsys.readouterr().out


def test_sync_skill_unknown_name_prints_not_found(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    skills = [{'name': 'a', 'url': 'u', 'local_path': '/tmp/a', 'load_at_startup': False, 'version': ''}]
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
    p = tmp_path / 'skills.md'
    skills = [{'name': 'a', 'url': 'u', 'local_path': '/tmp/a', 'load_at_startup': False, 'version': ''}]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)

    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, 'git', stderr='fetch failed')):
        sync_skill('a')  # must not raise

    assert 'Error' in capsys.readouterr().out


# -- init_project --

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


# -- install_skill cycle check --

def test_install_skill_aborts_on_cycle(tmp_path):
    b_dir = tmp_path / 'b-skill'
    b_dir.mkdir()
    (b_dir / 'SKILL.md').write_text('---\ndepends_on:\n  - a-skill\n---\n# B\n')

    a_dir = tmp_path / 'a-skill'
    a_dir.mkdir()
    (a_dir / 'SKILL.md').write_text('---\ndepends_on:\n  - b-skill\n---\n# A\n')

    p = tmp_path / 'skills.md'
    skills = [{'name': 'b-skill', 'url': 'u', 'local_path': str(b_dir), 'load_at_startup': False, 'version': ''}]

    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('manage_skills.get_skills_home', return_value=str(tmp_path / 'skills')):
        write_skill_list(skills)
        with pytest.raises(SystemExit):
            install_skill('https://github.com/u/a-skill', name='a-skill', local_path=str(a_dir), skip_clone=True)


# -- check_dependencies --

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
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
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
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        check_dependencies()

    assert 'No dependency cycles' in capsys.readouterr().out


# -- list_skills --

def test_list_skills_empty(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        list_skills()
    assert 'No skills found.' in capsys.readouterr().out


def test_list_skills_prints_table(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    skills = [{'name': 'mything', 'url': 'https://x.com/y', 'local_path': '/tmp/y', 'load_at_startup': True, 'version': 'abc1234'}]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)):
        write_skill_list(skills)
        list_skills()
    out = capsys.readouterr().out
    assert 'mything' in out
    assert 'version' in out


# -- env_set / env_list / env_init --

def test_env_set_creates_file(tmp_path, capsys):
    with patch('manage_skills.get_skills_home', return_value=str(tmp_path)), \
         patch('manage_skills._is_project_mode', return_value=False):
        env_set('POND_HERMES_KEY=abc123')
    env_file = tmp_path / '.env'
    assert env_file.exists()
    assert 'POND_HERMES_KEY=abc123' in env_file.read_text()
    assert 'Set POND_HERMES_KEY' in capsys.readouterr().out


def test_env_set_updates_existing_key(tmp_path):
    env_file = tmp_path / '.env'
    env_file.write_text('POND_HERMES_KEY=old\n')
    with patch('manage_skills.get_skills_home', return_value=str(tmp_path)), \
         patch('manage_skills._is_project_mode', return_value=False):
        env_set('POND_HERMES_KEY=new')
    assert 'POND_HERMES_KEY=new' in env_file.read_text()
    assert 'POND_HERMES_KEY=old' not in env_file.read_text()


def test_env_set_missing_equals_exits(tmp_path):
    with patch('manage_skills.get_skills_home', return_value=str(tmp_path)), \
         patch('manage_skills._is_project_mode', return_value=False):
        with pytest.raises(SystemExit):
            env_set('NO_EQUALS')


def test_env_set_empty_key_exits(tmp_path):
    with patch('manage_skills.get_skills_home', return_value=str(tmp_path)), \
         patch('manage_skills._is_project_mode', return_value=False):
        with pytest.raises(SystemExit):
            env_set('=value')


def test_env_list_prints_keys_not_values(tmp_path, capsys):
    env_file = tmp_path / '.env'
    env_file.write_text('POND_HERMES_KEY=secret\nGOLLUM_HERMES_KEY=other\n')
    with patch('manage_skills.get_skills_home', return_value=str(tmp_path)), \
         patch('manage_skills._is_project_mode', return_value=False):
        env_list()
    out = capsys.readouterr().out
    assert 'POND_HERMES_KEY' in out
    assert 'GOLLUM_HERMES_KEY' in out
    assert 'secret' not in out
    assert 'other' not in out


def test_env_list_empty(tmp_path, capsys):
    with patch('manage_skills.get_skills_home', return_value=str(tmp_path)), \
         patch('manage_skills._is_project_mode', return_value=False):
        env_list()
    assert 'No entries' in capsys.readouterr().out


def test_env_list_shows_path_header(tmp_path, capsys):
    env_file = tmp_path / '.env'
    env_file.write_text('KEY=val\n')
    with patch('manage_skills.get_skills_home', return_value=str(tmp_path)), \
         patch('manage_skills._is_project_mode', return_value=False):
        env_list()
    assert str(tmp_path) in capsys.readouterr().out


def test_env_set_writes_to_local_env_in_project_mode(tmp_path, capsys):
    with patch('manage_skills._is_project_mode', return_value=True), \
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
    with patch('manage_skills._is_project_mode', return_value=True), \
         patch('os.getcwd', return_value=str(local_dir)), \
         patch('manage_skills.get_skills_home', return_value=str(global_dir)):
        env_set('PROJECT_KEY=projectval')
    assert not (global_dir / '.env').exists()
    assert 'PROJECT_KEY=projectval' in (local_dir / '.env').read_text()


def test_is_project_mode_true_when_skills_md_present(tmp_path):
    (tmp_path / 'skills.md').write_text('')
    with patch('os.getcwd', return_value=str(tmp_path)):
        assert _is_project_mode() is True


def test_is_project_mode_false_without_skills_md(tmp_path):
    with patch('os.getcwd', return_value=str(tmp_path)):
        assert _is_project_mode() is False


def test_env_init_scaffolds_from_example(tmp_path, capsys):
    skill_dir = tmp_path / 'ask-remote-agent-skill'
    skill_dir.mkdir()
    (skill_dir / '.env.example').write_text('POND_HERMES_KEY=\nGOLLUM_HERMES_KEY=\n')

    p = tmp_path / 'skills.md'
    skills = [{'name': 'ask-remote-agent-skill', 'url': 'u', 'local_path': str(skill_dir), 'load_at_startup': False, 'version': ''}]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('manage_skills.get_skills_home', return_value=str(tmp_path)), \
         patch('manage_skills._is_project_mode', return_value=False):
        write_skill_list(skills)
        env_init()

    out = capsys.readouterr().out
    assert 'Added POND_HERMES_KEY' in out
    assert 'Added GOLLUM_HERMES_KEY' in out
    env_file = tmp_path / '.env'
    assert env_file.exists()


def test_env_init_skips_existing_keys(tmp_path, capsys):
    skill_dir = tmp_path / 'myskill'
    skill_dir.mkdir()
    (skill_dir / '.env.example').write_text('POND_HERMES_KEY=\n')

    env_file = tmp_path / '.env'
    env_file.write_text('POND_HERMES_KEY=existing\n')

    p = tmp_path / 'skills.md'
    skills = [{'name': 'myskill', 'url': 'u', 'local_path': str(skill_dir), 'load_at_startup': False, 'version': ''}]
    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('manage_skills.get_skills_home', return_value=str(tmp_path)), \
         patch('manage_skills._is_project_mode', return_value=False):
        write_skill_list(skills)
        env_init()

    assert 'Nothing new' in capsys.readouterr().out
    assert 'POND_HERMES_KEY=existing' in env_file.read_text()


def test_env_init_no_skills(tmp_path, capsys):
    p = tmp_path / 'skills.md'
    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('manage_skills.get_skills_home', return_value=str(tmp_path)), \
         patch('manage_skills._is_project_mode', return_value=False):
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
    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('manage_skills._is_project_mode', return_value=True), \
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
    with patch('manage_skills.get_skill_list_path', return_value=str(p)), \
         patch('manage_skills._is_project_mode', return_value=True), \
         patch('manage_skills.get_skills_home', return_value=str(global_dir)), \
         patch('os.getcwd', return_value=str(project_dir)):
        write_skill_list(skills)
        env_init()

    assert 'Added SHARED_KEY' in capsys.readouterr().out
    assert (project_dir / '.env').exists()
