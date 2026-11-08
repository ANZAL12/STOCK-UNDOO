# Cloudflare Tunnel Setup for STOCK UNDO!

Cloudflare Tunnel securely exposes the PC 1 FastAPI backend to the public internet via an encrypted outbound tunnel, without opening any router ports or exposing Tally port 9000.

---

## Architecture Security Guarantees

1. **Port 9000 is NEVER exposed**: Cloudflare Tunnel only connects to `http://127.0.0.1:8000`. Port 9000 remains strictly bound to localhost (PC 1) and Tailscale (PC 2).
2. **PC 2 is NEVER exposed**: PC 2 is reachable exclusively by PC 1 through the encrypted Tailscale mesh (`100.x.y.z`).
3. **No Inbound Ports**: Zero firewall openings or router port forwards are required.
4. **Staff Access**: Authorized staff access the application via a standard browser over HTTPS without needing Tailscale or VPN client installed.

---

## Step-by-Step Setup Instructions

### 1. Download Cloudflare Tunnel (`cloudflared`) on PC 1

Download `cloudflared-windows-amd64.exe` from [Cloudflare Releases](https://github.com/cloudflare/cloudflared/releases) and place it in `C:\Program Files\cloudflared\` (or add to your PATH).

### 2. Login to Cloudflare
In PowerShell or Command Prompt on PC 1, run:
```cmd
cloudflared tunnel login
```
This opens your browser to authenticate with your Cloudflare domain.

### 3. Create the STOCK UNDO Tunnel
```cmd
cloudflared tunnel create stock-undo-tunnel
```
Note the generated Tunnel UUID (e.g., `f3d7e8b2-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).

### 4. Create DNS Route
Route your public API subdomain to the tunnel:
```cmd
cloudflared tunnel route dns stock-undo-tunnel stock-undo-api.yourdomain.com
```

### 5. Configure the Tunnel
Copy `tunnel/config.yml.example` to `C:\Users\USER\.cloudflared\config.yml` and replace the Tunnel UUID and domain name:
```yaml
tunnel: f3d7e8b2-xxxx-xxxx-xxxx-xxxxxxxxxxxx
credentials-file: C:\Users\USER\.cloudflared\f3d7e8b2-xxxx-xxxx-xxxx-xxxxxxxxxxxx.json

ingress:
  - hostname: stock-undo-api.yourdomain.com
    service: http://127.0.0.1:8000
  - service: http_status:404
```

### 6. Run the Tunnel as a Background Windows Service
```cmd
cloudflared service install
net start cloudflared
```

### 7. Point Vercel Frontend to the Public API
In your Vercel Project Settings > **Environment Variables**, set:
```env
VITE_API_BASE_URL=https://stock-undo-api.yourdomain.com
```
Redeploy the frontend on Vercel.

