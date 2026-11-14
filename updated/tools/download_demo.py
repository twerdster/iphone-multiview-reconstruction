"""Download 11 pinned, hash-verified Avignon photographs (CC BY-NC 3.0)."""
import argparse
import hashlib
import json
import tempfile
import urllib.request
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024*1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_one(destination, record):
    target = destination / record["name"]
    if target.exists():
        if target.stat().st_size != record["bytes"] or sha256(target) != record["sha256"]:
            raise FileExistsError(f"Existing file differs from the pinned dataset: {target}")
        return "verified existing"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination, prefix=".download-", delete=False) as output:
            temporary = Path(output.name)
            with urllib.request.urlopen(record["source_url"], timeout=45) as response:
                total = 0
                for chunk in iter(lambda: response.read(1024*1024), b""):
                    total += len(chunk)
                    if total > record["bytes"]:
                        raise ValueError("Download exceeds the pinned file size")
                    output.write(chunk)
        if temporary.stat().st_size != record["bytes"] or sha256(temporary) != record["sha256"]:
            raise ValueError(f"Size or SHA-256 mismatch: {record['name']}")
        temporary.replace(target)
        return "downloaded and verified"
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="Image folder; about 152 MiB total")
    args = parser.parse_args()
    manifest = json.loads(Path(__file__).with_name("demo_manifest.json").read_text())
    print(f"{manifest['author']} · {manifest['license']} · {manifest['license_url']}")
    print(f"11 original photographs, {manifest['bytes']:,} bytes. Noncommercial data license; separate from code licensing.")
    args.destination.mkdir(parents=True, exist_ok=True)
    for record in manifest["images"]:
        print(record["name"], download_one(args.destination, record), flush=True)


if __name__ == "__main__":
    main()
