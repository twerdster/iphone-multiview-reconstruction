"""Local single-worker reconstruction service; no accounts or external services."""
from __future__ import annotations

import argparse
import hmac
import io
import json
import os
import re
import secrets
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file, send_from_directory
from werkzeug.exceptions import HTTPException

from .inputs import InputError, MAX_TOTAL_BYTES, prepare_images, zip_entries
from .reconstruction import write_json

JOB_PATTERN = re.compile(r"^[a-f0-9]{24}$")
EXPORTS = {"result.ply", "sparse.ply", "stereo.ply", "summary.json", "inputs.json", "cloud.json", "cameras.json", "sparse-cloud.json"}


def create_app(work_dir: Path, token: str, launch_workers=True, timeout=900):
    work_dir = work_dir.expanduser().resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    app = Flask(__name__, static_folder="web", static_url_path="/static")
    app.config["MAX_CONTENT_LENGTH"] = MAX_TOTAL_BYTES
    app.config["MAX_FORM_PARTS"] = 100
    lock, busy = threading.Lock(), {"job": None}
    children, stopping = {}, threading.Event()

    def stop_workers():
        stopping.set()
        with lock:
            active = list(children.items())
            queued_path = work_dir / busy["job"] if busy["job"] else None
        for process, path in active:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            status = json.loads((path / "status.json").read_text()) if (path / "status.json").exists() else {}
            if status.get("state") != "complete":
                write_json(path / "status.json", {"state": "failed", "stage": "failed", "message": "Server stopped during reconstruction; start a new run"})
        if queued_path and queued_path.is_dir():
            status = json.loads((queued_path / "status.json").read_text()) if (queued_path / "status.json").exists() else {}
            if status.get("state") not in {"failed", "complete"}:
                write_json(queued_path / "status.json", {"state": "failed", "stage": "failed", "message": "Server stopped before reconstruction completed; start a new run"})
    app.extensions["multiview_stop_workers"] = stop_workers

    @app.before_request
    def authenticate():
        if request.path.startswith("/api/"):
            supplied = request.headers.get("Authorization", "")
            if not hmac.compare_digest(supplied.encode(), ("Bearer " + token).encode()):
                abort(401)
            # Even with a leaked token, a different website cannot submit through a browser.
            origin = request.headers.get("Origin")
            if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
                abort(403)

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' blob: data:; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        return response

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    def job_path(identifier):
        if not JOB_PATTERN.fullmatch(identifier):
            abort(404)
        path = work_dir / identifier
        if not path.is_dir():
            abort(404)
        return path

    def worker(path):
        process = None
        try:
            if stopping.is_set():
                raise RuntimeError("Server is stopping")
            with (path / "worker.log").open("wb") as log:
                with lock:
                    if stopping.is_set():
                        raise RuntimeError("Server is stopping")
                    process = subprocess.Popen([sys.executable, "-m", "multiview", str(path), str(path), "--prepared"],
                                               stdout=log, stderr=subprocess.STDOUT, cwd=Path(__file__).parent.parent)
                    children[process] = path
                try:
                    result = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    raise RuntimeError(f"Reconstruction exceeded the {timeout} second limit")
                if result:
                    status = json.loads((path / "status.json").read_text()) if (path / "status.json").exists() else {}
                    if status.get("state") not in {"failed", "complete"}:
                        raise RuntimeError("Reconstruction worker failed; see the local worker.log")
        except Exception as exc:
            write_json(path / "status.json", {"state": "failed", "stage": "failed", "message": str(exc)})
        finally:
            with lock:
                children.pop(process, None)
                busy["job"] = None

    @app.post("/api/jobs")
    def submit():
        with lock:
            if stopping.is_set():
                return jsonify(error="Server is stopping"), 503
            if busy["job"]:
                return jsonify(error="One reconstruction is already running; wait for it to finish"), 409
            identifier = secrets.token_hex(12)
            busy["job"] = identifier
        path = work_dir / identifier
        worker_started = False
        try:
            path.mkdir()
            if "archive" in request.files:
                archive = request.files["archive"].read(MAX_TOTAL_BYTES + 1)
                if len(archive) > MAX_TOTAL_BYTES:
                    raise InputError("Upload exceeds the size limit")
                records = prepare_images(zip_entries(io.BytesIO(archive)), path / "images")
            else:
                files = request.files.getlist("photos")
                records = prepare_images(((f.filename or "", f.read(24*1024*1024 + 1)) for f in files), path / "images")
            with lock:
                if stopping.is_set():
                    write_json(path / "status.json", {"state": "failed", "stage": "failed", "message": "Server stopped during upload; start a new run"})
                    return jsonify(error="Server is stopping"), 503
                write_json(path / "status.json", {"state": "queued", "stage": "queued", "input_images": len(records)})
            if launch_workers:
                threading.Thread(target=worker, args=(path,), daemon=True).start()
                worker_started = True
            return jsonify(job=identifier, input_images=len(records)), 202
        except HTTPException as exc:
            return jsonify(error="Invalid or oversized multipart upload"), exc.code or 400
        except (InputError, OSError, ValueError) as exc:
            return jsonify(error=str(exc)), 400
        finally:
            if not worker_started:
                with lock:
                    busy["job"] = None

    @app.get("/api/jobs/<identifier>")
    def status(identifier):
        path = job_path(identifier)
        status_path = path / "status.json"
        return jsonify(json.loads(status_path.read_text()) if status_path.exists() else {"state": "queued"})

    @app.get("/api/jobs/<identifier>/<filename>")
    def artifact(identifier, filename):
        path = job_path(identifier)
        if filename not in EXPORTS or not (path / filename).is_file():
            abort(404)
        return send_file(path / filename, as_attachment=filename.endswith(".ply"))

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(error="Upload is larger than 256 MB"), 413

    return app


def main():
    parser = argparse.ArgumentParser(description="Local photo reconstruction server")
    parser.add_argument("--work-dir", type=Path, default=Path.home() / "multiview-runs")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token", default=os.environ.get("MULTIVIEW_TOKEN"))
    args = parser.parse_args()
    token = args.token or secrets.token_urlsafe(24)
    if len(token) < 16:
        parser.error("Token must contain at least 16 characters")
    print(f"Open http://{args.host}:{args.port}/#token={token}", flush=True)
    print("For a phone, use this Mac/Linux machine's LAN address. Keep this server on a trusted local network.", flush=True)
    app = create_app(args.work_dir, token)
    def terminate_server(signum, frame):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, terminate_server)
    try:
        app.run(host=args.host, port=args.port, threaded=True, debug=False)
    finally:
        app.extensions["multiview_stop_workers"]()


if __name__ == "__main__":
    main()
