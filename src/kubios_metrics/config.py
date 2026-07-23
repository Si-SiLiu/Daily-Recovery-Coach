import json
from functools import lru_cache
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
SOURCES_PATH = BASE_DIR / "config" / "kubios_data_sources.json"
METRICS_PATH = BASE_DIR / "config" / "kubios_core_metrics.json"


@lru_cache(maxsize=4)
def load_source_config(path=SOURCES_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data.get("source_priority", [])
    names = [row.get("source_type") for row in rows]
    if not rows or len(names) != len(set(names)):
        raise ValueError("kubios_source_priority_invalid")
    return data


@lru_cache(maxsize=4)
def load_metric_config(path=METRICS_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    metrics = data.get("metrics", [])
    names = [row.get("internal_name") for row in metrics]
    if not metrics or len(names) != len(set(names)):
        raise ValueError("kubios_core_metrics_invalid")
    return data


def source_priority(source_type, config=None):
    config = config or load_source_config()
    for row in config["source_priority"]:
        if row["source_type"] == source_type:
            return int(row["priority"])
    return 999


def metric_definitions(config=None):
    return {row["internal_name"]: row for row in (config or load_metric_config())["metrics"]}
