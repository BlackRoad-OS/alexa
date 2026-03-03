# alexa

Primary human operator context for the BlackRoad system.

---

## System Architecture

All AI vendor API traffic routes through a self-hosted gateway on your own infrastructure. No request goes directly from a client device to any vendor.

```
Client → Tailscale mesh → BlackRoad API Gateway → Vendor API
                                 ↑
                        Auth via self-hosted Authentik (OAuth 2.0 / OIDC)
```

Public-facing services (e.g. the login portal) are exposed without opening firewall ports via a Cloudflare Tunnel (outbound-only connection from your Pi).

---

## Documentation

| Guide | Description |
|-------|-------------|
| [`docs/oauth.md`](docs/oauth.md) | Self-hosted OAuth / OIDC with Authentik |
| [`docs/api-gateway.md`](docs/api-gateway.md) | Custom AI API gateway (LiteLLM proxy) |
| [`docs/network.md`](docs/network.md) | Tailscale mesh + Cloudflare Tunnel setup |

---

## Quick Start

```bash
# 1. Copy environment template and fill in your secrets
cp config/.env.example .env
$EDITOR .env

# 2. Start the stack
cd config
docker compose up -d

# 3. Follow docs/oauth.md to complete Authentik initial setup
# 4. Follow docs/network.md to join nodes to the Tailscale mesh
```

See each guide for detailed setup instructions.

---

## Principles

- 🔱 **Sovereignty** — your data, your hardware, your keys
- 🔒 **Privacy** — no telemetry, no external dependencies on core paths
- 🌐 **Offline-First** — gateway and auth work without internet after setup
- 🚀 **Production Quality** — reliable, auditable, and scalable
