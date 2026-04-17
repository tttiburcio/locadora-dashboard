import { useEffect, useState, useMemo } from 'react'
import { getMaintenanceAnalysis } from '../utils/api'
import { brl, brlShort, num } from '../utils/format'
import KPICard from '../components/KPICard'
import {
  FornecedorChart, SistemaTreemap, TipoPie,
  ImplementoRadial, TrendProjectionChart, ServicosChart,
} from '../components/charts/MaintenanceCharts'
import {
  Wrench, DollarSign, Hash, Award, Search, X,
  Calendar, AlertTriangle, ChevronDown, ChevronUp,
  Activity, Loader2, TrendingUp,
} from 'lucide-react'

function Section({ title, icon: Icon, children, className = '' }) {
  return (
    <section className={className}>
      <div className="flex items-center gap-2.5 mb-4">
        <div className="p-1.5 bg-g-850 border border-g-800 rounded-lg">
          <Icon className="w-4 h-4 text-g-500" />
        </div>
        <h2 className="text-g-300 font-semibold text-xs uppercase tracking-widest">{title}</h2>
        <div className="flex-1 h-px bg-g-900" />
      </div>
      {children}
    </section>
  )
}

function ChartCard({ title, subtitle, children, className = '' }) {
  return (
    <div className={`card p-4 ${className}`}>
      <p className="text-g-500 text-xs font-semibold uppercase tracking-widest mb-0.5">{title}</p>
      {subtitle && <p className="text-g-700 text-xs mb-4">{subtitle}</p>}
      {!subtitle && <div className="mb-4" />}
      {children}
    </div>
  )
}

export default function MaintenancePage({ year, vehicles = [] }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [placa, setPlaca]     = useState('')
  const [input, setInput]     = useState('')
  const [upcomingOpen, setUpcomingOpen] = useState(true)

  const placas = useMemo(() =>
    [...new Set(vehicles.map(v => v.placa))].sort(),
    [vehicles]
  )

  const load = (yr, p) => {
    setLoading(true)
    getMaintenanceAnalysis(yr, p || undefined)
      .then(setData)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(year, placa) }, [year, placa])

  const handleSearch = () => {
    const v = input.trim().toUpperCase()
    setPlaca(v)
  }
  const clearFilter = () => { setPlaca(''); setInput('') }

  const s = data?.summary

  return (
    <div className="flex flex-col gap-8">

      {/* ── Filtro de placa ── */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-g-600" />
          <input
            list="placa-list"
            placeholder="Filtrar por placa…"
            value={input}
            onChange={e => setInput(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            className="pl-9 pr-10 py-2 bg-g-900 border border-g-800 rounded-lg text-g-200 text-sm placeholder-g-700 focus:outline-none focus:border-g-600 transition-colors w-52 font-mono"
          />
          <datalist id="placa-list">
            {placas.map(p => <option key={p} value={p} />)}
          </datalist>
          {(input || placa) && (
            <button onClick={clearFilter} className="absolute right-2.5 top-1/2 -translate-y-1/2">
              <X className="w-3.5 h-3.5 text-g-600 hover:text-g-300" />
            </button>
          )}
        </div>
        <button
          onClick={handleSearch}
          className="px-4 py-2 bg-g-800 hover:bg-g-700 border border-g-700 rounded-lg text-g-200 text-sm transition-colors"
        >
          Filtrar
        </button>
        {placa && (
          <span className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-950/50 border border-indigo-800/50 rounded-full text-indigo-300 text-xs font-mono">
            <Wrench className="w-3 h-3" />
            {placa}
            <button onClick={clearFilter}><X className="w-3 h-3 ml-0.5" /></button>
          </span>
        )}
        <span className="ml-auto text-g-700 text-xs">
          {placa ? `Análise individual · ${placa}` : `Frota completa · ${year}`}
        </span>
      </div>

      {loading && (
        <div className="flex items-center justify-center h-64 gap-3 animate-fade-in">
          <Loader2 className="w-6 h-6 animate-spin text-g-600" />
          <p className="text-g-600 text-sm">Processando análise de manutenção…</p>
        </div>
      )}

      {!loading && data && (
        <>
          {/* ── KPIs ── */}
          <Section title="Resumo de Manutenção" icon={Wrench}>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <KPICard
                icon={Hash} label="Ordens de Serviço"
                rawValue={s.total_os} formatter={num}
                sub="OS únicas no período" delay={0}
              />
              <KPICard
                icon={DollarSign} label="Custo Total"
                rawValue={s.total_cost} formatter={brlShort}
                sub="Soma todas as OS" delay={55}
              />
              <KPICard
                icon={Activity} label="Custo Médio / OS"
                rawValue={s.avg_per_os} formatter={brlShort}
                sub="Média por ordem de serviço" delay={110}
              />
              <KPICard
                icon={Award} label="Principal Fornecedor"
                value={s.top_fornecedor?.length > 14 ? s.top_fornecedor.slice(0, 13) + '…' : s.top_fornecedor}
                sub={data.by_fornecedor?.[0] ? brl(data.by_fornecedor[0].total) + ' no período' : '—'}
                accent delay={165}
              />
            </div>
          </Section>

          {/* ── Fornecedor + Sistema ── */}
          <Section title="Por Fornecedor e Sistema" icon={Award}>
            <div className="grid grid-cols-2 gap-4">
              <ChartCard title="Top Fornecedores" subtitle="Custo total por oficina / prestador">
                <FornecedorChart data={data.by_fornecedor} />
              </ChartCard>
              <ChartCard title="Mapa de Sistemas" subtitle="Distribuição de custo por sistema mecânico (Treemap)">
                <SistemaTreemap data={data.by_sistema} />
              </ChartCard>
            </div>
          </Section>

          {/* ── Tipo + Implemento ── */}
          <Section title="Tipo de Manutenção e Implemento" icon={Activity}>
            <div className="grid grid-cols-3 gap-4">
              <ChartCard title="Preventiva vs Corretiva" subtitle="Distribuição de custo por tipo">
                <TipoPie data={data.by_tipo} />
              </ChartCard>
              <div className="col-span-2">
                <ChartCard title="Custo por Implemento" subtitle="Radial — proporção relativa ao maior custo">
                  <ImplementoRadial data={data.by_implemento} />
                </ChartCard>
              </div>
            </div>
          </Section>

          {/* ── Serviços mais frequentes ── */}
          {data.by_servico?.length > 0 && (
            <Section title="Serviços Mais Executados" icon={Wrench}>
              <ChartCard title="Top Serviços por Custo" subtitle="Tipos de serviço e valor total acumulado">
                <ServicosChart data={data.by_servico} />
              </ChartCard>
            </Section>
          )}

          {/* ── Tendência + Projeção ── */}
          <Section title="Tendência e Projeção" icon={TrendingUp}>
            <ChartCard
              title="Histórico Mensal + Projeção Linear"
              subtitle="Barras = realizado · Linha tracejada = projeção com intervalo de confiança (±1σ)"
            >
              <TrendProjectionChart monthly={data.monthly} projection={data.projection} />
            </ChartCard>

            {data.projection?.length > 0 && (
              <div className="grid grid-cols-4 gap-3 mt-3">
                {data.projection.map((p, i) => (
                  <div key={i} className="card p-3 border-indigo-900/40 stagger-child" style={{'--i': i + 1}}>
                    <p className="text-g-600 text-xs uppercase tracking-wider mb-1">Projeção M+{i + 1}</p>
                    <p className="text-indigo-300 font-bold font-mono tabular-nums text-lg">{brlShort(p.projected)}</p>
                    <p className="text-g-700 text-xs mt-0.5">
                      {brlShort(p.low)} – {brlShort(p.high)}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </Section>

          {/* ── Próximas manutenções ── */}
          {data.upcoming?.length > 0 && (
            <Section title="Manutenções Programadas" icon={Calendar}>
              <div className="card overflow-hidden">
                <button
                  className="w-full flex items-center justify-between px-4 py-3 bg-g-900 border-b border-g-800 hover:bg-g-850 transition-colors"
                  onClick={() => setUpcomingOpen(v => !v)}
                >
                  <span className="text-g-300 text-xs font-semibold uppercase tracking-wider">
                    {data.upcoming.length} pendências identificadas
                  </span>
                  {upcomingOpen
                    ? <ChevronUp className="w-4 h-4 text-g-600" />
                    : <ChevronDown className="w-4 h-4 text-g-600" />}
                </button>
                {upcomingOpen && (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[640px]">
                      <thead className="bg-g-900/50">
                        <tr>
                          <th className="th th-left text-xs">Placa</th>
                          <th className="th th-left text-xs">Modelo</th>
                          <th className="th th-left text-xs">Serviço</th>
                          <th className="th th-left text-xs">Sistema</th>
                          <th className="th text-xs">KM Atual</th>
                          <th className="th text-xs">Próx. KM</th>
                          <th className="th text-xs">Próx. Data</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.upcoming.map((u, i) => {
                          const kmAlert = u.prox_km && u.km_atual && u.prox_km - u.km_atual < 5000
                          const dateAlert = u.prox_data && new Date(u.prox_data) <= new Date(Date.now() + 30 * 86400000)
                          return (
                            <tr key={i} className={`border-b border-g-900 hover:bg-g-900/60 transition-colors ${kmAlert || dateAlert ? 'bg-amber-950/10' : ''}`}>
                              <td className="td td-left text-xs font-mono font-bold text-g-50">{u.placa}</td>
                              <td className="td td-left text-xs text-g-400">{u.modelo?.length > 18 ? u.modelo.slice(0,17)+'…' : u.modelo}</td>
                              <td className="td td-left text-xs text-g-300">{u.servico?.length > 22 ? u.servico.slice(0,21)+'…' : u.servico}</td>
                              <td className="td td-left text-xs text-g-500">{u.sistema}</td>
                              <td className="td text-xs tabular-nums text-g-500">{u.km_atual ? num(u.km_atual) + ' km' : '—'}</td>
                              <td className={`td text-xs tabular-nums font-semibold ${kmAlert ? 'text-amber-300' : 'text-g-400'}`}>
                                {u.prox_km ? num(u.prox_km) + ' km' : '—'}
                              </td>
                              <td className={`td text-xs tabular-nums ${dateAlert ? 'text-amber-300 font-semibold' : 'text-g-400'}`}>
                                {u.prox_data || '—'}
                                {(kmAlert || dateAlert) && <AlertTriangle className="inline w-3 h-3 ml-1 text-amber-400" />}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </Section>
          )}
        </>
      )}
    </div>
  )
}
