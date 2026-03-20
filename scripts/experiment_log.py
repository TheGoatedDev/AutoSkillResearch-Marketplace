"""Experiment log management with pruning and cap enforcement."""

import json
from datetime import datetime, timezone
from pathlib import Path


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
    entries = data["entries"]
    kept = [e for e in entries if e["outcome"] == "kept"]
    discarded = [e for e in entries if e["outcome"] != "kept"]

    if len(discarded) > max_discarded:
        discarded = discarded[-max_discarded:]

    if len(kept) > max_kept_detailed:
        to_summarize = kept[: len(kept) - max_kept_detailed]
        kept = kept[len(kept) - max_kept_detailed:]
        summaries = data.get("lessons_summary", [])
        for entry in to_summarize:
            summaries.append(f"iter {entry['iteration']}: {entry.get('lessons', entry.get('change_summary', ''))}")
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
