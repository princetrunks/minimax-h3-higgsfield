#!/usr/bin/env python3
"""Snapshot completed H3 Studio videos and their settings/timing metadata."""

import argparse
import datetime
import json
import pathlib
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comfy-root", required=True, type=pathlib.Path)
    parser.add_argument("--archive", required=True, type=pathlib.Path)
    args = parser.parse_args()
    video = args.comfy_root.resolve() / "output" / "video"
    if not video.is_dir():
        parser.error(f"Video output directory not found: {video}")
    names = sorted(p for p in video.glob("h3_studio_*.mp4") if p.is_file() and not p.is_symlink())
    args.archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.archive, "w", zipfile.ZIP_STORED) as bundle:
        for path in names:
            bundle.write(path, "video/" + path.name)
        for name in (".h3-studio-metadata.json", ".h3-studio-kept.json"):
            path = video / name
            if path.is_file():
                if name == ".h3-studio-metadata.json":
                    metadata = json.loads(path.read_text(encoding="utf-8"))
                    if not isinstance(metadata, dict):
                        raise SystemExit("Invalid H3 metadata registry")
                    for item in metadata.values():
                        if isinstance(item, dict) and isinstance(item.get("sample_key"), str):
                            _, separator, rest = item["sample_key"].partition("|")
                            if separator:
                                item["sample_key"] = "restored-server|" + rest
                    bundle.writestr("video/" + name, json.dumps(metadata, ensure_ascii=False))
                else:
                    bundle.write(path, "video/" + name)
        bundle.writestr("snapshot.json", json.dumps({
            "kind": "h3-studio-library", "version": 1,
            "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "video_count": len(names),
            "files": [{"name": p.name, "bytes": p.stat().st_size} for p in names],
        }, indent=2))
    print(f"LIBRARY_BACKUP_OK videos={len(names)} bytes={args.archive.stat().st_size}")


if __name__ == "__main__":
    main()
