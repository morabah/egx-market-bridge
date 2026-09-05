from __future__ import annotations

from typing import Any
from pathlib import Path
import json
import zipfile
import shutil

from .models import HandoffManifest, utc_now


def write_json(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_file(src: Path, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def zip_directory(src_dir: Path, zip_path: Path, arc_root: str | None = None):
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    root_name = arc_root or src_dir.name
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(src_dir.rglob("*")):
            if f.is_file():
                zf.write(f, arcname=str(Path(root_name) / f.relative_to(src_dir)))
    return zip_path


def list_files_relative(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())


def finalize_manifest(manifest: HandoffManifest, package_dir: Path) -> dict[str, Any]:
    manifest.included_files = list_files_relative(package_dir)
    if not manifest.generated_at:
        manifest.generated_at = utc_now()
    data = manifest.to_dict()
    write_json(package_dir / "manifest.json", data)
    return data
