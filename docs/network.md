# Network Infrastructure — Tailscale + Cloudflare

BlackRoad OS uses **Tailscale** for zero-configuration mesh networking between nodes and **Cloudflare Tunnel** for exposing selected services to the internet without opening firewall ports.

```
                 ┌───────────────────────────────────┐
                 │         Tailscale Mesh             │
                 │                                   │
  Laptop ────────┤  Pi-1 (API Gateway)               │
  Phone  ────────┤  Pi-2 (Authentik)                 │
  Server ────────┤  Pi-3 (Storage / DB)              │
                 │                                   │
                 └───────────┬───────────────────────┘
                             │ Cloudflare Tunnel (outbound only)
                             ▼
                     Public domain (HTTPS)
                     e.g. auth.blackroad.io
```

---

## 1. Tailscale

### Install on each node

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --authkey=<reusable-authkey>
```

Generate a reusable auth key at [login.tailscale.com/admin/settings/keys](https://login.tailscale.com/admin/settings/keys).

### Enable MagicDNS

In the Tailscale admin console → DNS:
- Turn on **MagicDNS**
- Set a custom domain, e.g. `blackroad.internal`

Nodes will resolve each other as `pi-1.blackroad.internal`, `api.blackroad.internal`, etc.

### Custom OIDC (self-hosted auth via Authentik)

Follow the steps in [`docs/oauth.md`](oauth.md#tailscale-sso-integration) to replace Tailscale's default cloud authentication with your Authentik instance. Once configured, Tailscale control-plane auth no longer relies on any third-party identity provider.

### ACL Policy (example)

Only authorised operators (@blackboxprogramming, @lucidia) can reach the API gateway:

```hujson
// Tailscale ACL — paste into admin console → Access Controls
{
  "tagOwners": {
    "tag:gateway":  ["autogroup:owner"],
    "tag:operator": ["autogroup:owner"]
  },
  "acls": [
    // operators can reach the API gateway
    {
      "action": "accept",
      "src":    ["tag:operator"],
      "dst":    ["tag:gateway:4000", "tag:gateway:443"]
    },
    // operators can reach Authentik for authentication
    {
      "action": "accept",
      "src":    ["tag:operator"],
      "dst":    ["tag:gateway:9000"]
    }
  ]
}
```

---

## 2. Cloudflare Tunnel

Cloudflare Tunnel creates an outbound-only encrypted connection from your Pi to Cloudflare's edge. No inbound ports, no firewall changes.

### Install `cloudflared`

```bash
# On the gateway Pi — pin to a specific release for reproducibility
# Check https://github.com/cloudflare/cloudflared/releases for the latest version
CLOUDFLARED_VERSION="2025.1.0"
wget "https://github.com/cloudflare/cloudflared/releases/download/${CLOUDFLARED_VERSION}/cloudflared-linux-arm64.deb"
sudo dpkg -i cloudflared-linux-arm64.deb
```

### Authenticate and create a tunnel

```bash
cloudflared tunnel login          # opens browser — authorise your Cloudflare zone
cloudflared tunnel create blackroad
```

### Configure the tunnel

```yaml
# ~/.cloudflared/config.yml
tunnel: <tunnel-id>
credentials-file: /root/.cloudflared/<tunnel-id>.json

ingress:
  # Public-facing Authentik (login portal only)
  - hostname: auth.blackroad.io
    service: http://localhost:9000

  # Catch-all — reject everything else
  - service: http_status:404
```

### Run as a service

```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
```

### DNS records

In the Cloudflare dashboard → DNS, add a CNAME:

| Name | Target |
|------|--------|
| `auth` | `<tunnel-id>.cfargotunnel.com` |

The API gateway (`api.blackroad.internal`) is **not** exposed through the tunnel — it is only reachable inside the Tailscale mesh.

---

## 3. Traffic Flow Summary

| Request | Route |
|---------|-------|
| Login (Authentik UI) | Internet → Cloudflare Tunnel → Pi-2 port 9000 |
| API call from operator device | Device → Tailscale mesh → Pi-1 port 443 |
| Vendor API call | Pi-1 → Internet → Vendor (proxied by LiteLLM) |
| Inbound connection to Pi cluster | ❌ Blocked — no open ports |

**Confirmation:** OpenAI, Anthropic, and other vendor traffic is *outbound only* from Pi-1. No vendor can initiate a connection into your mesh. Your Pis are not routing external traffic to you — they are making outbound API calls on your behalf.

---

## 4. Verification

```bash
# Confirm no unexpected open ports
sudo ss -tlnp

# Confirm Tailscale peers
tailscale status

# Confirm tunnel is up
cloudflared tunnel info blackroad

# Test API gateway from inside the mesh
curl -H "Authorization: Bearer <key>" \
  https://api.blackroad.internal/v1/models
```

---

*Maintained by @blackboxprogramming · BlackRoad OS, Inc.*
