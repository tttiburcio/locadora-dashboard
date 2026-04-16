import { useState, useEffect, useCallback } from 'react'
import { getYears, getKpis, getMonthly, getVehicles } from './utils/api'
import Sidebar from './components/Sidebar'
import OverviewPage from './pages/OverviewPage'
import VehiclesPage from './pages/VehiclesPage'
import { Loader2 } from 'lucide-react'

export default function App() {
  const [page, setPage]           = useState('overview')
  const [years, setYears]         = useState([])
  const [year, setYear]           = useState(null)
  const [kpis, setKpis]           = useState(null)
  const [monthly, setMonthly]     = useState([])
  const [vehicles, setVehicles]   = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)

  // Load year list once
  useEffect(() => {
    getYears()
      .then(d => {
        setYears(d.years)
        if (d.years.length > 0) setYear(d.years[0])
      })
      .catch(() => setError('Não foi possível conectar ao servidor. Verifique se o backend está rodando.'))
  }, [])

  // Load data when year changes
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

  useEffect(() => {
    loadData(year)
  }, [year, loadData])

  if (error && !year) {
    return (
      <div className="flex h-screen items-center justify-center bg-g-950">
        <div className="text-center p-8 card rounded-2xl max-w-md">
          <div className="text-4xl mb-4">⚠️</div>
          <h2 className="text-g-100 text-xl font-semibold mb-2">Erro de Conexão</h2>
          <p className="text-g-400 text-sm">{error}</p>
          <p className="text-g-500 text-xs mt-4">Inicie o backend com: <code className="text-g-300 bg-g-900 px-1 rounded">uvicorn main:app --reload</code></p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen overflow-hidden bg-g-950">
      <Sidebar
        page={page}
        setPage={setPage}
        years={years}
        year={year}
        setYear={setYear}
      />

      <main className="flex-1 overflow-y-auto">
        {/* Header bar */}
        <div className="sticky top-0 z-10 bg-g-950/90 backdrop-blur-sm border-b border-g-900 px-6 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-g-100 font-semibold text-base">
              {page === 'overview' ? 'Visão Geral' : 'Frota — Detalhamento'}
            </h1>
            <p className="text-g-500 text-xs mt-0.5">
              Dashboard Financeiro · Exercício {year}
            </p>
          </div>
          {loading && (
            <div className="flex items-center gap-2 text-g-400 text-xs">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Atualizando dados…
            </div>
          )}
          {error && !loading && (
            <span className="text-red-400 text-xs">{error}</span>
          )}
        </div>

        <div className="p-6">
          {!loading && kpis && page === 'overview' && (
            <OverviewPage kpis={kpis} monthly={monthly} vehicles={vehicles} year={year} />
          )}
          {!loading && page === 'vehicles' && (
            <VehiclesPage vehicles={vehicles} year={year} />
          )}
          {loading && (
            <div className="flex flex-col items-center justify-center h-96 gap-4">
              <Loader2 className="w-8 h-8 animate-spin text-g-500" />
              <p className="text-g-400 text-sm">Processando dados de {year}…</p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
