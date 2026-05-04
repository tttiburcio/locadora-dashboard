import { LayoutDashboard, Truck, Wrench, ChevronDown, Menu, X } from 'lucide-react'
import { useState } from 'react'

const LEGENDS = {
  overview: [
    { color: '#22c55e', label: 'Locação' },
    { color: '#34d399', label: 'Reembolsos' },
    { color: '#f97316', label: 'Manutenção' },
    { color: '#ef4444', label: 'Seguro' },
    { color: '#a855f7', label: 'Impostos' },
    { color: '#f59e0b', label: 'Rastreamento' },
  ],
  vehicles: [
    { color: '#22c55e', label: 'Locação' },
    { color: '#34d399', label: 'Reembolsos' },
    { color: '#f97316', label: 'Manutenção' },
    { color: '#ef4444', label: 'Seguro' },
    { color: '#a855f7', label: 'Impostos' },
    { color: '#f59e0b', label: 'Rastreamento' },
  ],
  maintenance: [
    { color: '#f59e0b', label: 'Em andamento' },
    { color: '#f97316', label: 'Aguardando peça' },
    { color: '#94a3b8', label: 'Pendente' },
    { color: '#10b981', label: 'Finalizada' },
    { color: '#22c55e', label: 'Preventiva' },
    { color: '#ef4444', label: 'Corretiva' },
  ],
}

const NAV = [
  { key: 'overview',     label: 'Visão Geral',  icon: LayoutDashboard },
  { key: 'vehicles',     label: 'Frota',        icon: Truck },
  { key: 'maintenance',  label: 'Manutenção',   icon: Wrench },
]

export default function Sidebar({ page, setPage, years, year, setYear, isCollapsed, setIsCollapsed, isMobileOpen, setIsMobileOpen }) {
  const legend = LEGENDS[page] || LEGENDS.overview
  const [showYears, setShowYears] = useState(false)

  return (
    <>
      {/* Overlay para mobile */}
      {isMobileOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden backdrop-blur-sm animate-fade-in"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      <aside 
        className={`fixed inset-y-0 left-0 z-50 md:relative md:flex ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        } ${isCollapsed ? 'w-20' : 'w-56'} shrink-0 flex flex-col bg-g-950 border-r border-g-900 h-screen transition-all duration-300 ease-in-out`}
      >
        {/* Topo */}
        <div className={`px-4 pt-2 pb-3 border-b border-g-900 flex flex-col ${isCollapsed ? 'items-center' : ''}`}>
          <div className={`flex items-center justify-between mb-1`}>
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="p-1.5 rounded-lg text-g-600 hover:text-g-300 hover:bg-g-850 transition-colors hidden md:block"
              title={isCollapsed ? 'Expandir menu' : 'Recolher menu'}
            >
              <Menu className="w-5 h-5" />
            </button>
            <button
              onClick={() => setIsMobileOpen(false)}
              className="p-1.5 rounded-lg text-g-600 hover:text-g-300 hover:bg-g-850 transition-colors block md:hidden"
              title="Fechar menu"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

        {!isCollapsed ? (
          <div className="flex flex-col items-center px-1">
            <div className="bg-white rounded-2xl p-2 shadow-sm mb-2 w-full flex justify-center">
              <img
                src="/logo.png"
                alt="TKJ Gerenciamento"
                className="h-24 w-auto object-contain"
              />
            </div>
            <p className="text-g-700 text-[10px] uppercase tracking-widest font-bold text-center">
              Painel de Gestão
            </p>
          </div>
        ) : (
          <div className="mt-2 flex flex-col items-center gap-1 opacity-50">
            <img src="/icon.png" alt="" className="w-6 h-6 object-contain" />
          </div>
        )}
      </div>

      {/* Year selector */}
      <div className={`px-3 pt-4 pb-2 ${isCollapsed ? 'flex justify-center' : ''}`}>
        {!isCollapsed && (
          <p className="text-g-700 text-[10px] uppercase tracking-widest font-semibold mb-2 px-1">Período</p>
        )}
        <div className="relative w-full">
          <button
            onClick={() => setShowYears(v => !v)}
            className={`w-full flex items-center justify-between bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm hover:border-g-750 transition-colors shadow-sm ${
              isCollapsed ? 'px-2 py-2 justify-center' : 'px-3 py-2'
            }`}
          >
            <span className="font-semibold font-mono">{year || '—'}</span>
            {!isCollapsed && (
              <ChevronDown className={`w-3.5 h-3.5 text-g-600 transition-transform duration-200 ${showYears ? 'rotate-180' : ''}`} />
            )}
          </button>
          {showYears && (
            <div className={`absolute mt-1 left-0 right-0 bg-g-900 border border-g-800 rounded-lg shadow-lg z-20 overflow-hidden animate-fade-in ${
              isCollapsed ? 'w-20 -left-1' : ''
            }`}>
              {years.map(y => (
                <button
                  key={y}
                  onClick={() => { setYear(y); setShowYears(false) }}
                  className={`w-full text-left px-3 py-2 text-sm transition-colors font-mono ${
                    y === year
                      ? 'text-g-100 font-bold bg-g-850'
                      : 'text-g-500 hover:bg-g-850 hover:text-g-300'
                  } ${isCollapsed ? 'text-center' : ''}`}
                >
                  {y}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className={`px-3 pt-2 flex flex-col gap-0.5 ${isCollapsed ? 'items-center' : ''}`}>
        {!isCollapsed && (
          <p className="text-g-700 text-[10px] uppercase tracking-widest font-semibold mb-1.5 px-1 mt-2">Menu</p>
        )}
        {NAV.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => { setPage(key); setIsMobileOpen && setIsMobileOpen(false); }}
            className={`nav-item flex items-center gap-3 transition-all duration-200 ${
              page === key ? 'nav-item-active' : 'nav-item-inactive'
            } ${isCollapsed ? 'w-10 h-10 justify-center px-0' : 'w-full px-3'}`}
            title={isCollapsed ? label : ''}
          >
            <Icon className="w-5 h-5 shrink-0" />
            {!isCollapsed && <span>{label}</span>}
          </button>
        ))}
      </nav>

      {/* Legend */}
      {!isCollapsed && (
        <div className="mt-auto px-3 pt-4 pb-3 border-t border-g-900">
          <p className="text-g-700 text-[10px] uppercase tracking-widest font-semibold mb-3 px-1">Categorias</p>
          <div className="space-y-2">
            {legend.map(({ color, label }) => (
              <div key={label} className="flex items-center gap-2.5">
                <span className="w-2 h-2 rounded-sm shrink-0" style={{ background: color }} />
                <span className="text-g-600 text-xs">{label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {isCollapsed && (
        <div className="mt-auto px-3 pt-4 pb-4 border-t border-g-900 flex justify-center">
          <div className="flex flex-col gap-2 items-center">
             <div className="w-2 h-2 rounded-full bg-g-500" />
          </div>
        </div>
      )}
      </aside>
    </>
  )
}
