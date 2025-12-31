# Self-Hosted Infisical with Tailscale and Caddy

Secure, Tailscale-exposed Infisical instance with automatic HTTPS via Caddy (Cloudflare DNS-01).

## Prerequisites

- Docker & Docker Compose
- Tailscale account (auth key)
- Cloudflare domain + API token (DNS edit permissions)
- Python 3 (for manage script)

## Setup

1. Clone repo  
   ```bash
   git clone https://github.com/brainxio/selfhosted-secrets.git
   cd selfhosted-secrets/infisical
   ```

2. Run management script  
   ```bash
   python3 manage_stack.py
   ```
   - Prompts for Tailscale authkey, Cloudflare token, domain.
   - Auto-generates secrets, creates `.env` and `Caddyfile`.

3. Start stack  
   ```bash
   python3 manage_stack.py up
   ```

## Access

- Infisical: `https://your-domain.com` (via Tailnet or public)
- Only exposed via Caddy on Tailscale network.

## Management

- `./manage_stack.py` → update/setup secrets
- `./manage_stack.py up` → start
- `./manage_stack.py down` → stop

## Notes

- Secrets stored in system keyring if available, else `.env`.
- Delete `pg_data` volume for fresh DB on key changes.
- Tailscale state persisted in `tailscale-state/`.
