import { useState, useEffect, useCallback } from 'react'
import { getYears, getKpis, getMonthly, getVehicles } from './utils/api'
import Sidebar from './components/Sidebar'
import OverviewPage from './pages/OverviewPage'
import VehiclesPage from './pages/VehiclesPage'
import { Loader2 } from 'lucide-react'

export default function App() {
  const [page, setPage]         = useState('overview')
  const [years, setYears]       = useState([])
  const [year, setYear]         = useState(null)
  const [kpis, setKpis]         = useState(null)
  const [monthly, setMonthly]   = useState([])
  const [vehicles, setVehicles] = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)

  useEffect(() => {
    getYears()
      .then(d => {
        setYears(d.years)
        if (d.years.length > 0) setYear(d.years[0])
      })
      .catch(() => setError('Não foi possível conectar ao servidor. Verifique se o backend está rodando.'))
  }, [])

  const loadData = useCallback(async (y) => {
    if (!y) return
    setLoading(true)
    setError(null)
    try {
      const [k, m, v] = await Promise.all([getKpis(y), getMonthly(y), getVehicles(y)])
      setKpis(k)
      setMonthly(m.monthly || [])
      setVehicles(v.vehicles || [])
    } catch {
      setError('Erro ao carregar os dados. Verifique a conexão com o backend.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadData(year) }, [year, loadData])

  if (error && !year) {
    return (
      <div className="flex h-screen items-center justify-center bg-g-950">
        <div className="text-center p-8 card rounded-2xl max-w-md animate-fade-in">
          <div className="text-4xl mb-4">⚠️</div>
          <h2 className="text-g-100 text-xl font-semibold mb-2">Erro de Conexão</h2>
          <p className="text-g-400 text-sm">{error}</p>
          <p className="text-g-600 text-xs mt-4">
            Inicie o backend com:{' '}
            <code className="text-g-300 bg-g-800 px-1.5 py-0.5 rounded font-mono text-xs">
              uvicorn main:app --reload
            </code>
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden bg-g-950">
      <Sidebar page={page} setPage={setPage} years={years} year={year} setYear={setYear} />

      <main className="flex-1 overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-g-950/95 backdrop-blur-sm border-b border-g-900 px-6 py-3.5 flex items-center justify-between">
          <div>
            <h1 className="text-g-50 font-semibold text-sm tracking-wide">
              {page === 'overview' ? 'Visão Geral' : 'Frota — Detalhamento'}
            </h1>
            <p className="text-g-600 text-xs mt-0.5">
              Dashboard Financeiro · Exercício {year}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {loading && (
              <div className="flex items-center gap-2 text-g-500 text-xs">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Atualizando…
              </div>
            )}
            {error && !loading && (
              <span className="text-red-400 text-xs">{error}</span>
            )}
          </div>
        </div>

        {/* Page content — key triggers re-animation on page change */}
        <div className="p-6">
          {loading && (
            <div className="flex flex-col items-center justify-center h-96 gap-4 animate-fade-in">
              <Loader2 className="w-7 h-7 animate-spin text-g-600" />
              <p className="text-g-500 text-sm">Carregando dados de {year}…</p>
            </div>
          )}

          {!loading && kpis && page === 'overview' && (
            <div key={`overview-${year}`} className="animate-page-fade">
              <OverviewPage kpis={kpis} monthly={monthly} vehicles={vehicles} year={year} />
            </div>
          )}

          {!loading && page === 'vehicles' && (
            <div key={`vehicles-${year}`} className="animate-page-fade">
              <VehiclesPage vehicles={vehicles} year={year} />
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
