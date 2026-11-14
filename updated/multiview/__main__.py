import argparse
import json
import os
from pathlib import Path

from .inputs import directory_entries, prepare_images, zip_entries


def main():
    parser = argparse.ArgumentParser(description="Reconstruct overlapping photographs with CPU COLMAP")
    parser.add_argument("source", type=Path, help="Photo directory or ZIP (ignored with --prepared)")
    parser.add_argument("output", type=Path, help="New output workspace")
    parser.add_argument("--sparse-only", action="store_true")
    parser.add_argument("--prepared", action="store_true", help="Use an already normalized workspace (server worker)")
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.threads <= 16:
        parser.error("--threads must be between 1 and 16")
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ[variable] = str(args.threads)
    from .reconstruction import reconstruct, write_json
    if not args.prepared:
        args.output.mkdir(parents=True, exist_ok=False)
        entries = directory_entries(args.source) if args.source.is_dir() else zip_entries(args.source)
        prepare_images(entries, args.output / "images")
    try:
        print(json.dumps(reconstruct(args.output, dense=not args.sparse_only, threads=args.threads), indent=2))
    except Exception as exc:
        write_json(args.output / "status.json", {"state": "failed", "stage": "failed", "message": str(exc)})
        raise


if __name__ == "__main__":
    main()
