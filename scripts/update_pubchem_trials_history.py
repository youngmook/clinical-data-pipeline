#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_row_count(path: Path) -> int:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(obj, list):
        return len(obj)
    return 1


def _read_state(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_state(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_snapshot_timestamp(path: Path) -> datetime | None:
    name = path.name
    if not (name.startswith("trials_") and name.endswith(".json")):
        return None
    token = name[len("trials_") : -len(".json")]
    try:
        return datetime.strptime(token, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _prune_old_snapshots(history_dir: Path, now_ts: datetime, retention_days: int) -> int:
    if retention_days < 0 or not history_dir.exists():
        return 0
    cutoff = now_ts - timedelta(days=retention_days)
    deleted = 0
    for p in history_dir.glob("trials_*.json"):
        snap_ts = _parse_snapshot_timestamp(p)
        if snap_ts is None:
            continue
        if snap_ts < cutoff:
            p.unlink(missing_ok=True)
            deleted += 1
    return deleted


def main() -> int:
    p = argparse.ArgumentParser(prog="update-pubchem-trials-history")
    p.add_argument("--trials-file", required=True, help="Newly collected trials.json path")
    p.add_argument("--state-file", default="snapshots/pubchem_trials/collection_state.json")
    p.add_argument("--latest-file", default="snapshots/pubchem_trials/latest/trials.json")
    p.add_argument("--history-dir", default="snapshots/pubchem_trials/history")
    p.add_argument("--timestamp", default=None, help="UTC timestamp override (ISO8601)")
    p.add_argument(
        "--retention-days",
        type=int,
        default=365,
        help="Delete snapshot files older than this many days (default: 365, negative to disable)",
    )
    p.add_argument("--changed-flag-path", default=None, help="Write 'true' or 'false' for workflow")
    p.add_argument(
        "--snapshot-on-change",
        action="store_true",
        help="Save history snapshot only when file content changed (default: snapshot every collection run)",
    )
    args = p.parse_args()

    trials_file = Path(args.trials_file)
    if not trials_file.exists():
        raise FileNotFoundError(f"trials file not found: {trials_file}")

    state_file = Path(args.state_file)
    latest_file = Path(args.latest_file)
    history_dir = Path(args.history_dir)

    ts = args.timestamp or _now_utc_iso()
    safe_ts = ts.replace(":", "").replace("-", "")
    now_dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)

    new_checksum = _checksum(trials_file)
    new_rows = _json_row_count(trials_file)

    prev = _read_state(state_file)
    prev_checksum = prev.get("latest_checksum")
    changed = not latest_file.exists() or new_checksum != prev_checksum

    latest_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(trials_file, latest_file)

    should_snapshot = changed if args.snapshot_on_change else True
    snapshot_path = None
    if should_snapshot:
        history_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = history_dir / f"trials_{safe_ts}.json"
        shutil.copy2(trials_file, snapshot_path)

    deleted_snapshots = _prune_old_snapshots(history_dir, now_dt, args.retention_days)

    history_files = sorted(history_dir.glob("trials_*.json")) if history_dir.exists() else []

    state = {
        "schema_version": 1,
        "last_collected_at": ts,
        "last_changed_at": ts if changed else prev.get("last_changed_at", ts),
        "latest_file": str(latest_file),
        "latest_checksum": new_checksum,
        "latest_row_count": new_rows,
        "history_count": len(history_files),
        "last_pruned_count": deleted_snapshots,
        "latest_snapshot": str(snapshot_path) if snapshot_path else prev.get("latest_snapshot", ""),
    }
    _write_state(state_file, state)

    if args.changed_flag_path:
        flag_path = Path(args.changed_flag_path)
        flag_path.parent.mkdir(parents=True, exist_ok=True)
        flag_path.write_text("true\n" if changed else "false\n", encoding="utf-8")

    print(f"changed: {str(changed).lower()}")
    print(f"latest: {latest_file}")
    print(f"state: {state_file}")
    if snapshot_path:
        print(f"snapshot: {snapshot_path}")
    print(f"pruned_snapshots: {deleted_snapshots}")
    print(f"rows: {new_rows}")
    print(f"checksum: {new_checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
