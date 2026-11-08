import React from 'react';
import { RotateCw, Server, AlertCircle, CheckCircle2, ShieldCheck } from 'lucide-react';

export default function Header({
  pc1Status,
  pc2Status,
  onRefresh,
  isRefreshing,
  countdown,
  lastUpdated,
}) {
  return (
    <header className="bg-slate-900 text-white border-b border-slate-800 shadow-md sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between py-3.5 gap-3">
          
          {/* Logo & Tagline */}
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-xl bg-slate-800 p-1.5 flex items-center justify-center shadow-inner border border-slate-700 shrink-0">
              <img
                src="/logo.svg"
                alt="STOCK UNDO! Logo"
                className="w-full h-full object-contain"
              />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight text-white flex items-center">
                  STOCK <span className="text-amber-400 ml-1">UNDO!</span>
                </h1>
                <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
                  <ShieldCheck className="w-3 h-3" /> READ-ONLY
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-300 font-medium">
                "Check stock before you call the godown!"
              </p>
            </div>
          </div>

          {/* Right Section: Tally Connection Badges & Refresh Controls */}
          <div className="flex flex-wrap items-center gap-2.5 sm:gap-3.5">
            
            {/* PC 1 Status Badge */}
            <div
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                pc1Status?.online
                  ? 'bg-emerald-950/70 border-emerald-700/80 text-emerald-300'
                  : 'bg-rose-950/60 border-rose-800/80 text-rose-300'
              }`}
              title={pc1Status?.online ? `Online (${pc1Status.latency_ms}ms) - ${pc1Status.open_company || 'Active'}` : `Offline: ${pc1Status?.error || 'Closed'}`}
            >
              <span className="relative flex h-2.5 w-2.5">
                {pc1Status?.online && (
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                )}
                <span
                  className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                    pc1Status?.online ? 'bg-emerald-500' : 'bg-rose-500'
                  }`}
                ></span>
              </span>
              <span className="font-mono">PC 1 (Central)</span>
              {pc1Status?.online ? (
                <span className="text-[10px] opacity-75 font-normal">
                  {pc1Status.latency_ms}ms
                </span>
              ) : (
                <span className="text-[10px] opacity-75">Offline</span>
              )}
            </div>

            {/* PC 2 Status Badge (Tailscale) */}
            <div
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                pc2Status?.online
                  ? 'bg-emerald-950/70 border-emerald-700/80 text-emerald-300'
                  : 'bg-rose-950/60 border-rose-800/80 text-rose-300'
              }`}
              title={pc2Status?.online ? `Online (${pc2Status.latency_ms}ms) via Tailscale - ${pc2Status.open_company || 'Active'}` : `Offline: ${pc2Status?.error || 'Unreachable'}`}
            >
              <span className="relative flex h-2.5 w-2.5">
                {pc2Status?.online && (
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                )}
                <span
                  className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                    pc2Status?.online ? 'bg-emerald-500' : 'bg-rose-500'
                  }`}
                ></span>
              </span>
              <span className="font-mono">PC 2 (Godown)</span>
              {pc2Status?.online ? (
                <span className="text-[10px] opacity-75 font-normal">
                  {pc2Status.latency_ms}ms
                </span>
              ) : (
                <span className="text-[10px] opacity-75">Offline</span>
              )}
            </div>

            {/* Auto-Refresh Timer & Manual Button */}
            <div className="flex items-center gap-2 pl-1 border-l border-slate-800">
              <span className="text-xs text-slate-400 font-mono hidden lg:inline" title="Next auto-refresh">
                {countdown}s
              </span>
              <button
                onClick={onRefresh}
                disabled={isRefreshing}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 active:scale-95 text-slate-950 font-bold text-xs transition shadow hover:shadow-amber-500/20 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer"
                title="Force refresh stock from both Tally installations"
              >
                <RotateCw
                  className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`}
                />
                <span>{isRefreshing ? 'Checking...' : 'Refresh'}</span>
              </button>
            </div>

          </div>

        </div>
      </div>
    </header>
  );
}

