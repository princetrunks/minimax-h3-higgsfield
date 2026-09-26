#!/usr/bin/env python3
"""Merge a H3 Studio library snapshot into a new ComfyUI output directory."""

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import uuid
import zipfile


def read_json(path, fallback):
    try:
        with open(path, encoding="utf-8") as stream:
            value = json.load(stream)
        return value if isinstance(value, type(fallback)) else fallback
    except FileNotFoundError:
        return fallback
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Cannot safely merge invalid registry {path}: {exc}")


def valid_name(name):
    return isinstance(name, str) and pathlib.Path(name).name == name \
        and name.startswith("h3_studio_") and name.endswith(".mp4")


def put_json(path, value):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with open(temporary, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comfy-root", required=True, type=pathlib.Path)
    parser.add_argument("--archive", required=True, type=pathlib.Path)
    args = parser.parse_args()
    root = args.comfy_root.resolve()
    if not (root / "main.py").is_file():
        parser.error("ComfyUI main.py not found")
    destination = root / "output" / "video"
    destination.mkdir(parents=True, exist_ok=True)
    copied = skipped = 0
    with zipfile.ZipFile(args.archive) as bundle:
        names = set(bundle.namelist())
        manifest = json.loads(bundle.read("snapshot.json"))
        if manifest.get("kind") != "h3-studio-library" or manifest.get("version") != 1:
            raise SystemExit("Not a supported H3 Studio library snapshot")
        records = manifest.get("files", [])
        if not isinstance(records, list):
            raise SystemExit("Invalid snapshot file list")
        for record in records:
            name = record.get("name") if isinstance(record, dict) else None
            if not valid_name(name) or "video/" + name not in names:
                raise SystemExit("Invalid video entry in library snapshot")
            target = destination / name
            if target.is_symlink():
                raise SystemExit("Refusing to overwrite a symlink: " + name)
            temporary = destination / ("." + name + "." + uuid.uuid4().hex + ".tmp")
            try:
                with bundle.open("video/" + name) as source, temporary.open("wb") as output:
                    shutil.copyfileobj(source, output)
                if temporary.stat().st_size != record.get("bytes"):
                    raise SystemExit("Size mismatch in snapshot: " + name)
                if target.exists():
                    if digest(target) != digest(temporary):
                        raise SystemExit("Existing video differs; refusing to overwrite: " + name)
                    skipped += 1
                else:
                    os.replace(temporary, target)
                    copied += 1
            finally:
                temporary.unlink(missing_ok=True)

        meta_path = destination / ".h3-studio-metadata.json"
        kept_path = destination / ".h3-studio-kept.json"
        metadata = read_json(meta_path, {})
        kept = set(read_json(kept_path, []))
        if "video/.h3-studio-metadata.json" in names:
            prior = json.loads(bundle.read("video/.h3-studio-metadata.json"))
            if not isinstance(prior, dict):
                raise SystemExit("Invalid metadata registry in snapshot")
            for name, value in prior.items():
                if valid_name(name) and (destination / name).is_file() and isinstance(value, dict):
                    metadata.setdefault(name, value)
        if "video/.h3-studio-kept.json" in names:
            prior = json.loads(bundle.read("video/.h3-studio-kept.json"))
            if not isinstance(prior, list):
                raise SystemExit("Invalid pinned registry in snapshot")
            kept.update(name for name in prior if valid_name(name) and (destination / name).is_file())
        put_json(meta_path, metadata)
        put_json(kept_path, sorted(kept))
    print(f"LIBRARY_RESTORE_OK copied={copied} already_present={skipped}")


if __name__ == "__main__":
    main()
