#!/usr/bin/env python3
"""List the hostnames a codebase connects to.

Usage: python3 find_hosts.py [repo-root] [--json] [--all]

Scans source and config files for URL literals and prints each distinct host
with a count and one example location. It only sees literal URLs. Hosts built
at runtime, loaded from remote config, or used by binary SDKs are not found,
so treat the output as a starting list, not a complete one.

By default, a short list of exact hosts that are not app backends (XML schema
and DTD hosts, package registries, documentation sites) and local addresses
are hidden. API hosts of large providers (for example api.github.com or
*.googleapis.com) are never hidden, since apps do call them.
Pass --all to include them.
"""
import json
import os
import re
import sys

SKIP_DIRS = {
    ".git", "node_modules", "Pods", "build", "dist", ".gradle", ".dart_tool",
    "DerivedData", ".idea", ".vscode", "vendor", "Carthage", ".build", "out",
    ".expo", ".next", "__pycache__", ".venv", "venv", "xcuserdata", ".cxx",
    "ephemeral", ".symlinks", "coverage",
}
EXTENSIONS = {
    ".swift", ".m", ".mm", ".h", ".kt", ".kts", ".java", ".dart", ".js", ".jsx",
    ".ts", ".tsx", ".json", ".plist", ".xml", ".yaml", ".yml", ".gradle",
    ".properties", ".env", ".xcconfig", ".strings", ".toml", ".graphql",
}
EXTRA_NAMES = {".env", ".env.production", ".env.development", ".env.staging"}
NOISE = re.compile(
    r"^("
    r"(www\.)?w3\.org|www\.apple\.com|schemas\.android\.com|developer\.android\.com|"
    r"developer\.apple\.com|(www\.)?npmjs\.(org|com)|registry\.npmjs\.org|"
    r"registry\.yarnpkg\.com|repo1?\.maven\.org|repo\.maven\.apache\.org|"
    r"maven\.apache\.org|services\.gradle\.org|plugins\.gradle\.org|(www\.)?jitpack\.io|"
    r"pub\.dev|cdn\.cocoapods\.org|(www\.)?kotlinlang\.org|(docs\.|api\.)?flutter\.dev|"
    r"dart\.dev|reactnative\.dev|docs\.expo\.dev|(www\.)?swift\.org|"
    r"schema\.org|json-schema\.org|json\.schemastore\.org|opensource\.org|"
    r"creativecommons\.org|www\.apache\.org|(www\.)?example\.(com|org|net)|"
    r"stackoverflow\.com|[a-z]+\.wikipedia\.org|docs\.trustpin\.cloud|trustpin\.cloud|"
    r"app\.trustpin\.cloud|github\.com|raw\.githubusercontent\.com|img\.shields\.io|"
    r"dl\.google\.com|maven\.google\.com|fb\.me|aka\.ms|goo\.gl|bit\.ly"
    r")$"
)
LOCAL = re.compile(r"^(localhost|127\.|10\.|192\.168\.|0\.0\.0\.0|\[?::1\]?)")
URL = re.compile(r"\b(https?|wss?)://([A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?)(?::\d+)?", re.I)
MAX_BYTES = 2_000_000


def scan(root):
    hosts = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext not in EXTENSIONS and name not in EXTRA_NAMES:
                continue
            if name in ("package-lock.json", "yarn.lock", "pubspec.lock", "Podfile.lock"):
                continue
            path = os.path.join(dirpath, name)
            try:
                if os.path.getsize(path) > MAX_BYTES:
                    continue
                with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                    for lineno, line in enumerate(fh, 1):
                        for scheme, host in URL.findall(line):
                            host = host.lower()
                            if "." not in host and host != "localhost":
                                continue
                            entry = hosts.setdefault(host, {
                                "host": host, "count": 0, "schemes": set(),
                                "example": f"{os.path.relpath(path, root)}:{lineno}",
                            })
                            entry["count"] += 1
                            entry["schemes"].add(scheme.lower())
            except OSError:
                continue
    return hosts


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    root = args[0] if args else "."
    hosts = scan(root)
    rows = []
    hidden = 0
    for entry in hosts.values():
        host = entry["host"]
        note = ""
        if LOCAL.match(host):
            note = "local"
        elif NOISE.search(host):
            note = "likely not an app backend"
        if note and "--all" not in flags:
            hidden += 1
            continue
        if entry["schemes"] & {"http", "ws"}:
            note = (note + "; " if note else "") + "plain http/ws seen: never pin-validated"
        rows.append({
            "host": host, "count": entry["count"],
            "schemes": sorted(entry["schemes"]), "example": entry["example"], "note": note,
        })
    rows.sort(key=lambda r: (-r["count"], r["host"]))
    if "--json" in flags:
        print(json.dumps({"hosts": rows, "hidden": hidden}, indent=2))
        return
    if not rows:
        print("No hosts found in URL literals.")
    else:
        width = max(len(r["host"]) for r in rows)
        for r in rows:
            line = f"{r['host']:<{width}}  x{r['count']:<4} {r['example']}"
            if r["note"]:
                line += f"  [{r['note']}]"
            print(line)
    if hidden:
        print(f"\n{hidden} host(s) hidden as unlikely app backends. Use --all to list them.")
    print("\nLiteral URLs only. Also check hosts built at runtime or loaded from remote config.")


if __name__ == "__main__":
    main()
