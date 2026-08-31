from brasileirao_scripts import update_h9_fixtures as job


def test_refresh_stops_at_first_failed_step(monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return type("Result", (), {"returncode": 7 if len(calls) == 2 else 0})()

    monkeypatch.setattr(job.subprocess, "run", run)
    assert job.main() == 7
    assert calls == [job.STEPS[0][1], job.STEPS[1][1]]


def test_refresh_runs_all_steps(monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr(job.subprocess, "run", run)
    assert job.main() == 0
    assert calls == [step[1] for step in job.STEPS]
