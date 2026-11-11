#!/usr/bin/env python3
"""Check a results folder for credentials before it is committed. Exits 1 when anything is found.

    python3 harness/scan_secrets.py results/<run folder> && git add results/<run folder>

It collects every secret-looking value this machine uses for the measurements (the client's key file, the
management key file, key and token fields of the CLIProxyAPI config, every string in the login files) and looks
for them in the folder, plus the usual token shapes, e-mail addresses, home folder paths and pi session files
(a session file stores pi's whole system prompt, with the names and paths of the owner's skills; they stay local). Values are never printed: a finding names
the file and the field the value came from, so it can be judged.

Model names are not secrets: model lists and the names in a login's `model_aliases` are skipped, because a run that
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
# Anchored on the left, so "sk-" or "eyJ" in the middle of a long base64 blob (encrypted reasoning in session
# files) doesn't count.
TOKEN_SHAPES = re.compile(r"(?<![A-Za-z0-9_+/=-])(sk-[A-Za-z0-9_-]{20,}|Bearer [A-Za-z0-9._-]{20,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,})")
HOME_PATH = re.compile(r"/(Users|home)/[A-Za-z0-9._-]+/")  # a personal folder path names the account and the folder layout
EMAIL = re.compile(r"[\w.+-]+@(gmail|outlook|hotmail|yahoo|icloud|proton)\.[a-z.]+", re.I)


def collect():
    """value -> where it was found (a file kind and a field path, never the value)."""
    secrets = {}
    where = [""]

    def add(value, path=""):
        if isinstance(value, str) and len(value) >= 16 and " " not in value and not value.startswith(("http", "/", "~")) \
                and not value.endswith(".json") and not re.fullmatch(r"[\w.+-]+@[\w.-]+", value) \
                and not re.fullmatch(r"\d{4}-\d\d-\d\dT[\d:.+Z-]+", value):
            secrets.setdefault(value, where[0] + path)

    def walk(node, path=""):
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for value in node:
                walk(value, path + "[]")
        elif not re.search(r"model_aliases\[\]\.(name|alias)$|excluded_models\[\]$|(^|\.)models?(\[\])?(\.(id|name|alias|slug))?$|model_ids\[\]$", path):
            add(node, path)

    if os.path.exists(CLIENT_KEYS):
        where[0] = "client key file"
        walk(json.load(open(CLIENT_KEYS)))
    if os.path.exists(KEYS_FILE):
        where[0] = "management key file"
        for line in open(KEYS_FILE):
            if "=" in line:
                add(line.split("=", 1)[1].strip(), " " + line.split("=", 1)[0].strip())
    if os.path.exists(CONFIG):
        # key, token, secret and password fields, without needing a YAML parser
        where[0] = "config"
        for m in re.finditer(r"^\s*-?\s*([\w-]*(?:key|token|secret|password)[\w-]*):\s*[\"']?([^\"'\s#]+)", open(CONFIG).read(), re.I | re.M):
            add(m.group(2), " " + m.group(1))
    for path in glob.glob(LOGINS):
        try:
            where[0] = "login file (" + os.path.basename(path).split("-")[0] + ")"
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
            dirs[:] = [d for d in dirs if d != "logs" and not d.startswith("work-")]  # git-ignored, never committed
            for name in names:
                path = os.path.join(root, name)
                files += 1
                text = open(path, errors="ignore").read()
                found = []
                origins = sorted({origin for value, origin in secrets.items() if value in text})
                if origins:
                    found.append("a value from " + "; ".join(origins[:4]))
                if TOKEN_SHAPES.search(text):
                    found.append("something shaped like a token")
                if EMAIL.search(text):
                    found.append("an e-mail address")
                if HOME_PATH.search(text):
                    found.append("a home folder path")
                if "pi-sessions" in path.split(os.sep):
                    found.append("a pi session file (holds the whole system prompt: skill names, folder paths)")
                if found:
                    hits += 1
                    print(f"{path}: {', '.join(found)}")
    print(f"{files} files scanned against {len(secrets)} credentials: {'CLEAN' if not hits else str(hits) + ' file(s) with findings'}")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
