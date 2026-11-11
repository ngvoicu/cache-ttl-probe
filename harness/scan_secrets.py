#!/usr/bin/env python3
"""Check a results folder for credentials before it is committed. Exits 1 when anything is found.

    python3 harness/scan_secrets.py results/<run folder> && git add results/<run folder>

It collects every secret-looking value this machine uses for the measurements (the client's key file, the
management key file, key and token fields of the CLIProxyAPI config, every string in the login files) and looks
for them in the folder, plus the usual token shapes and e-mail addresses. Values are never printed.

Model names are not secrets: the names and aliases in a login's `model_aliases` are skipped, because a run that
measured `devin/some-model` necessarily contains that name.
"""
import glob
import json
import os
import re
import sys

HOME = os.path.expanduser("~")
CLIENT_KEYS = os.environ.get("SCAN_CLIENT_KEYS", HOME + "/.pi/agent/cliproxyapi.json")
KEYS_FILE = os.environ.get("SCAN_KEYS_FILE", HOME + "/.cli-proxy-api/keys.txt")
CONFIG = os.environ.get("SCAN_CONFIG", "/opt/homebrew/etc/cliproxyapi.conf")
LOGINS = os.environ.get("SCAN_LOGINS", HOME + "/.cli-proxy-api/*.json")
TOKEN_SHAPES = re.compile(r"(sk-[A-Za-z0-9_-]{20,}|Bearer [A-Za-z0-9._-]{20,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,})")
EMAIL = re.compile(r"[\w.+-]+@(gmail|outlook|hotmail|yahoo|icloud|proton)\.[a-z.]+", re.I)


def collect():
    secrets = set()

    def add(value):
        if isinstance(value, str) and len(value) >= 16 and " " not in value and not value.startswith(("http", "/", "~")) \
                and not value.endswith(".json") and not re.fullmatch(r"[\w.+-]+@[\w.-]+", value) \
                and not re.fullmatch(r"\d{4}-\d\d-\d\dT[\d:.+Z-]+", value):
            secrets.add(value)

    def walk(node, path=""):
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for value in node:
                walk(value, path + "[]")
        elif not re.search(r"model_aliases\[\]\.(name|alias)$|excluded_models\[\]$", path):
            add(node)

    if os.path.exists(CLIENT_KEYS):
        walk(json.load(open(CLIENT_KEYS)))
    if os.path.exists(KEYS_FILE):
        for line in open(KEYS_FILE):
            if "=" in line:
                add(line.split("=", 1)[1].strip())
    if os.path.exists(CONFIG):
        # key, token, secret and password fields, without needing a YAML parser
        for m in re.finditer(r"^\s*-?\s*[\w-]*(key|token|secret|password)[\w-]*:\s*[\"']?([^\"'\s#]+)", open(CONFIG).read(), re.I | re.M):
            add(m.group(2))
    for path in glob.glob(LOGINS):
        try:
            walk(json.load(open(path)))
        except (ValueError, OSError):
            pass
    return secrets


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    secrets = collect()
    hits = files = 0
    for folder in sys.argv[1:]:
        for root, dirs, names in os.walk(folder):
            dirs[:] = [d for d in dirs if d != "logs"]  # logs are never committed
            for name in names:
                path = os.path.join(root, name)
                files += 1
                text = open(path, errors="ignore").read()
                found = []
                if any(s in text for s in secrets):
                    found.append("a credential used on this machine")
                if TOKEN_SHAPES.search(text):
                    found.append("something shaped like a token")
                if EMAIL.search(text):
                    found.append("an e-mail address")
                if found:
                    hits += 1
                    print(f"{path}: {', '.join(found)}")
    print(f"{files} files scanned against {len(secrets)} credentials: {'CLEAN' if not hits else str(hits) + ' file(s) with findings'}")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
