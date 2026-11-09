/**
 * STOCK UNDO! - Frontend API Client
 * Connects to FastAPI backend via relative path or configured VITE_API_BASE_URL.
 */

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '');

export function getWebSocketUrl() {
  if (API_BASE) {
    const wsBase = API_BASE.replace(/^https:\/\//i, 'wss://').replace(/^http:\/\//i, 'ws://');
    return `${wsBase}/api/ws/stock`;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/api/ws/stock`;
}

async function fetchWithTimeout(url, timeoutMs = 10000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { signal: controller.signal, cache: 'no-store' });
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchHealth() {
  const res = await fetchWithTimeout(`${API_BASE}/api/health`, 5000);
  if (!res.ok) {
    throw new Error(`Health check failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchTallyStatus() {
  const res = await fetchWithTimeout(`${API_BASE}/api/tally/status`, 6000);
  if (!res.ok) {
    throw new Error(`Tally status probe failed: HTTP ${res.status}`);
  }
  return res.json();
}

export async function fetchAllStock(refresh = false) {
  const url = `${API_BASE}/api/stock/all${refresh ? '?refresh=true' : ''}`;
  const res = await fetchWithTimeout(url, 12000);
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
  const res = await fetchWithTimeout(`${API_BASE}/api/stock/search?${params.toString()}`, 10000);
  if (!res.ok) {
    throw new Error(`Search request failed: HTTP ${res.status}`);
  }
  return res.json();
}

