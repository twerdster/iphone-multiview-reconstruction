"""Bounded image/ZIP import. Input files are never extracted by their names."""
from __future__ import annotations

import hashlib
import io
import json
import warnings
import zipfile
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGES = 80
MAX_IMAGE_BYTES = 24 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_PIXELS = 40_000_000
EXTENSIONS = {".jpg", ".jpeg", ".png"}
Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class InputError(ValueError):
    pass


def prepare_images(entries, target: Path, max_size: int = 1600):
    """Normalize orientation and size; discard metadata, paths and duplicate images."""
    target.mkdir(parents=True, exist_ok=False)
    records, total, hashes = [], 0, set()
    try:
        for name, data in entries:
            if len(records) >= MAX_IMAGES:
                raise InputError(f"At most {MAX_IMAGES} photographs are supported")
            if Path(name).suffix.lower() not in EXTENSIONS:
                raise InputError("Use JPEG or PNG photographs; export HEIC as JPEG first")
            total += len(data)
            if not data or len(data) > MAX_IMAGE_BYTES or total > MAX_TOTAL_BYTES:
                raise InputError("Image collection exceeds the upload size limit")
            digest = hashlib.sha256(data).hexdigest()
            if digest in hashes:
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(io.BytesIO(data)) as image:
                        if image.format not in {"JPEG", "PNG"}:
                            raise InputError("File content must be JPEG or PNG")
                        if image.width * image.height > MAX_PIXELS:
                            raise InputError("Photograph exceeds the 40 megapixel limit")
                        image = ImageOps.exif_transpose(image).convert("RGB")
                        if min(image.size) < 128:
                            raise InputError("Photographs must be at least 128 pixels on each side")
                        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                        filename = f"image-{len(records):03d}.jpg"
                        image.save(target / filename, quality=94)
                        size = image.size
            except (UnidentifiedImageError, OSError, Image.DecompressionBombError,
                    Image.DecompressionBombWarning) as exc:
                raise InputError("Unreadable or oversized image") from exc
            hashes.add(digest)
            records.append({"name": filename, "original_name": Path(name).name,
                            "input_sha256": digest, "width": size[0], "height": size[1],
                            "normalized_sha256": hashlib.sha256((target / filename).read_bytes()).hexdigest()})
        if len(records) < 3:
            raise InputError("Provide at least three distinct overlapping photographs")
    except Exception:
        for p in target.iterdir():
            p.unlink()
        target.rmdir()
        raise
    (target.parent / "inputs.json").write_text(json.dumps(records, indent=2) + "\n")
    return records


def zip_entries(source):
    """Yield bounded image members without following archive paths or symlinks."""
    try:
        with zipfile.ZipFile(source) as archive:
            members = [m for m in archive.infolist() if not m.is_dir()
                       and not m.filename.startswith("__MACOSX/") and not Path(m.filename).name.startswith("._")]
            if len(members) > MAX_IMAGES:
                raise InputError(f"ZIP contains more than {MAX_IMAGES} files")
            if sum(m.file_size for m in members) > MAX_TOTAL_BYTES:
                raise InputError("ZIP expands beyond the size limit")
            for member in members:
                parts = Path(member.filename).parts
                if (member.filename.startswith(("/", "\\")) or ".." in parts
                        or "\\" in member.filename or (member.external_attr >> 16) & 0o170000 == 0o120000):
                    raise InputError("ZIP contains an unsafe path or symbolic link")
                if member.file_size > MAX_IMAGE_BYTES:
                    raise InputError("ZIP image exceeds the size limit")
                if Path(member.filename).suffix.lower() not in EXTENSIONS:
                    # Common dataset archives contain metadata. Ignore it, never execute it.
                    continue
                yield member.filename, archive.read(member)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise InputError("ZIP is invalid or uses unsupported encryption/compression") from exc


def directory_entries(source: Path):
    for path in sorted(source.iterdir()):
        if path.is_file() and not path.is_symlink() and not path.name.startswith("._") and path.suffix.lower() in EXTENSIONS:
            if path.stat().st_size > MAX_IMAGE_BYTES:
                raise InputError("Image exceeds the size limit")
            yield path.name, path.read_bytes()
