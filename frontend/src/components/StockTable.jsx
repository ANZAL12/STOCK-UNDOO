import React from 'react';
import {
  Package,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  WifiOff,
  Building2,
  Warehouse,
  Boxes,
} from 'lucide-react';

export default function StockTable({
  items = [],
  searchQuery,
  onSearchChange,
  sourceFilter,
  onSourceFilterChange,
  availabilityFilter,
  onAvailabilityFilterChange,
  isLoading,
}) {
  // Client-side filtering over whitelist models
  const filteredItems = items.filter((item) => {
    // 1. Search Query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      const modelMatch = item.model.toLowerCase().includes(q);
      if (!modelMatch) return false;
    }

    // 2. Source Filter
    if (sourceFilter === 'pc1' && !item.source.includes('PC 1')) return false;
    if (sourceFilter === 'pc2' && !item.source.includes('PC 2')) return false;

    // 3. Availability Filter
    if (availabilityFilter === 'available' && item.status !== 'Available') return false;
    if (availabilityFilter === 'out_of_stock' && item.status !== 'Out of Stock') return false;

    return true;
  });

  return (
    <div className="space-y-4">
      {/* Search & Filter Toolbar */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 transition">
        <div className="flex flex-col md:flex-row gap-3 md:items-center md:justify-between">
          
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search model name (e.g., FORMENTY, CARRIER, GENERAL)..."
              className="w-full pl-10 pr-4 py-2 text-sm bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-500/40 focus:border-amber-500 text-slate-800 placeholder-slate-400 transition"
            />
            {searchQuery && (
              <button
                onClick={() => onSearchChange('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-600 bg-slate-200 px-1.5 py-0.5 rounded cursor-pointer"
              >
                Clear
              </button>
            )}
          </div>

          {/* Filter Pills */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {/* Source Segmented Control */}
            <div className="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-100">
              <button
                onClick={() => onSourceFilterChange('all')}
                className={`px-3 py-1.5 rounded-md font-semibold transition cursor-pointer ${
                  sourceFilter === 'all'
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                All Sources
              </button>
              <button
                onClick={() => onSourceFilterChange('pc1')}
                className={`px-3 py-1.5 rounded-md font-semibold transition cursor-pointer flex items-center gap-1.5 ${
                  sourceFilter === 'pc1'
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Building2 className="w-3 h-3 text-amber-400" />
                PC 1 Central
              </button>
              <button
                onClick={() => onSourceFilterChange('pc2')}
                className={`px-3 py-1.5 rounded-md font-semibold transition cursor-pointer flex items-center gap-1.5 ${
                  sourceFilter === 'pc2'
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Warehouse className="w-3 h-3 text-emerald-400" />
                PC 2 Godown
              </button>
            </div>

            {/* Availability Filter Toggle */}
            <select
              value={availabilityFilter}
              onChange={(e) => onAvailabilityFilterChange(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-slate-200 bg-slate-50 font-medium text-slate-700 hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-amber-500/40 text-xs cursor-pointer"
            >
              <option value="all">All Statuses</option>
              <option value="available">Available Only (&gt; 0)</option>
              <option value="out_of_stock">Out of Stock Only</option>
            </select>
          </div>

        </div>

        {/* Counter and Whitelist Notice */}
        <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between text-xs text-slate-500 gap-2">
          <div className="flex items-center gap-1.5">
            <Boxes className="w-3.5 h-3.5 text-slate-400" />
            <span>
              Showing <strong className="text-slate-800">{filteredItems.length}</strong> entries (Strict Whitelist Scope)
            </span>
          </div>
          <span className="text-[11px] text-slate-400 italic">
            * Strictly read-only closing balances. No financial or pricing data is retrieved.
          </span>
        </div>
      </div>

      {/* Stock Items Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        {isLoading && items.length === 0 ? (
          /* Loading Skeletons */
          <div className="p-8 space-y-4">
            <div className="flex items-center justify-center gap-2 text-slate-500 text-sm font-medium">
              <div className="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
              <span>Connecting to TallyPrime installations...</span>
            </div>
            {[1, 2, 3, 4, 5].map((n) => (
              <div key={n} className="h-12 bg-slate-100 animate-pulse rounded-lg"></div>
            ))}
          </div>
        ) : filteredItems.length === 0 ? (
          /* Empty / No Matches State */
          <div className="text-center py-16 px-4">
            <Package className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <h3 className="text-base font-bold text-slate-700">No matching whitelist models</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1">
              {searchQuery
                ? `No models matching "${searchQuery}" were found in the configured whitelist.`
                : 'No stock items match your selected filters.'}
            </p>
          </div>
        ) : (
          /* Responsive Table */
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-900 text-slate-200 text-xs uppercase tracking-wider font-bold border-b border-slate-800">
                  <th scope="col" className="py-3 px-4 sm:px-6">Model</th>
                  <th scope="col" className="py-3 px-4 sm:px-6 text-right">Available Stock</th>
                  <th scope="col" className="py-3 px-4 sm:px-6 text-center">Unit</th>
                  <th scope="col" className="py-3 px-4 sm:px-6">Source</th>
                  <th scope="col" className="py-3 px-4 sm:px-6 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm">
                {filteredItems.map((item, idx) => {
                  const isAvailable = item.status === 'Available';
                  const isOutOfStock = item.status === 'Out of Stock';
                  const isNotFound = item.status === 'Model Not Found';
                  const isOffline = item.status === 'Source Offline';

                  return (
                    <tr
                      key={`${item.source}-${item.model}-${idx}`}
                      className="hover:bg-amber-50/40 transition-colors group"
                    >
                      {/* Model Name */}
                      <td className="py-3.5 px-4 sm:px-6">
                        <div className="font-semibold text-slate-900 group-hover:text-amber-950 transition">
                          {item.model}
                        </div>
                      </td>

                      {/* Available Stock Quantity */}
                      <td className="py-3.5 px-4 sm:px-6 text-right font-mono">
                        <span
                          className={`inline-block px-2.5 py-1 rounded-md text-base font-extrabold ${
                            isAvailable
                              ? 'bg-emerald-100 text-emerald-900 font-black'
                              : isOutOfStock
                              ? 'bg-amber-100 text-amber-900'
                              : 'bg-slate-100 text-slate-500'
                          }`}
                        >
                          {isOffline ? '-' : isNotFound ? '-' : item.available_stock}
                        </span>
                      </td>

                      {/* Unit */}
                      <td className="py-3.5 px-4 sm:px-6 text-center text-xs text-slate-500 font-medium">
                        {item.unit || 'Nos'}
                      </td>

                      {/* Source Badge */}
                      <td className="py-3.5 px-4 sm:px-6">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold ${
                            item.source.includes('PC 1')
                              ? 'bg-blue-50 text-blue-800 border border-blue-200'
                              : 'bg-indigo-50 text-indigo-800 border border-indigo-200'
                          }`}
                        >
                          {item.source.includes('PC 1') ? (
                            <Building2 className="w-3 h-3 text-blue-600" />
                          ) : (
                            <Warehouse className="w-3 h-3 text-indigo-600" />
                          )}
                          {item.source}
                        </span>
                      </td>

                      {/* Status Badge */}
                      <td className="py-3.5 px-4 sm:px-6 text-center">
                        {isAvailable && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                            Available
                          </span>
                        )}
                        {isOutOfStock && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                            Out of Stock
                          </span>
                        )}
                        {isNotFound && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-300">
                            <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
                            Model Not Found
                          </span>
                        )}
                        {isOffline && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200">
                            <WifiOff className="w-3.5 h-3.5 text-rose-500" />
                            Source Offline
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

