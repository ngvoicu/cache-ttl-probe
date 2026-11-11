#!/usr/bin/env python3
"""Pin one model to one login of a local CLIProxyAPI, for a measurement.

    python3 harness/pool.py add probe/gpt-6.1-sol --login codex-1234.json --model gpt-6.1-sol
    python3 harness/pool.py add devin/gpt-6-astra          # a login already serves this exact id
    python3 harness/pool.py list
    python3 harness/pool.py remove probe/gpt-6.1-sol

A measurement must reach one account. With the cpa-pools-and-aliases plugin, clients see only pools, so the
model has to be a pool with that login as its only member. `add` makes one the way the plugin's page does,
through CLIProxyAPI's management API:

  1. an alias on the login (`model_aliases` in its credential file): <model> -> <pool id>, keeping the model's
     own name served as before;
  2. the pool id in the plugin's pool list.

`remove` undoes both. Without --login and --model only step 2 runs: enough when a login already serves the
pool id as is (Devin's `devin/...` ids, Meta's `muse-...`).

CLIProxyAPI rewrites the pool list when it saves it, so a YAML comment written inside that list is lost.

The management key comes from CPA_MGMT_KEY, or from the MGMT_KEY line of ~/.cli-proxy-api/keys.txt. It is never
printed. Back up the config and the login folder before changing a CLIProxyAPI you depend on.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

PLUGIN = "cpa-pools-and-aliases"


def management_key():
    key = os.environ.get("CPA_MGMT_KEY", "").strip()
    if key:
        return key
    path = os.path.expanduser("~/.cli-proxy-api/keys.txt")
    if os.path.exists(path):
        for line in open(path):
            if line.startswith("MGMT_KEY") and "=" in line:
                return line.split("=", 1)[1].strip()
    sys.exit("no management key: set CPA_MGMT_KEY")


class Api:
    def __init__(self, base, key):
        self.base, self.key = base.rstrip("/") + "/v8/management", key

    def call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method, headers={
            "Authorization": "Bearer " + self.key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as err:
            sys.exit(f"{method} {path}: HTTP {err.code} {err.read().decode(errors='replace')[:300]}")
        return json.loads(raw) if raw.strip() else None

    def logins(self):
        return [f["name"] for f in self.call("GET", "/credentials").get("files", [])]

    def aliases(self, login):
        content = self.call("GET", "/credentials/download?name=" + urllib.parse.quote(login))
        return list(content.get("model_aliases") or content.get("model-aliases") or [])

    def set_aliases(self, login, aliases):
        self.call("PATCH", "/credentials/fields", {"name": login, "model_aliases": aliases})

    def pools(self):
        config = self.call("GET", f"/config/plugins/configs/{PLUGIN}") or {}
        config = config.get("value", config) if isinstance(config, dict) else {}
        return list(config.get("pools") or [])

    def set_pools(self, pools):
        self.call("PUT", f"/config/plugins/configs/{PLUGIN}/pools", pools)


def add(api, pool, login, model):
    if "/" not in pool:
        sys.exit("use a pool id of the form <name>/<model>, e.g. probe/gpt-6.1-sol: a plain id is the model's main pool")
    if bool(login) != bool(model):
        sys.exit("give --login and --model together, or neither")
    pools = api.pools()
    if pool in pools:
        sys.exit(f"pool {pool} already exists")
    if not login:
        api.set_pools(pools + [pool])
        print(f"added {pool} (served as is, no alias)")
        return
    if login not in api.logins():
        sys.exit(f"no login file named {login}")
    aliases = api.aliases(login)
    if any(a.get("alias") == pool for a in aliases):
        sys.exit(f"{login} already has an alias {pool}")
    # Alias first, pool list last: a failed alias write must not leave a pool nothing serves.
    api.set_aliases(login, aliases + [{"alias": pool, "name": model, "fork": True}])
    api.set_pools(pools + [pool])
    print(f"added {pool}: {model} on {login}")


def remove(api, pool):
    pools = api.pools()
    if pool in pools:
        api.set_pools([p for p in pools if p != pool])
    touched = []
    for login in api.logins():
        aliases = api.aliases(login)
        kept = [a for a in aliases if a.get("alias") != pool]
        if len(kept) != len(aliases):
            api.set_aliases(login, kept)
            touched.append(login)
    if pool not in pools and not touched:
        sys.exit(f"nothing named {pool}")
    print(f"removed {pool}" + (f" (alias taken off {', '.join(touched)})" if touched else ""))


def show(api):
    pools = api.pools()
    by_pool = {}
    for login in api.logins():
        for a in api.aliases(login):
            by_pool.setdefault(a.get("alias"), []).append(f"{login}: {a.get('name')}")
    for pool in pools:
        members = by_pool.get(pool) or ["(no login alias: served as is, or by API keys)"]
        print(pool)
        for member in members:
            print("   " + member)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", default=os.environ.get("CPA_BASE_URL", "http://127.0.0.1:8317"))
    sub = parser.add_subparsers(dest="command", required=True)
    p_add = sub.add_parser("add", help="pin a model to one login under a new pool id")
    p_add.add_argument("pool")
    p_add.add_argument("--login", help="credential file name, e.g. codex-1234.json")
    p_add.add_argument("--model", help="the model id that login serves")
    p_remove = sub.add_parser("remove", help="remove a pool made by add")
    p_remove.add_argument("pool")
    sub.add_parser("list", help="show pools and the login aliases behind them")
    args = parser.parse_args()

    api = Api(args.base_url, management_key())
    if args.command == "add":
        add(api, args.pool, args.login, args.model)
    elif args.command == "remove":
        remove(api, args.pool)
    else:
        show(api)


if __name__ == "__main__":
    main()
