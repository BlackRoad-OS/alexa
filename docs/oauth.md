# OAuth / OIDC — Self-Hosted Authentication

BlackRoad OS uses **Authentik** as its identity provider. Authentik is fully self-hosted, open-source, and requires no third-party cloud. All authentication tokens, sessions, and user data remain on your infrastructure.

## Why Authentik

| Property | Value |
|----------|-------|
| Self-hosted | ✅ Runs on your hardware (Raspberry Pi, bare-metal, VPS) |
| Internet required | ❌ None after initial container pull |
| Vendor lock-in | ❌ None |
| Protocols | OAuth 2.0, OIDC, SAML 2.0, LDAP, SCIM |
| License | MIT |

---

## Quick Start (Docker Compose)

```bash
# Download the official compose file
curl -o docker-compose.yml \
  https://goauthentik.io/docker-compose.yml

# Generate secret key and postgres password (use > to create a fresh .env)
echo "PG_PASS=$(openssl rand -base64 36 | tr -d '\n')" > .env
echo "AUTHENTIK_SECRET_KEY=$(openssl rand -base64 60 | tr -d '\n')" >> .env

# Bring it up
docker compose up -d
```

Access the admin UI at `http://<your-host>:9000/if/flow/initial-setup/`.

---

## Configure an OAuth2 / OIDC Application

1. **Admin UI → Applications → Create**
2. Set *Provider Type* to **OAuth2/OpenID Connect Provider**
3. Configure:

   | Field | Value |
   |-------|-------|
   | Name | `blackroad-api-gateway` |
   | Client type | Confidential |
   | Redirect URIs | `https://<your-gateway>/callback` |
   | Scopes | `openid profile email` |

4. Copy **Client ID** and **Client Secret** for use in the API gateway (see [`docs/api-gateway.md`](api-gateway.md)).

---

## Tailscale SSO Integration

Authentik can serve as the OIDC provider for Tailscale, so all mesh-node authentication flows through your own IdP instead of Tailscale's cloud account.

1. In Authentik, create a new **OAuth2/OIDC Provider** named `tailscale-sso`.
2. In the [Tailscale admin console](https://login.tailscale.com/admin/settings/general):
   - Enable **Custom OIDC**
   - Set *Issuer URL* to `https://<authentik-host>/application/o/tailscale-sso/`
   - Paste the Client ID and Client Secret from Authentik.
3. All device auth events now appear in Authentik's audit log.

> **Offline note:** Authentik runs entirely on-prem. The Tailscale OIDC check only hits your Authentik instance, not any cloud endpoint, as long as the Tailscale control plane can reach your host over the mesh.

---

## Environment Variables Reference

```env
# .env (do NOT commit — add to .gitignore)
PG_PASS=<random string>
AUTHENTIK_SECRET_KEY=<random string>
AUTHENTIK_EMAIL__HOST=localhost
AUTHENTIK_EMAIL__PORT=25
AUTHENTIK_EMAIL__USE_TLS=false
```

---

## Security Hardening

- Place Authentik behind the Cloudflare Tunnel (see [`docs/network.md`](network.md)) so the login UI is never directly exposed to the public internet.
- Enable **MFA** (TOTP) for all admin accounts in Authentik → Directory → Users.
- Rotate `AUTHENTIK_SECRET_KEY` and `PG_PASS` during initial setup before any users are created.

---

*Maintained by @blackboxprogramming · BlackRoad OS, Inc.*
