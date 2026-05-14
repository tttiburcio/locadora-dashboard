import { useState, useEffect, useCallback } from 'react'
import { getYears, getKpis, getMonthly, getVehicles, getRegions, runSync } from './utils/api'
import Sidebar from './components/Sidebar'
import OverviewPage from './pages/OverviewPage'
import VehiclesPage from './pages/VehiclesPage'
import MaintenancePage from './pages/MaintenancePage'
import { ThemeProvider } from './contexts/ThemeContext'
import { Loader2, Plus, Menu, RefreshCw } from 'lucide-react'

const HEADER_ACTIONS = {}

export default function App() {
  const [page, setPage]           = useState('overview')
  const [headerTrigger, setHeaderTrigger] = useState({})
  const [years, setYears]       = useState([])
  const [year, setYear]         = useState(null)
  const [kpis, setKpis]         = useState(null)
  const [monthly, setMonthly]   = useState([])
  const [vehicles, setVehicles] = useState([])
  const [regions, setRegions]   = useState([])
  const [region, setRegion]     = useState(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [isMobileMenuOpen, setIsMobileMenuOpen]     = useState(false)
  const [finAlertDismissed, setFinAlertDismissed]   = useState(false)
  const [trackerFilter, setTrackerFilter]           = useState(null)

  useEffect(() => {
    getYears()
      .then(d => {
        setYears(d.years)
        if (d.years.length > 0) setYear(d.years[0])
      })
      .catch(() => setError('Não foi possível conectar ao servidor. Verifique se o backend está rodando.'))
  }, [])

  const loadData = useCallback(async (y, r) => {
    if (!y) return
    setLoading(true)
    setError(null)
    try {
      const [k, m, v, reg] = await Promise.all([
        getKpis(y),
        getMonthly(y),
        getVehicles(y, r),
        getRegions(y),
      ])
      setKpis(k)
      setMonthly(m.monthly || [])
      setVehicles(v.vehicles || [])
      setRegions(reg.regions || [])
    } catch {
      setError('Erro ao carregar os dados. Verifique a conexão com o backend.')
    } finally {
      setLoading(false)
    }
  }, [])

  const handleRefresh = useCallback(async () => {
    runSync().catch(() => {})
    try {
      setLoading(true)
      const d = await getYears()
      setYears(d.years)
      if (d.years.length > 0 && !year) setYear(d.years[0])
      await loadData(year, region)
    } catch {
      setError('Erro ao atualizar os dados.')
    } finally {
      setLoading(false)
    }
  }, [year, region, loadData])

  useEffect(() => { loadData(year, region) }, [year, region, loadData])

  const handleRegionChange = (r) => { setRegion(r || null) }

  if (error && !year) {
    return (
      <ThemeProvider>
      <div className="flex h-screen items-center justify-center bg-g-950">
        <div className="text-center p-8 card rounded-2xl max-w-md animate-fade-in">
          <div className="w-16 h-16 mx-auto mb-4">
            <img src="/icon.png" alt="TKJ" className="w-full h-full object-contain opacity-40" />
          </div>
          <h2 className="text-g-100 text-xl font-semibold mb-2">Erro de Conexão</h2>
          <p className="text-g-400 text-sm">{error}</p>
          <p className="text-g-600 text-xs mt-4">
            Inicie o backend:{' '}
            <code className="text-g-300 bg-g-800 px-1.5 py-0.5 rounded font-mono text-xs">
              uvicorn main:app --reload
            </code>
          </p>
        </div>
      </div>
      </ThemeProvider>
    )
  }

  const pageTitle = {
    overview:    'Visão Geral',
    vehicles:    'Frota — Detalhamento',
    maintenance: 'Análise de Manutenção',
  }

  return (
    <ThemeProvider>
    <div className="flex h-screen overflow-hidden bg-g-950">
      <Sidebar
        page={page}
        setPage={setPage}
        years={years}
        year={year}
        setYear={setYear}
        isCollapsed={isSidebarCollapsed}
        setIsCollapsed={setIsSidebarCollapsed}
        isMobileOpen={isMobileMenuOpen}
        setIsMobileOpen={setIsMobileMenuOpen}
      />

      <main className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-g-900/95 backdrop-blur-sm border-b border-g-800 px-4 sm:px-6 py-3.5 flex items-center justify-between no-print">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsMobileMenuOpen(true)}
              className="p-1.5 -ml-1.5 rounded-lg text-g-600 hover:text-g-300 hover:bg-g-850 transition-colors block md:hidden"
            >
              <Menu className="w-5 h-5" />
            </button>
            <img src="/icon.png" alt="" className="w-5 h-5 object-contain opacity-50 hidden sm:block" />
            <div>
              <h1 className="text-g-200 font-bold text-lg tracking-wide">
                {pageTitle[page]}
              </h1>
              <p className="text-g-600 text-sm mt-0.5 font-medium">
                TKJ Gerenciamento · Exercício {year}
                {region && <span className="ml-2 text-g-100">· {region}</span>}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {loading && (
              <div className="flex items-center gap-2 text-g-600 text-xs">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Atualizando…
              </div>
            )}
            {error && !loading && <span className="text-red-500 text-xs">{error}</span>}

            <button
              onClick={handleRefresh}
              disabled={loading}
              title="Atualizar dados"
              className="flex items-center gap-1.5 px-3 py-1.5 bg-g-850 border border-g-700 text-g-100 hover:bg-g-800 hover:text-white rounded-lg transition-colors cursor-pointer text-xs font-semibold shadow-sm hover:shadow active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Atualizar
            </button>

            {/* Ações contextuais por página */}
            {HEADER_ACTIONS[page]?.map(action => (
              <button
                key={action.key}
                onClick={() => setHeaderTrigger(t => ({ ...t, [action.key]: (t[action.key] || 0) + 1 }))}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-g-100 text-white text-xs font-semibold rounded-lg hover:bg-g-50 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                {action.label}
              </button>
            ))}
          </div>
        </div>

        <div className="p-4 py-6">
          {loading && (
            <div className="flex flex-col items-center justify-center h-96 gap-4 animate-fade-in">
              <img src="/icon.png" alt="" className="w-12 h-12 object-contain opacity-30 animate-pulse-slow" />
              <p className="text-g-500 text-sm">Carregando dados de {year}…</p>
            </div>
          )}

          {!loading && kpis && page === 'overview' && (
            <div key={`overview-${year}`} className="animate-page-fade">
              <OverviewPage
                kpis={kpis} monthly={monthly} vehicles={vehicles} year={year}
                setPage={setPage}
                setTrackerFilter={setTrackerFilter}
              />
            </div>
          )}

          {!loading && page === 'vehicles' && (
            <div key={`vehicles-${year}-${region}`} className="animate-page-fade">
              <VehiclesPage
                vehicles={vehicles}
                year={year}
                regions={regions}
                region={region}
                onRegionChange={handleRegionChange}
                trackerFilter={trackerFilter}
                onTrackerFilterConsumed={() => setTrackerFilter(null)}
              />
            </div>
          )}

          {!loading && page === 'maintenance' && (
            <div key={`maintenance-${year}`} className="animate-page-fade">
              <MaintenancePage 
                year={year} 
                vehicles={vehicles} 
                headerTrigger={headerTrigger} 
                finAlertDismissed={finAlertDismissed}
                setFinAlertDismissed={setFinAlertDismissed}
                onRefreshData={() => loadData(year, region)}
              />
            </div>
          )}
        </div>
      </main>
    </div>
    </ThemeProvider>
  )
}
