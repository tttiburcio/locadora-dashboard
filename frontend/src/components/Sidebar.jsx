import { LayoutDashboard, Truck, ChevronDown } from 'lucide-react'
import { useState } from 'react'

const LEGEND = [
  { color: '#6366f1', label: 'Locação' },
  { color: '#8b5cf6', label: 'Reembolsos' },
  { color: '#f97316', label: 'Manutenção' },
  { color: '#ef4444', label: 'Seguro' },
  { color: '#a855f7', label: 'Impostos' },
  { color: '#f59e0b', label: 'Rastreamento' },
]

export default function Sidebar({ page, setPage, years, year, setYear }) {
  const [showYears, setShowYears] = useState(false)

  return (
    <aside className="w-56 shrink-0 flex flex-col bg-g-950 border-r border-g-900 h-screen">
      {/* Logo */}
      <div className="px-4 pt-5 pb-4 border-b border-g-900">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-g-800 rounded-lg flex items-center justify-center text-base border border-g-700">
            🚛
          </div>
          <div>
            <p className="text-g-50 font-bold text-sm leading-none tracking-tight">Locadora</p>
            <p className="text-g-600 text-xs mt-0.5">Fleet Analytics</p>
          </div>
        </div>
      </div>

      {/* Year selector */}
      <div className="px-3 pt-4 pb-2">
        <p className="text-g-600 text-xs uppercase tracking-widest font-semibold mb-2 px-1">Período</p>
        <div className="relative">
          <button
            onClick={() => setShowYears(v => !v)}
            className="w-full flex items-center justify-between px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-200 text-sm hover:border-g-700 transition-colors"
          >
            <span className="font-semibold font-mono">{year || '—'}</span>
            <ChevronDown className={`w-3.5 h-3.5 text-g-600 transition-transform duration-200 ${showYears ? 'rotate-180' : ''}`} />
          </button>
          {showYears && (
            <div className="absolute top-full mt-1 left-0 right-0 bg-g-900 border border-g-700 rounded-lg shadow-2xl z-20 overflow-hidden animate-fade-in">
              {years.map(y => (
                <button
                  key={y}
                  onClick={() => { setYear(y); setShowYears(false) }}
                  className={`w-full text-left px-3 py-2 text-sm transition-colors font-mono ${
                    y === year
                      ? 'bg-white/10 text-white font-bold'
                      : 'text-g-400 hover:bg-g-800 hover:text-g-100'
                  }`}
                >
                  {y}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="px-3 pt-2 flex flex-col gap-0.5">
        <p className="text-g-600 text-xs uppercase tracking-widest font-semibold mb-1.5 px-1 mt-2">Menu</p>
        <button
          onClick={() => setPage('overview')}
          className={`nav-item ${page === 'overview' ? 'nav-item-active' : 'nav-item-inactive'}`}
        >
          <LayoutDashboard className="w-4 h-4 shrink-0" />
          Visão Geral
        </button>
        <button
          onClick={() => setPage('vehicles')}
          className={`nav-item ${page === 'vehicles' ? 'nav-item-active' : 'nav-item-inactive'}`}
        >
          <Truck className="w-4 h-4 shrink-0" />
          Frota
        </button>
      </nav>

      {/* Legend */}
      <div className="mt-auto px-3 py-4 border-t border-g-900">
        <p className="text-g-600 text-xs uppercase tracking-widest font-semibold mb-3 px-1">Categorias</p>
        <div className="space-y-2">
          {LEGEND.map(({ color, label }) => (
            <div key={label} className="flex items-center gap-2.5">
              <span
                className="w-2 h-2 rounded-sm shrink-0"
                style={{ background: color }}
              />
              <span className="text-g-500 text-xs">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </aside>
  )
}
