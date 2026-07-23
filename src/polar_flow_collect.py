import argparse
import hashlib
import shutil
import time
from pathlib import Path

try:
    from .db import BASE_DIR, DB_PATH, connect
except ImportError:
    from db import BASE_DIR, DB_PATH, connect


DEFAULT_SOURCE_DIR = Path.home() / "Downloads"
POLAR_FLOW_IMPORT_DIR = BASE_DIR / "data" / "imports" / "polar_flow"
SUPPORTED_EXTENSIONS = {".csv", ".tcx", ".gpx", ".fit", ".json", ".zip"}
TEMP_EXTENSIONS = {".crdownload", ".download", ".part", ".tmp"}


def is_supported_file(path):
    if not path.is_file():
        return False
    if path.suffix.lower() in TEMP_EXTENSIONS:
        return False
    if path.suffix.lower() in SUPPORTED_EXTENSIONS:
        return True
    return False


def is_probably_polar_file(path):
    name = path.name.lower()
    if "polar" in name or "flow" in name or "training" in name or "activity" in name:
        return True
    return path.suffix.lower() in {".tcx", ".gpx", ".fit"}


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_stored_name(path, digest):
    stem = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in path.stem)
    return f"{stem}_{digest[:12]}{path.suffix.lower()}"


def existing_digest(connection, digest):
    row = connection.execute(
        "SELECT id FROM polar_flow_import_files WHERE sha256 = ?",
        (digest,),
    ).fetchone()
    return row is not None


def record_collected_file(connection, source_path, stored_path, digest):
    connection.execute(
        """
        INSERT INTO polar_flow_import_files (
            source_path,
            stored_path,
            filename,
            file_type,
            sha256,
            status
        )
        VALUES (?, ?, ?, ?, ?, 'collected')
        ON CONFLICT(sha256) DO UPDATE SET
            source_path = excluded.source_path,
            stored_path = excluded.stored_path,
            filename = excluded.filename,
            file_type = excluded.file_type,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            str(source_path),
            str(stored_path),
            stored_path.name,
            stored_path.suffix.lower().lstrip("."),
            digest,
        ),
    )
    connection.commit()


def collect_file(connection, source_path, import_dir=POLAR_FLOW_IMPORT_DIR):
    source_path = Path(source_path)
    digest = file_sha256(source_path)
    if existing_digest(connection, digest):
        return {
            "status": "skipped_duplicate",
            "source_path": source_path,
            "stored_path": None,
            "sha256": digest,
        }

    import_dir = Path(import_dir)
    import_dir.mkdir(parents=True, exist_ok=True)
    stored_path = import_dir / safe_stored_name(source_path, digest)
    shutil.copy2(source_path, stored_path)
    record_collected_file(connection, source_path, stored_path, digest)
    return {
        "status": "collected",
        "source_path": source_path,
        "stored_path": stored_path,
        "sha256": digest,
    }


def scan_for_polar_exports(source_dir=DEFAULT_SOURCE_DIR, min_age_seconds=5):
    source_dir = Path(source_dir).expanduser()
    if not source_dir.exists():
        return []

    now = time.time()
    candidates = []
    for path in source_dir.iterdir():
        if not is_supported_file(path):
            continue
        if not is_probably_polar_file(path):
            continue
        if now - path.stat().st_mtime < min_age_seconds:
            continue
        candidates.append(path)
    return sorted(candidates)


def collect_polar_flow_exports(
    source_dir=DEFAULT_SOURCE_DIR,
    import_dir=POLAR_FLOW_IMPORT_DIR,
    connection=None,
    min_age_seconds=5,
):
    owns_connection = connection is None
    connection = connection or connect()
    results = []
    for candidate in scan_for_polar_exports(source_dir, min_age_seconds=min_age_seconds):
        results.append(collect_file(connection, candidate, import_dir=import_dir))

    if owns_connection:
        connection.close()

    return results


def parse_args():
    parser = argparse.ArgumentParser(description="Collect Polar Flow exports from a local folder.")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE_DIR))
    parser.add_argument("--import-dir", default=str(POLAR_FLOW_IMPORT_DIR))
    parser.add_argument("--min-age-seconds", type=int, default=5)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=int, default=30)
    return parser.parse_args()


def print_results(results):
    collected = [item for item in results if item["status"] == "collected"]
    skipped = [item for item in results if item["status"] == "skipped_duplicate"]
    print(f"Collected: {len(collected)}")
    print(f"Skipped duplicates: {len(skipped)}")
    for item in collected:
        print(f"- {item['stored_path']}")


def main():
    args = parse_args()
    print(f"Database: {DB_PATH}")
    print(f"Source: {Path(args.source).expanduser()}")
    print(f"Import dir: {Path(args.import_dir)}")

    if args.watch:
        while True:
            results = collect_polar_flow_exports(
                source_dir=args.source,
                import_dir=args.import_dir,
                min_age_seconds=args.min_age_seconds,
            )
            if results:
                print_results(results)
            time.sleep(args.interval)

    results = collect_polar_flow_exports(
        source_dir=args.source,
        import_dir=args.import_dir,
        min_age_seconds=args.min_age_seconds,
    )
    print_results(results)


if __name__ == "__main__":
    main()
