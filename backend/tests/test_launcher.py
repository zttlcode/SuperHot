import importlib.util
import json
import sys
import uuid
from pathlib import Path
import pytest
from app.config import RUNTIME

spec = importlib.util.spec_from_file_location('superhot_launcher', Path(__file__).resolve().parents[2] / 'scripts' / 'run.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


@pytest.fixture
def deployment(monkeypatch):
    root = RUNTIME / ('launcher-test-' + uuid.uuid4().hex)
    (root / 'backend').mkdir(parents=True)
    candidate_python = RUNTIME / ('candidate-' + uuid.uuid4().hex) / 'python'
    candidate_python.parent.mkdir()
    candidate_python.touch()
    for name in ('requirements.in', 'requirements.txt'):
        (root / 'backend' / name).write_text('tikhub==2.2.0\n')
    active = root / 'active-python.txt'
    active.write_text(sys.executable)
    monkeypatch.setattr(launcher, 'ROOT', root)
    monkeypatch.setattr(launcher, 'active_file', active)
    monkeypatch.setattr(launcher, 'previous_file', root / 'previous.json')
    starts, stops = [], []
    def start(python):
        starts.append(python)
        return [python + '-api', python + '-worker']
    monkeypatch.setattr(launcher, 'start', start)
    monkeypatch.setattr(launcher, 'stop', lambda children: stops.append(children))
    previous = launcher.snapshot(sys.executable, '2.2.0')
    candidate = {'python': str(candidate_python), 'version': '2.3.0', 'requirements.in': 'tikhub==2.3.0\n', 'requirements.txt': 'tikhub==2.3.0\n'}
    return root, previous, candidate, starts, stops


def test_failed_candidate_health_preserves_previous_release(deployment, monkeypatch):
    root, previous, candidate, starts, stops = deployment
    checks = iter([False, True])
    monkeypatch.setattr(launcher, 'health', lambda expected=None: next(checks))
    children, python, success = launcher.switch_runtime(['old-api', 'old-worker'], previous, candidate)
    assert success is False
    assert python == previous['python']
    assert starts == [candidate['python'], previous['python']]
    assert (root / 'backend/requirements.txt').read_text() == 'tikhub==2.2.0\n'
    assert (root / 'active-python.txt').read_text() == sys.executable
    assert len(stops) == 2


def test_success_commits_lock_and_preserves_rollback_snapshot(deployment, monkeypatch):
    root, previous, candidate, starts, stops = deployment
    monkeypatch.setattr(launcher, 'health', lambda expected=None: True)
    _, python, success = launcher.switch_runtime(['old-api', 'old-worker'], previous, candidate)
    assert success and python == candidate['python']
    assert (root / 'backend/requirements.txt').read_text() == 'tikhub==2.3.0\n'
    assert (root / 'active-python.txt').read_text() == str(Path(candidate['python']).resolve())
    saved = json.loads((root / 'previous.json').read_text())
    assert saved['version'] == '2.2.0'
    assert saved['requirements.txt'] == 'tikhub==2.2.0\n'


def test_activation_failure_restores_manifests_and_old_runtime(deployment, monkeypatch):
    root, previous, candidate, starts, stops = deployment
    monkeypatch.setattr(launcher, 'health', lambda expected=None: True)
    original = launcher.activate
    def failing_activate(release):
        if release['version'] == '2.3.0':
            (root / 'backend/requirements.txt').write_text('partially changed')
            raise OSError('simulated filesystem failure')
        original(release)
    monkeypatch.setattr(launcher, 'activate', failing_activate)
    _, python, success = launcher.switch_runtime(['old-api', 'old-worker'], previous, candidate)
    assert not success and python == previous['python']
    assert (root / 'backend/requirements.txt').read_text() == 'tikhub==2.2.0\n'
    assert (root / 'active-python.txt').read_text() == sys.executable


def test_updater_rejects_interpreters_outside_managed_directory():
    with pytest.raises(ValueError):
        launcher.checked_python(str(Path(__file__).resolve()))
