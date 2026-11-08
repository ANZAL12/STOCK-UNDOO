/**
 * STOCK UNDO! - Frontend API Client
 * Connects to FastAPI backend via relative path or configured VITE_API_BASE_URL.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchTallyStatus() {
  const res = await fetch(`${API_BASE}/api/tally/status`);
  if (!res.ok) {
    throw new Error(`Tally status probe failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchAllStock(refresh = false) {
  const url = `${API_BASE}/api/stock/all${refresh ? '?refresh=true' : ''}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to load stock data: HTTP ${res.status}`);
  }
  return res.json();
}

export async function searchStock(query, source = null) {
  const params = new URLSearchParams({ q: query });
  if (source) {
    params.append('source', source);
  }
  const res = await fetch(`${API_BASE}/api/stock/search?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Search request failed: HTTP ${res.status}`);
  }
  return res.json();
}

