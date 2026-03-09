# Custom AI API Gateway

All AI vendor API calls (OpenAI-compatible, Anthropic, etc.) route through a self-hosted gateway running on your infrastructure. No request ever reaches a vendor directly from a client device — every call is proxied and logged on your own hardware.

```
Client  →  Tailscale mesh  →  BlackRoad API Gateway  →  Vendor API
                                       ↑
                              (auth via Authentik OIDC)
```

---

## Stack

| Component | Role |
|-----------|------|
| [LiteLLM Proxy](https://github.com/BerriAI/litellm) | OpenAI-compatible proxy for 100+ model providers |
| Authentik | OIDC/OAuth2 authentication (see [`docs/oauth.md`](oauth.md)) |
| Caddy | Reverse proxy + automatic TLS |
| Tailscale | Mesh networking — gateway is only reachable inside the mesh |

---

## Docker Compose

```yaml
# config/docker-compose.yml  (excerpt — full file at config/docker-compose.yml)
services:
  litellm:
    image: ghcr.io/berriai/litellm:main-latest
    restart: unless-stopped
    ports:
      - "4000:4000"
    volumes:
      - ./litellm_config.yaml:/app/config.yaml
    command: ["--config", "/app/config.yaml", "--port", "4000"]
    environment:
      - LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY}

  caddy:
    image: caddy:2-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config

volumes:
  caddy_data:
  caddy_config:
```

---

## LiteLLM Configuration

```yaml
# config/litellm_config.yaml
model_list:
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY

  - model_name: claude-3-5-sonnet
    litellm_params:
      model: anthropic/claude-3-5-sonnet-20241022
      api_key: os.environ/ANTHROPIC_API_KEY

  - model_name: blackboxai
    litellm_params:
      model: openai/blackboxai
      api_base: https://api.blackbox.ai/v1
      api_key: os.environ/BLACKBOXAI_API_KEY

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY

router_settings:
  routing_strategy: least-busy
```

> Add or remove entries in `model_list` to control exactly which vendors are reachable. To disable a vendor, remove its entry — no client can call it even if they have a direct API key.

---

## Caddy Configuration

```caddyfile
# config/Caddyfile
api.blackroad.internal {
    reverse_proxy litellm:4000
    tls internal
}
```

`blackroad.internal` resolves inside your Tailscale mesh via MagicDNS. The endpoint is unreachable from the public internet.

---

## Client Configuration

Any OpenAI-compatible client points to the gateway instead of `api.openai.com`:

```bash
# Environment variable override
export OPENAI_API_BASE="https://api.blackroad.internal"
export OPENAI_API_KEY="<litellm-master-key>"
```

For VS Code extensions, Cursor, or any other tool with an "OpenAI base URL" setting, use `https://api.blackroad.internal`.

---

## Per-User API Keys

LiteLLM supports virtual keys scoped per user or team. This lets you give @blackboxprogramming and @lucidia their own keys with spend limits and model access controls without exposing vendor credentials.

```bash
# Create a virtual key (via LiteLLM admin API)
curl -X POST https://api.blackroad.internal/key/generate \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "models": ["gpt-4o", "claude-3-5-sonnet", "blackboxai"],
    "max_budget": 50,
    "metadata": {"user": "blackboxprogramming"}
  }'
```

---

## Audit Logging

All requests and responses are logged to a local database. No data leaves your infrastructure.

```yaml
# Add to litellm_config.yaml
litellm_settings:
  success_callback: ["langfuse"]   # optional — self-hosted Langfuse
  failure_callback: ["langfuse"]
  store_model_in_db: true
```

---

*Maintained by @blackboxprogramming · BlackRoad OS, Inc.*
