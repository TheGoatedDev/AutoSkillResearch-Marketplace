"""Bump patch version in plugin.json."""

import json
from pathlib import Path


def bump_patch(plugin_json_path: Path) -> str:
    data = json.loads(plugin_json_path.read_text())
    version = data.get("version", "1.0.0")
    parts = version.split(".")
    parts[2] = str(int(parts[2]) + 1)
    new_version = ".".join(parts)
    data["version"] = new_version
    plugin_json_path.write_text(json.dumps(data, indent=2))
    return new_version


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Bump patch version")
    parser.add_argument("--plugin-json", required=True, help="Path to plugin.json")
    args = parser.parse_args()
    new_version = bump_patch(Path(args.plugin_json))
    print(json.dumps({"version": new_version}))


if __name__ == "__main__":
    main()
