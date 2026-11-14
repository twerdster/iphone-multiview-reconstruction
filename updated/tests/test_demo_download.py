import hashlib
import io

import pytest

from tools.download_demo import download_one


def record(data):
    return {"name": "photo.jpg", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "source_url": "https://example.invalid/pinned.jpg"}


def test_download_verifies_size_and_hash(tmp_path, monkeypatch):
    data = b"pinned-image-bytes"
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: io.BytesIO(data))
    assert download_one(tmp_path, record(data)) == "downloaded and verified"
    assert (tmp_path / "photo.jpg").read_bytes() == data
    assert download_one(tmp_path, record(data)) == "verified existing"


def test_download_hash_mismatch_leaves_no_partial_file(tmp_path, monkeypatch):
    data = b"pinned-image-bytes"
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: io.BytesIO(b"x"*len(data)))
    with pytest.raises(ValueError, match="mismatch"):
        download_one(tmp_path, record(data))
    assert list(tmp_path.iterdir()) == []


def test_download_preserves_different_existing_file(tmp_path):
    (tmp_path / "photo.jpg").write_bytes(b"user-owned-file")
    with pytest.raises(FileExistsError, match="differs"):
        download_one(tmp_path, record(b"expected"))
    assert (tmp_path / "photo.jpg").read_bytes() == b"user-owned-file"
