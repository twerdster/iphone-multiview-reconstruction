import io
import zipfile

import pytest
from PIL import Image

from multiview.inputs import InputError, directory_entries, prepare_images, zip_entries


def photo(value=0, size=(160, 128)):
    image = Image.new("RGB", size, (value, 30, 80))
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def entries():
    return [(f"photo{i}.png", photo(i*20)) for i in range(3)]


def test_normalizes_names_metadata_and_hashes(tmp_path):
    records = prepare_images([(f"../../{n}", d) for n, d in entries()], tmp_path / "images")
    assert [r["name"] for r in records] == ["image-000.jpg", "image-001.jpg", "image-002.jpg"]
    assert len(records[0]["input_sha256"]) == 64
    assert records[0]["original_name"] == "photo0.png"
    assert (tmp_path / "inputs.json").exists()
    assert Image.open(tmp_path / "images/image-000.jpg").getexif() == {}


def test_duplicate_content_does_not_fake_three_views(tmp_path):
    with pytest.raises(InputError, match="three distinct"):
        prepare_images([("one.png", photo()), ("two.png", photo()), ("three.png", photo())], tmp_path / "images")
    assert not (tmp_path / "images").exists()


@pytest.mark.parametrize("name,data,match", [("one.heic", photo(), "JPEG or PNG"), ("one.png", b"not an image", "Unreadable"), ("one.png", photo(size=(40, 40)), "128 pixels")])
def test_bad_images_fail_cleanly(tmp_path, name, data, match):
    with pytest.raises(InputError, match=match):
        prepare_images([(name, data)], tmp_path / "images")
    assert not (tmp_path / "images").exists()


def make_zip(items):
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w") as archive:
        for name, data in items:
            archive.writestr(name, data)
    result.seek(0)
    return result


def test_zip_never_extracts_paths_and_skips_metadata(tmp_path):
    source = make_zip([("photos/"+n, d) for n, d in entries()] + [("README.txt", b"metadata"), ("__MACOSX/._image.png", b"apple"), ("photos/._one.png", b"apple")])
    records = prepare_images(zip_entries(source), tmp_path / "images")
    assert len(records) == 3
    assert not (tmp_path / "photos").exists()


@pytest.mark.parametrize("name", ["../escape.png", "/absolute.png", "folder\\escape.png"])
def test_zip_traversal_rejected(name):
    with pytest.raises(InputError, match="unsafe"):
        list(zip_entries(make_zip([(name, photo())])))


def test_corrupt_zip_rejected():
    with pytest.raises(InputError, match="ZIP is invalid"):
        list(zip_entries(io.BytesIO(b"broken")))


def test_import_skips_appledouble_and_symlinks(tmp_path):
    (tmp_path / "normal.png").write_bytes(photo())
    (tmp_path / "._normal.png").write_bytes(b"not an image")
    (tmp_path / "linked.png").symlink_to(tmp_path / "normal.png")
    assert [n for n, _ in directory_entries(tmp_path)] == ["normal.png"]
