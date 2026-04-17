import { LayoutDashboard, Truck, Wrench, ChevronDown, Sun, Moon } from 'lucide-react'
import { useState } from 'react'
import { useTheme } from '../contexts/ThemeContext'

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

export default function Sidebar({ page, setPage, years, year, setYear }) {
  const legend = LEGENDS[page] || LEGENDS.overview
  const [showYears, setShowYears] = useState(false)
  const { theme, toggle } = useTheme()

  return (
    <aside className="w-56 shrink-0 flex flex-col bg-g-950 border-r border-g-900 h-screen">
      {/* Logo */}
      <div className="px-4 pt-4 pb-3 border-b border-g-900">
        <div className="flex items-center justify-between">
          <div className="bg-white rounded-lg px-2 py-1.5 inline-flex">
            <img
              src="/logo.png"
              alt="TKJ Gerenciamento"
              className="h-7 w-auto object-contain object-left"
            />
          </div>
          <button
            onClick={toggle}
            className="p-1.5 rounded-lg text-g-600 hover:text-g-300 hover:bg-g-850 border border-transparent hover:border-g-800 transition-colors"
            title={theme === 'dark' ? 'Modo claro' : 'Modo escuro'}
          >
            {theme === 'dark'
              ? <Sun className="w-4 h-4" />
              : <Moon className="w-4 h-4" />}
          </button>
        </div>
        <p className="text-g-700 text-[10px] mt-1.5 uppercase tracking-widest font-medium pl-0.5">
          Dados Analíticos
        </p>
      </div>

      {/* Year selector */}
      <div className="px-3 pt-4 pb-2">
        <p className="text-g-700 text-[10px] uppercase tracking-widest font-semibold mb-2 px-1">Período</p>
        <div className="relative">
          <button
            onClick={() => setShowYears(v => !v)}
            className="w-full flex items-center justify-between px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm hover:border-g-750 transition-colors shadow-sm"
          >
            <span className="font-semibold font-mono">{year || '—'}</span>
            <ChevronDown className={`w-3.5 h-3.5 text-g-600 transition-transform duration-200 ${showYears ? 'rotate-180' : ''}`} />
          </button>
          {showYears && (
            <div className="absolute top-full mt-1 left-0 right-0 bg-g-900 border border-g-800 rounded-lg shadow-lg z-20 overflow-hidden animate-fade-in">
              {years.map(y => (
                <button
                  key={y}
                  onClick={() => { setYear(y); setShowYears(false) }}
                  className={`w-full text-left px-3 py-2 text-sm transition-colors font-mono ${
                    y === year
                      ? 'text-g-100 font-bold bg-g-850'
                      : 'text-g-500 hover:bg-g-850 hover:text-g-300'
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
        <p className="text-g-700 text-[10px] uppercase tracking-widest font-semibold mb-1.5 px-1 mt-2">Menu</p>
        {NAV.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setPage(key)}
            className={`nav-item ${page === key ? 'nav-item-active' : 'nav-item-inactive'}`}
          >
            <Icon className="w-4 h-4 shrink-0" />
            {label}
          </button>
        ))}
      </nav>

      {/* Legend */}
      <div className="mt-auto px-3 py-4 border-t border-g-900">
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
    </aside>
  )
}
