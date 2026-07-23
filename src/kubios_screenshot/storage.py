import hashlib
from pathlib import Path

from .image_preprocess import preprocess_image, validate_image_bytes
from .models import StoredImage


BASE_DIR = Path(__file__).resolve().parents[2]
IMPORT_ROOT = BASE_DIR / "data" / "imports" / "kubios_screenshots"
ORIGINAL_DIR = IMPORT_ROOT / "original"
PROCESSED_DIR = IMPORT_ROOT / "processed"


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def relative_to_project(path):
    return str(Path(path).resolve().relative_to(BASE_DIR.resolve()))


def find_by_hash(connection, file_sha256):
    try:
        row = connection.execute(
            "SELECT * FROM kubios_screenshot_imports WHERE file_sha256 = ?",
            (file_sha256,),
        ).fetchone()
    except Exception:
        return None
    return dict(row) if row else None


def store_image_bytes(data, filename, connection=None, config=None):
    suffix = validate_image_bytes(data, filename, config)
    digest = sha256_bytes(data)
    if connection is not None:
        existing = find_by_hash(connection, digest)
        if existing:
            return StoredImage(
                digest, existing["original_relative_path"],
                existing.get("processed_relative_path") or "", True,
            )
    ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    original = ORIGINAL_DIR / f"{digest}{suffix}"
    processed = PROCESSED_DIR / f"{digest}.png"
    if not original.exists():
        original.write_bytes(data)
    if not processed.exists():
        preprocess_image(original, processed, config)
    return StoredImage(digest, relative_to_project(original), relative_to_project(processed), False)


def resolve_relative_path(relative_path):
    candidate = (BASE_DIR / relative_path).resolve()
    root = IMPORT_ROOT.resolve()
    if root not in candidate.parents:
        raise ValueError("unsafe_import_path")
    return candidate


def delete_import(connection, import_id, delete_files=False, delete_formal_record=False):
    row = connection.execute(
        "SELECT * FROM kubios_screenshot_imports WHERE id = ?", (import_id,)
    ).fetchone()
    if not row:
        return {"deleted": False, "reason": "not_found"}
    row = dict(row)
    affected_date = row.get("detected_date")
    if delete_formal_record and row.get("imported_record_id"):
        connection.execute(
            "DELETE FROM kubios_morning_hrv_raw WHERE id = ?",
            (row["imported_record_id"],),
        )
    if delete_files:
        for key in ("original_relative_path", "processed_relative_path"):
            value = row.get(key)
            if value:
                path = resolve_relative_path(value)
                if path.is_file():
                    path.unlink()
    connection.execute("DELETE FROM kubios_screenshot_imports WHERE id = ?", (import_id,))
    connection.commit()
    if delete_formal_record and affected_date:
        from src.kubios_import import rebuild_kubios_daily_metrics
        rebuild_kubios_daily_metrics(connection, [affected_date])
    return {
        "deleted": True,
        "formal_record_preserved": not delete_formal_record,
        "files_deleted": bool(delete_files),
    }
