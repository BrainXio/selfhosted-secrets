#!/usr/bin/env python3
"""
manage_infisical.py - Simple working version (reverted)
"""

import os
import sys
import getpass
import secrets
import base64
import subprocess
import shutil

APP_LABEL = "infisical-tailnet"
ENV_PATH = ".env"
CADDYFILE_PATH = "Caddyfile"
TAILSCALE_DIR = "tailscale-state"

PROMPT_VARS = ["TS_AUTHKEY", "CLOUDFLARE_API_TOKEN", "DOMAIN"]

DEFAULTS = {
    "POSTGRES_USER": "infisical",
    "POSTGRES_DB": "infisical",
    "REDIS_URL": "redis://localhost:6379",
}

try:
    import secretstorage
    HAS_KEYRING = True
except ImportError:
    try:
        import keyring
        HAS_KEYRING = True
    except ImportError:
        HAS_KEYRING = False

def get_compose_cmd():
    if shutil.which("docker") and subprocess.run(["docker", "compose", "version"],
                                                 stdout=subprocess.DEVNULL,
                                                 stderr=subprocess.DEVNULL).returncode == 0:
        return ["docker", "compose"]
    elif shutil.which("docker-compose"):
        return ["docker-compose"]
    else:
        print("Error: No docker compose found.")
        sys.exit(1)

COMPOSE_CMD = get_compose_cmd()

def keyring_set(key, value):
    if 'secretstorage' in globals():
        import secretstorage
        conn = secretstorage.dbus_init()
        coll = secretstorage.get_default_collection(conn)
        if coll.is_locked(): coll.unlock()
        attrs = {"application": APP_LABEL, "key": key}
        coll.create_item(f"{APP_LABEL} {key}", attrs, value.encode(), replace=True)
    else:
        keyring.set_password(APP_LABEL, key, value)

def keyring_get(key):
    if 'secretstorage' in globals():
        import secretstorage
        conn = secretstorage.dbus_init()
        coll = secretstorage.get_default_collection(conn)
        items = list(coll.search_items({"application": APP_LABEL, "key": key}))
        return items[0].get_secret().decode() if items else None
    else:
        return keyring.get_password(APP_LABEL, key)

def load_secrets():
    env = DEFAULTS.copy()
    if HAS_KEYRING:
        for var in ["POSTGRES_PASSWORD", "AUTH_SECRET", "ENCRYPTION_KEY"] + PROMPT_VARS:
            val = keyring_get(var)
            if val:
                env[var] = val
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k] = v.strip('"\'')
    return env

def save_secrets(env):
    if HAS_KEYRING:
        for var in ["POSTGRES_PASSWORD", "AUTH_SECRET", "ENCRYPTION_KEY"] + PROMPT_VARS:
            if var in env:
                keyring_set(var, env[var])
        print("Secrets stored in keyring.")
    with open(ENV_PATH, "w") as f:
        for k in sorted(env):
            f.write(f'{k}="{env[k]}"\n')
    print(".env written.")

def generate_caddyfile(domain):
    content = f"""
{domain} {{
    reverse_proxy localhost:8080

    tls {{
        dns cloudflare {{env.CLOUDFLARE_API_TOKEN}}
    }}
}}
"""
    with open(CADDYFILE_PATH, "w") as f:
        f.write(content.strip() + "\n")
    print(f"Caddyfile generated for {domain}.")

def main():
    os.makedirs(TAILSCALE_DIR, exist_ok=True)

    env = load_secrets()
    changed = False

    if "POSTGRES_PASSWORD" not in env:
        env["POSTGRES_PASSWORD"] = secrets.token_hex(32)
        changed = True

    if "ENCRYPTION_KEY" not in env:
        env["ENCRYPTION_KEY"] = secrets.token_hex(16)
        changed = True

    if "AUTH_SECRET" not in env:
        env["AUTH_SECRET"] = base64.b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        changed = True

    for var in PROMPT_VARS:
        if var not in env:
            val = getpass.getpass(f"Enter {var}: ").strip()
            if not val:
                print(f"{var} required.")
                sys.exit(1)
            env[var] = val
            changed = True

    env["SITE_URL"] = f"https://{env['DOMAIN']}"
    env["DB_CONNECTION_URI"] = f"postgres://{env['POSTGRES_USER']}:{env['POSTGRES_PASSWORD']}@localhost:5432/{env['POSTGRES_DB']}"

    if changed or not os.path.exists(CADDYFILE_PATH):
        save_secrets(env)
        generate_caddyfile(env["DOMAIN"])
    else:
        print("All files up to date.")

    if len(sys.argv) > 1:
        if sys.argv[1] in ["up", "down"]:
            cmd = COMPOSE_CMD + (["up", "-d"] if sys.argv[1] == "up" else ["down"])
            subprocess.run(cmd, check=True)
        else:
            subprocess.run(COMPOSE_CMD + sys.argv[1:], check=True)

if __name__ == "__main__":
    main()