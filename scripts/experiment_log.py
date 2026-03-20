"""Experiment log management with pruning and cap enforcement."""

import json
from datetime import datetime, timezone
from pathlib import Path


def _is_kept_outcome(entry: dict) -> bool:
    return entry.get("outcome") in {"keep", "kept"}


def _entry_summary_text(entry: dict) -> str:
    return (
        entry.get("lessons")
        or entry.get("change_summary")
        or entry.get("notes")
        or entry.get("reason")
        or entry.get("hypothesis")
        or ""
    )


def create_empty_log(log_path: Path) -> None:
    log_path.write_text(json.dumps({"entries": []}, indent=2))


def read_log(log_path: Path) -> dict:
    return json.loads(log_path.read_text())


def add_entry(log_path: Path, entry: dict) -> None:
    data = read_log(log_path)
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    data["entries"].append(entry)
    log_path.write_text(json.dumps(data, indent=2))


def prune_log(log_path: Path, max_discarded: int = 50, max_kept_detailed: int = 30) -> None:
    data = read_log(log_path)
    kept, discarded = [], []
    for e in data["entries"]:
        (kept if _is_kept_outcome(e) else discarded).append(e)

    if len(discarded) > max_discarded:
        discarded = discarded[-max_discarded:]

    if len(kept) > max_kept_detailed:
        to_summarize = kept[: len(kept) - max_kept_detailed]
        kept = kept[len(kept) - max_kept_detailed:]
        summaries = data.get("lessons_summary", [])
        for entry in to_summarize:
            summaries.append(f"iter {entry['iteration']}: {_entry_summary_text(entry)}")
        # Cap summaries to prevent unbounded growth
        max_summaries = max_discarded + max_kept_detailed
        if len(summaries) > max_summaries:
            summaries = summaries[-max_summaries:]
        data["lessons_summary"] = summaries

    data["entries"] = kept + discarded
    log_path.write_text(json.dumps(data, indent=2))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Experiment log management")
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Create empty log")
    init_cmd.add_argument("--log-path", required=True)

    add_cmd = sub.add_parser("add", help="Add entry to log")
    add_cmd.add_argument("--log-path", required=True)
    add_cmd.add_argument("--entry", required=True, help="JSON entry")

    prune_cmd = sub.add_parser("prune", help="Prune log to enforce caps")
    prune_cmd.add_argument("--log-path", required=True)
    prune_cmd.add_argument("--max-discarded", type=int, default=50)
    prune_cmd.add_argument("--max-kept-detailed", type=int, default=30)

    read_cmd = sub.add_parser("read", help="Read and print log")
    read_cmd.add_argument("--log-path", required=True)

    args = parser.parse_args()

    if args.command == "init":
        create_empty_log(Path(args.log_path))
        print('{"status": "created"}')
    elif args.command == "add":
        entry = json.loads(args.entry)
        add_entry(Path(args.log_path), entry)
        print('{"status": "added"}')
    elif args.command == "prune":
        prune_log(Path(args.log_path), args.max_discarded, args.max_kept_detailed)
        print('{"status": "pruned"}')
    elif args.command == "read":
        data = read_log(Path(args.log_path))
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
