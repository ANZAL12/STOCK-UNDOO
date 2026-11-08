# STOCK UNDO! – Centralized TallyPrime Stock Viewer
> *"Check stock before you call the godown!"*

STOCK UNDO! is a secure, lightweight web application that retrieves real-time stock quantities from two independent TallyPrime installations (PC 1 Local and PC 2 via Tailscale) and displays closing balances to authorized staff through standard web browsers.

---

## Visual Identity & Branding

- **Application Name**: `STOCK UNDO!`
- **Tagline**: *"Check stock before you call the godown!"*
- **App Logo**: Official logo located at [`branding/logo.svg`](file:///a:/Stock%20Undoo/branding/logo.svg) and served via [`frontend/public/logo.svg`](file:///a:/Stock%20Undoo/frontend/public/logo.svg).
- **Color Palette**:
  - Deep Navy Blue (`#0A192F` / `#0F172A`)
  - Bright Yellow/Orange (`#F59E0B` / `#EA580C`)
  - Emerald Green (`#10B981`)
  - Crisp White / Slate (`#FFFFFF` / `#F8FAFC`)

---

## Strict Read-Only Integration & Security Perimeter

1. **Strictly Read-Only**: The backend only sends XML `<TALLYREQUEST>Export Data</TALLYREQUEST>`. Absolutely NO vouchers, alterations, deletions, adjustments, or ledger mutations can ever be performed.
2. **Auto-Discovery & Whitelist Support**: Live models in Tally are dynamically discovered and listed. Saved models are preserved in [`backend/whitelist.json`](file:///a:/Stock%20Undoo/backend/whitelist.json).
3. **No Financial Leaks**: Purchase costs, selling rates, closing values, and profit margins are completely stripped and never transmitted.
4. **Network Isolation**:
   - Tally port `9000` is **NEVER** exposed to the internet.
   - PC 2 is only accessible to PC 1 via encrypted Tailscale point-to-point mesh.
   - Cloudflare Tunnel exclusively exposes the FastAPI backend on port `8000`.
   - Staff access the web dashboard via standard HTTPS browsers without installing Tailscale or VPN.

---

## Project Structure

```
Stock Undoo/
├── START_STOCK_UNDO.bat           # 1-Click launcher: starts Backend & Frontend
├── run_backend.bat                # 1-Click launcher: activates .venv & starts FastAPI (Port 8000)
├── run_frontend.bat               # 1-Click launcher: starts React/Vite (Port 5173)
├── .gitignore                     # Git ignore rules (.venv, node_modules, etc.)
├── README.md                      # Comprehensive project documentation
├── branding/
│   └── logo.svg                   # Official STOCK UNDO! vector asset
├── scripts/
│   ├── test_tally_connectivity.py # Standalone Python diagnostic tool
│   └── test_tally_connectivity.ps1# Windows PowerShell diagnostic tool
├── backend/
│   ├── .venv/                     # Python Virtual Environment
│   ├── .env                       # Backend environment configuration
│   ├── whitelist.json             # Configurable permitted stock item models
│   ├── requirements.txt           # Python dependencies
│   ├── app/
│   │   ├── main.py                # FastAPI entrypoint with security middleware
│   │   ├── config.py              # Pydantic settings & whitelist loader
│   │   ├── tally/
│   │   │   ├── tally_client.py    # Async Tally HTTP/XML client
│   │   │   ├── tally_pc1.py       # PC 1 adapter (127.0.0.1:9000)
│   │   │   ├── tally_pc2.py       # PC 2 adapter (Tailscale:9000)
│   │   │   ├── xml_templates.py   # Strict read-only XML export generators
│   │   │   └── xml_parser.py      # Safe XML sanitizer & closing qty parser
│   │   ├── routes/
│   │   │   ├── health.py          # /api/health and /api/tally/status
│   │   │   └── stock.py           # /api/stock/all, pc1, pc2, search, whitelist
│   │   ├── services/
│   │   │   └── stock_service.py   # Model discovery, aggregator, TTL cache
│   │   └── models/
│   │       └── stock.py           # Pydantic schemas (strictly non-financial)
│   └── tests/
│       └── test_api.py            # Automated API test suite
├── frontend/
│   ├── package.json               # React 19, Tailwind CSS, Vite dependencies
│   ├── vercel.json                # Vercel SPA routing configuration
│   ├── vite.config.js             # Vite proxy to backend port 8000
│   ├── public/logo.svg            # Favicon & application icon
│   └── src/
│       ├── App.jsx                # Mobile-first single page with top search bar
│       ├── api.js                 # Frontend REST client
│       └── index.css              # Tailwind CSS styles
└── tunnel/
    ├── README_TUNNEL.md           # Step-by-step Cloudflare Tunnel setup guide
    └── config.yml.example         # cloudflared configuration template
```

---

## Virtual Environment Setup (.venv)

The backend is fully self-contained inside `backend/.venv`:

```cmd
# Activate virtual environment manually:
cd backend
.venv\Scripts\activate.bat

# Run tests using the virtual environment:
python tests\test_api.py
```

[`run_backend.bat`](file:///a:/Stock%20Undoo/run_backend.bat) automatically detects and activates `backend/.venv` upon execution.

---

## Quick Start (Local Run)

Double-click [`START_STOCK_UNDO.bat`](file:///a:/Stock%20Undoo/START_STOCK_UNDO.bat) to launch both servers at once:

- **Mobile Web App**: [http://localhost:5173](http://localhost:5173)
- **FastAPI Backend**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **API Docs**: [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)
