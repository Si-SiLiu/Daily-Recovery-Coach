import argparse
from datetime import date, timedelta
from statistics import median

from src.db import connect

from . import DERIVATION_VERSION
from .config import load_source_config
from .storage import upsert_derived
from .trends import consecutive_declines, consecutive_direction, linear_trend


FIELDS = ("rmssd_ms","mean_hr_bpm","sdnn_ms","readiness_percent","pns_index","sns_index","respiratory_rate_bpm","stress_index")


def pct(value, baseline):
    return None if value is None or baseline in (None,0) else (value-baseline)/abs(baseline)*100


def derive_for_date(connection, target_date):
    target=date.fromisoformat(str(target_date)); start=(target-timedelta(days=28)).isoformat()
    rows=[dict(row) for row in connection.execute(
        "SELECT * FROM kubios_hrv_normalized WHERE selected_as_primary=1 AND date BETWEEN ? AND ? ORDER BY date",
        (start,target.isoformat()),).fetchall()]
    current=next((row for row in rows if row["date"]==target.isoformat()),None)
    if not current: return None
    history=[row for row in rows if row["date"]<target.isoformat()]
    baselines={}
    for field in FIELDS:
        values=[row[field] for row in history if row[field] is not None]
        baselines[field]=median(values) if len(values)>=7 else None
    recent=(history+[current])[-7:]
    priority=current.get("source_priority",999)
    reliability=next((row["reliability"] for row in load_source_config()["source_priority"] if row["priority"]==priority),"unknown")
    complete=current.get("core_data_completeness") or 0
    quality="complete" if complete>=80 else ("partial" if complete>=40 else "limited")
    row={
        "date":target.isoformat(),
        "rmssd_vs_baseline_percent":pct(current["rmssd_ms"],baselines["rmssd_ms"]),
        "mean_hr_vs_baseline_percent":pct(current["mean_hr_bpm"],baselines["mean_hr_bpm"]),
        "sdnn_vs_baseline_percent":pct(current["sdnn_ms"],baselines["sdnn_ms"]),
        "readiness_vs_baseline_percent":pct(current["readiness_percent"],baselines["readiness_percent"]),
        "pns_vs_baseline_delta":None if current["pns_index"] is None or baselines["pns_index"] is None else current["pns_index"]-baselines["pns_index"],
        "sns_vs_baseline_delta":None if current["sns_index"] is None or baselines["sns_index"] is None else current["sns_index"]-baselines["sns_index"],
        "respiratory_rate_vs_baseline_percent":pct(current["respiratory_rate_bpm"],baselines["respiratory_rate_bpm"]),
        "stress_index_vs_baseline_percent":pct(current["stress_index"],baselines["stress_index"]),
        "rmssd_7d_trend":linear_trend([r["rmssd_ms"] for r in recent]),
        "mean_hr_7d_trend":linear_trend([r["mean_hr_bpm"] for r in recent]),
        "readiness_7d_trend":linear_trend([r["readiness_percent"] for r in recent]),
        "pns_7d_trend":linear_trend([r["pns_index"] for r in recent]),
        "sns_7d_trend":linear_trend([r["sns_index"] for r in recent]),
        "consecutive_rmssd_below_baseline_days":consecutive_direction(recent,"rmssd_ms",baselines["rmssd_ms"],"below"),
        "consecutive_mean_hr_above_baseline_days":consecutive_direction(recent,"mean_hr_bpm",baselines["mean_hr_bpm"],"above"),
        "consecutive_readiness_decline_days":consecutive_declines(recent,"readiness_percent"),
        "data_quality_status":quality,"source_reliability_status":reliability,
        "derivation_version":DERIVATION_VERSION,
    }
    return row


def rebuild(connection, dates=None, dry_run=False):
    dates=dates or [row[0] for row in connection.execute("SELECT DISTINCT date FROM kubios_hrv_normalized WHERE selected_as_primary=1 ORDER BY date")]
    results=[row for value in dates if (row:=derive_for_date(connection,value))]
    if not dry_run:
        for row in results: upsert_derived(connection,row)
        connection.commit()
    return {"derived_records":len(results),"dry_run":dry_run}


def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("--dry-run",action="store_true"); parser.add_argument("--all",action="store_true"); parser.add_argument("--date",action="append")
    args=parser.parse_args(argv)
    with connect() as connection: result=rebuild(connection,args.date,args.dry_run)
    print(f"derived_records={result['derived_records']} dry_run={str(result['dry_run']).lower()}")


if __name__ == "__main__": main()
