import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { fetchAllStock, fetchHealth, getWebSocketUrl } from './api';
import { Search, RotateCw, X, Package, WifiOff, AlertTriangle } from 'lucide-react';

export default function App() {
  const [stockItems, setStockItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isServerOffline, setIsServerOffline] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedModel, setSelectedModel] = useState('32 HDR- FM 32 HDROP 1');

  // Real-time changed items map: { [model]: 'increased' | 'decreased' }
  const [changedModels, setChangedModels] = useState({});
  const prevStockRef = useRef({});
  const wsRef = useRef(null);
  const isFetchingRef = useRef(false);

  // Helper to detect changed quantities
  const updateStockWithDeltas = useCallback((newItems) => {
    const changes = {};
    const newMap = {};

    newItems.forEach((item) => {
      const prev = prevStockRef.current[item.model];
      const curr = item.available_stock || 0;
      newMap[item.model] = curr;

      if (prev !== undefined && prev !== curr) {
        changes[item.model] = curr > prev ? 'increased' : 'decreased';
      }
    });

    prevStockRef.current = newMap;
    setStockItems(newItems);
    setIsServerOffline(false); // Server is confirmed online

    if (Object.keys(changes).length > 0) {
      setChangedModels(changes);
      setTimeout(() => {
        setChangedModels({});
      }, 3500);
    }
  }, []);

  // Verify immediately whether the backend server is truly offline
  const verifyServerOnline = useCallback(async () => {
    try {
      await fetchHealth();
      setIsServerOffline(false);
      return true;
    } catch {
      setIsServerOffline(true);
      return false;
    }
  }, []);

  // Fetch stock from backend
  const loadStock = useCallback(async (isManual = false) => {
    if (!isManual && isFetchingRef.current) return;
    isFetchingRef.current = true;
    if (isManual) setIsRefreshing(true);

    try {
      const data = await fetchAllStock(isManual);
      updateStockWithDeltas(data.items || []);
      setIsServerOffline(false);
    } catch (err) {
      console.warn('Backend server is unreachable:', err);
      setIsServerOffline(true); // Trigger instant popup
    } finally {
      isFetchingRef.current = false;
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [updateStockWithDeltas]);

  // Initial load
  useEffect(() => {
    loadStock(false);
  }, [loadStock]);

  // Background polling (every 5 seconds as fallback + instant offline detection)
  useEffect(() => {
    const pollTimer = setInterval(() => {
      if (document.visibilityState !== 'hidden') {
        loadStock(false);
      }
    }, 5000);

    return () => clearInterval(pollTimer);
  }, [loadStock]);

  // WebSocket Live Connection with heartbeat
  useEffect(() => {
    const wsUrl = getWebSocketUrl();

    let reconnectTimer = null;
    let heartbeatTimer = null;
    let isUnmounted = false;

    const connectWebSocket = () => {
      if (isUnmounted) return;
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          setIsServerOffline(false);
          if (heartbeatTimer) clearInterval(heartbeatTimer);
          heartbeatTimer = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send('ping');
            }
          }, 20000);
        };

        ws.onmessage = (event) => {
          if (event.data === 'pong') return;
          try {
            const message = JSON.parse(event.data);
            if (message.type === 'STOCK_UPDATED' || message.type === 'INITIAL_STOCK') {
              if (message.data && message.data.items) {
                updateStockWithDeltas(message.data.items);
                setIsLoading(false);
                setIsServerOffline(false);
              }
            }
          } catch (e) {
            console.error('WS parse error:', e);
          }
        };

        ws.onclose = () => {
          if (heartbeatTimer) {
            clearInterval(heartbeatTimer);
            heartbeatTimer = null;
          }
          if (!isUnmounted) {
            reconnectTimer = setTimeout(() => {
              connectWebSocket();
            }, 2500);
          }
        };

        ws.onerror = () => {
          // Confirm server reachability before showing offline modal
          verifyServerOnline();
          ws.close();
        };
      } catch (err) {
        verifyServerOnline();
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        loadStock(false);
        if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
          if (reconnectTimer) clearTimeout(reconnectTimer);
          connectWebSocket();
        }
      }
    };

    connectWebSocket();
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      isUnmounted = true;
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (heartbeatTimer) clearInterval(heartbeatTimer);
      if (wsRef.current) wsRef.current.close();
    };
  }, [updateStockWithDeltas, verifyServerOnline, loadStock]);

  // Flexible search: ignores spaces, punctuation, extra whitespace, and word order
  const filteredItems = useMemo(() => {
    const raw = searchQuery.toLowerCase().trim();
    if (!raw) return stockItems;

    const clean = (str) => str.toLowerCase().replace(/[^a-z0-9*]+/g, ' ').trim();
    const compact = (str) => str.toLowerCase().replace(/[^a-z0-9*]/g, '');

    const compactQuery = compact(raw);
    const tokens = clean(raw).split(/\s+/).filter(Boolean);

    if (!compactQuery && tokens.length === 0) return stockItems;

    return stockItems.filter((item) => {
      const compactModel = compact(item.model);
      if (compactQuery && compactModel.includes(compactQuery)) {
        return true;
      }
      const cleanModel = clean(item.model);
      return tokens.length > 0 && tokens.every((tok) => cleanModel.includes(tok) || compactModel.includes(tok));
    });
  }, [stockItems, searchQuery]);

  return (
    <div className="min-h-screen bg-white text-slate-900 flex justify-center selection:bg-amber-100 relative">
      
      {/* ========================================================================= */}
      {/* INSTANT SERVER OFFLINE POPUP MODAL */}
      {/* ========================================================================= */}
      {isServerOffline && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="w-full max-w-xs sm:max-w-sm bg-white rounded-3xl shadow-2xl border border-rose-200 p-6 text-center flex flex-col items-center">
            
            {/* Warning Icon Badge */}
            <div className="w-16 h-16 rounded-full bg-rose-50 border-2 border-rose-200 flex items-center justify-center mb-4 text-rose-600 shadow-inner">
              <WifiOff className="w-8 h-8 animate-pulse text-rose-600" />
            </div>

            {/* Popup Title */}
            <h3 className="text-xl font-black text-slate-900 tracking-tight">
              Server is Offline!
            </h3>

            {/* Popup Message */}
            <p className="text-xs sm:text-sm text-slate-500 mt-2 mb-5 leading-relaxed font-medium">
              Cannot connect to the office server. Please verify the server computer is powered on.
            </p>

            {/* Reconnect Button */}
            <button
              onClick={() => loadStock(true)}
              disabled={isRefreshing}
              className="w-full py-3 px-4 bg-slate-950 hover:bg-slate-800 active:scale-95 text-white text-xs sm:text-sm font-bold rounded-2xl transition flex items-center justify-center gap-2 shadow-lg cursor-pointer disabled:opacity-50"
            >
              <RotateCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>{isRefreshing ? 'Reconnecting...' : 'Retry Connection Now'}</span>
            </button>

            <span className="text-[11px] text-slate-400 mt-3 font-medium">
              Auto-reconnecting every 2 seconds...
            </span>
          </div>
        </div>
      )}

      {/* Mobile-Friendly Main Container */}
      <div className="w-full max-w-md sm:max-w-lg min-h-screen px-4 pt-4 pb-8 flex flex-col">
        
        {/* Top Header Bar */}
        <header className="flex items-center justify-between pb-3">
          
          {/* Logo & Brand Name */}
          <div className="flex items-center">
            {/* Official SU Logo Icon */}
            <img
              src="/su_icon.png"
              alt="STOCK UNDO Logo"
              className="h-10 sm:h-11 w-auto object-contain"
            />

            {/* Vertical Divider */}
            <div className="h-7 w-[1.5px] bg-slate-300 mx-3.5"></div>

            {/* Brand Title */}
            <h1 className="text-2xl sm:text-[26px] font-black tracking-tight text-black font-sans">
              STOCK UNDO!
            </h1>
          </div>

          {/* Refresh Button */}
          <button
            onClick={() => loadStock(true)}
            disabled={isRefreshing}
            className="w-10 h-10 rounded-2xl border border-slate-200 flex items-center justify-center text-slate-800 hover:bg-slate-50 active:scale-95 transition cursor-pointer disabled:opacity-50"
            title="Refresh Stock"
            aria-label="Refresh Stock"
          >
            <RotateCw className={`w-4 h-4 text-slate-800 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        </header>

        {/* Search Bar */}
        <div className="relative mt-1 mb-3">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search model name..."
            autoComplete="off"
            autoCorrect="off"
            spellCheck="false"
            className="w-full bg-[#FAFAFA] border border-slate-200 rounded-xl pl-10 pr-9 py-2.5 text-sm font-medium text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-300 focus:bg-white transition"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-700 cursor-pointer"
              aria-label="Clear Search"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Meta / Model Count */}
        <div className="text-xs font-bold text-slate-900 px-1 mb-2.5">
          <span>
            {searchQuery.trim()
              ? `${filteredItems.length} of ${stockItems.length} Models`
              : `All ${stockItems.length} Models`}
          </span>
        </div>

        {/* Subtle Horizontal Divider */}
        <div className="border-b border-slate-100 mb-3"></div>

        {/* Content: All Models Listed */}
        <div className="flex-1 space-y-2.5">
          
          {/* Loading Skeletons */}
          {isLoading && stockItems.length === 0 ? (
            <div className="space-y-2.5 py-2">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div key={i} className="p-4 bg-slate-50 border border-slate-200 rounded-2xl animate-pulse flex items-center justify-between">
                  <div className="h-4 bg-slate-200 rounded w-1/2"></div>
                  <div className="h-8 bg-slate-200 rounded w-16"></div>
                </div>
              ))}
            </div>
          ) : filteredItems.length === 0 ? (
            /* Empty State */
            <div className="text-center py-16 px-4">
              <Package className="w-12 h-12 text-slate-300 mx-auto mb-2" />
              <h3 className="text-sm font-bold text-slate-700">No matching model</h3>
              <p className="text-xs text-slate-400 mt-1">
                "{searchQuery}" was not found.
              </p>
            </div>
          ) : (
            /* Model Stock Cards */
            filteredItems.map((item, idx) => {
              const qty = item.available_stock || 0;
              const isAvailable = item.status === 'Available' || qty > 0;
              const isNotFound = item.status === 'Model Not Found';
              const isOffline = item.status === 'Source Offline';
              const changeType = changedModels[item.model];
              const isSelected = selectedModel === item.model;

              return (
                <div
                  key={`${item.model}-${idx}`}
                  onClick={() => setSelectedModel(selectedModel === item.model ? null : item.model)}
                  className={`rounded-2xl p-4 flex items-center justify-between transition-all duration-200 cursor-pointer select-none ${
                    isSelected || changeType
                      ? 'border-2 border-[#FACC15] bg-white shadow-xs'
                      : 'border border-slate-200 bg-white hover:border-slate-300 shadow-2xs'
                  }`}
                >
                  {/* Model Name (Left) */}
                  <div className="flex-1 min-w-0 pr-3">
                    <h2 className="text-sm sm:text-[15px] font-bold text-slate-950 leading-snug break-words font-sans">
                      {item.model}
                    </h2>
                  </div>

                  {/* Quantity & In Stock Badge (Right) */}
                  <div className="shrink-0 flex flex-col items-end">
                    {isAvailable ? (
                      <>
                        <div className="px-3 py-1 rounded-xl bg-[#DCFCE7] text-slate-950 flex items-center gap-1.5">
                          <span className="text-base sm:text-lg font-black font-sans leading-none tracking-tight">
                            {qty}
                          </span>
                          <span className="text-xs font-bold uppercase text-slate-800">
                            {item.unit || 'NO'}
                          </span>
                        </div>
                        <span className="text-xs font-bold text-[#16A34A] mt-1">
                          In Stock
                        </span>
                      </>
                    ) : isNotFound ? (
                      <span className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-500 text-xs font-bold">
                        Not Found
                      </span>
                    ) : isOffline ? (
                      <span className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-500 text-xs font-bold">
                        Offline
                      </span>
                    ) : (
                      <>
                        <div className="px-3 py-1 rounded-xl bg-amber-50 border border-amber-200 text-slate-800 flex items-center gap-1.5">
                          <span className="text-base sm:text-lg font-black font-sans leading-none text-slate-600">
                            0
                          </span>
                          <span className="text-xs font-bold uppercase text-slate-600">
                            {item.unit || 'NO'}
                          </span>
                        </div>
                        <span className="text-xs font-bold text-amber-700 mt-1">
                          Out of Stock
                        </span>
                      </>
                    )}
                  </div>
                </div>
              );
            })
          )}

        </div>

      </div>

    </div>
  );
}
