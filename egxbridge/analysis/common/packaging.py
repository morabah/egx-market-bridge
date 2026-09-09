from __future__ import annotations

from typing import Any
from pathlib import Path
import json
import zipfile
import shutil
import tempfile

from .models import HandoffManifest, utc_now


def write_json(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_jsonl(path: Path, rows: list[Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(r, ensure_ascii=False, default=str) for r in (rows or [])]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def copy_file(src: Path, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def zip_directory(src_dir: Path, zip_path: Path, arc_root: str | None = None):
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    root_name = arc_root or src_dir.name
    with tempfile.NamedTemporaryFile(dir=zip_path.parent, suffix=".zip.tmp", delete=False) as tmp:
        temporary = Path(tmp.name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(src_dir.rglob("*")):
                if f.is_file() and f not in {temporary, zip_path}:
                    zf.write(f, arcname=str(Path(root_name) / f.relative_to(src_dir)))
        temporary.replace(zip_path)
    finally:
        temporary.unlink(missing_ok=True)
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
