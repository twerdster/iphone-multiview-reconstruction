import io
import json

import pytest

from multiview.server import create_app
from test_inputs import entries, make_zip

TOKEN = "test-token-that-is-long-enough"
AUTH = {"Authorization": "Bearer " + TOKEN}


@pytest.fixture
def client(tmp_path):
    return create_app(tmp_path, TOKEN, launch_workers=False).test_client()


def test_static_shell_has_no_remote_script_dependencies(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"/static/viewer.js" in response.data
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer incorrect"}])
def test_jobs_require_token(client, headers):
    assert client.post("/api/jobs", headers=headers).status_code == 401


def test_cross_origin_upload_rejected(client):
    assert client.post("/api/jobs", headers={**AUTH, "Origin": "https://other.example"}).status_code == 403


def test_valid_photo_upload_and_status(client):
    response = client.post("/api/jobs", headers=AUTH, data={"photos": [(io.BytesIO(data), name) for name, data in entries()]})
    assert response.status_code == 202
    job = response.json["job"]
    assert client.get(f"/api/jobs/{job}", headers=AUTH).json["input_images"] == 3
    inputs = client.get(f"/api/jobs/{job}/inputs.json", headers=AUTH).json
    assert len(inputs) == 3
    assert client.get(f"/api/jobs/{job}/worker.log", headers=AUTH).status_code == 404
    assert client.get(f"/api/jobs/{job}/../../inputs.json", headers=AUTH).status_code == 404


def test_zip_upload(client):
    response = client.post("/api/jobs", headers=AUTH, data={"archive": (make_zip(entries()), "photos.zip")})
    assert response.status_code == 202
    assert response.json["input_images"] == 3


def test_invalid_upload_does_not_block_next_job(client):
    assert client.post("/api/jobs", headers=AUTH).status_code == 400
    response = client.post("/api/jobs", headers=AUTH, data={"archive": (make_zip(entries()), "photos.zip")})
    assert response.status_code == 202


def test_unknown_job_and_file_are_not_readable(client):
    assert client.get("/api/jobs/not-a-job", headers=AUTH).status_code == 404
    assert client.get("/api/jobs/" + "a"*24, headers=AUTH).status_code == 404


def test_truncated_multipart_does_not_hold_worker_lock(client):
    response = client.post("/api/jobs", headers=AUTH,
        data={"photos": [(io.BytesIO(data), name) for name, data in entries()]},
        environ_overrides={"CONTENT_LENGTH": "100000"})
    assert response.status_code == 400
    assert client.post("/api/jobs", headers=AUTH,
        data={"archive": (make_zip(entries()), "photos.zip")}).status_code == 202


def test_relative_work_directory_is_resolved(tmp_path, monkeypatch):
    from pathlib import Path
    import threading
    finished = threading.Event()
    captured = []
    class Process:
        def wait(self, timeout):
            return 0
    def fake_popen(command, **kwargs):
        captured.append((command, kwargs))
        finished.set()
        return Process()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("multiview.server.subprocess.Popen", fake_popen)
    app = create_app(Path("relative-runs"), TOKEN, launch_workers=True)
    assert app.test_client().post("/api/jobs", headers=AUTH,
        data={"archive": (make_zip(entries()), "photos.zip")}).status_code == 202
    assert finished.wait(2)
    command, arguments = captured[0]
    worker_input = Path(command[3])
    assert worker_input.is_absolute()
    assert (worker_input / "inputs.json").is_file()
    assert Path(arguments["cwd"]) != tmp_path


@pytest.mark.parametrize("failure", ["exit", "timeout"])
def test_native_worker_failure_is_reported_and_releases_job(tmp_path, monkeypatch, failure):
    import subprocess
    class ImmediateThread:
        def __init__(self, target, args, **_):
            self.target, self.args = target, args
        def start(self):
            self.target(*self.args)
    class Process:
        terminated = False
        def wait(self, timeout):
            if failure == "timeout" and not self.terminated:
                raise subprocess.TimeoutExpired("test-worker", timeout)
            return -11 if failure == "exit" else 0
        def terminate(self):
            self.terminated = True
    monkeypatch.setattr("multiview.server.threading.Thread", ImmediateThread)
    monkeypatch.setattr("multiview.server.subprocess.Popen", lambda *a, **kw: Process())
    client = create_app(tmp_path, TOKEN, launch_workers=True, timeout=1).test_client()
    response = client.post("/api/jobs", headers=AUTH,
        data={"archive": (make_zip(entries()), "photos.zip")})
    assert response.status_code == 202
    status = client.get(f"/api/jobs/{response.json['job']}", headers=AUTH).json
    assert status["state"] == "failed"
    assert ("exceeded" if failure == "timeout" else "worker failed") in status["message"]
    assert client.post("/api/jobs", headers=AUTH,
        data={"archive": (make_zip(entries()), "photos.zip")}).status_code == 202


def test_server_shutdown_terminates_its_worker_and_reports_failure(tmp_path, monkeypatch):
    import threading
    started, terminated = threading.Event(), threading.Event()
    class Process:
        def wait(self, timeout=None):
            started.set()
            assert terminated.wait(3)
            return -15
        def poll(self):
            return -15 if terminated.is_set() else None
        def terminate(self):
            terminated.set()
    monkeypatch.setattr("multiview.server.subprocess.Popen", lambda *a, **kw: Process())
    app = create_app(tmp_path, TOKEN)
    client = app.test_client()
    response = client.post("/api/jobs", headers=AUTH,
        data={"archive": (make_zip(entries()), "photos.zip")})
    assert response.status_code == 202 and started.wait(2)
    app.extensions["multiview_stop_workers"]()
    assert terminated.is_set()
    status = client.get(f"/api/jobs/{response.json['job']}", headers=AUTH).json
    assert status["state"] == "failed"
    assert client.post("/api/jobs", headers=AUTH).status_code == 503


def test_completed_result_survives_worker_shutdown_exit_code(tmp_path, monkeypatch):
    from pathlib import Path
    from multiview.reconstruction import write_json
    class ImmediateThread:
        def __init__(self, target, args, **_):
            self.target, self.args = target, args
        def start(self):
            self.target(*self.args)
    class Process:
        def wait(self, timeout):
            return -15
    def launch(command, **_):
        write_json(Path(command[3]) / "status.json", {"state": "complete", "summary": {"output_points": 30}})
        return Process()
    monkeypatch.setattr("multiview.server.threading.Thread", ImmediateThread)
    monkeypatch.setattr("multiview.server.subprocess.Popen", launch)
    client = create_app(tmp_path, TOKEN).test_client()
    response = client.post("/api/jobs", headers=AUTH,
        data={"archive": (make_zip(entries()), "photos.zip")})
    status = client.get(f"/api/jobs/{response.json['job']}", headers=AUTH).json
    assert status["state"] == "complete"


def test_shutdown_marks_a_queued_job_failed_before_worker_launch(tmp_path, monkeypatch):
    class DeferredThread:
        def __init__(self, **_):
            pass
        def start(self):
            pass
    monkeypatch.setattr("multiview.server.threading.Thread", DeferredThread)
    app = create_app(tmp_path, TOKEN)
    client = app.test_client()
    response = client.post("/api/jobs", headers=AUTH,
        data={"archive": (make_zip(entries()), "photos.zip")})
    assert response.status_code == 202
    app.extensions["multiview_stop_workers"]()
    assert client.get(f"/api/jobs/{response.json['job']}", headers=AUTH).json["state"] == "failed"


def test_upload_finishing_after_shutdown_cannot_requeue_job(tmp_path, monkeypatch):
    from multiview.inputs import prepare_images
    app = create_app(tmp_path, TOKEN)
    def prepare_then_stop(*args, **kwargs):
        result = prepare_images(*args, **kwargs)
        app.extensions["multiview_stop_workers"]()
        return result
    monkeypatch.setattr("multiview.server.prepare_images", prepare_then_stop)
    response = app.test_client().post("/api/jobs", headers=AUTH,
        data={"archive": (make_zip(entries()), "photos.zip")})
    assert response.status_code == 503
    status = json.loads(next(tmp_path.glob("*/status.json")).read_text())
    assert status["state"] == "failed"
