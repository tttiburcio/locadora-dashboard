import { useEffect, useState } from 'react'
import { getVehicle } from '../utils/api'
import { brl, pct, dias, brlShort } from '../utils/format'
import { VehicleMonthlyChart, VehicleCostPie } from './charts/VehicleCharts'
import {
  X, TrendingUp, TrendingDown, Wrench, Shield, FileText,
  MapPin, Calendar, DollarSign, Percent, Clock, AlertTriangle,
  ChevronRight, Loader2,
} from 'lucide-react'

function MiniKPI({ label, value, sub, color = 'text-g-100', icon: Icon }) {
  return (
    <div className="bg-g-900 rounded-lg p-3 border border-g-800">
      <div className="flex items-center gap-1.5 mb-1.5">
        {Icon && <Icon className="w-3.5 h-3.5 text-g-500" />}
        <span className="text-g-500 text-xs uppercase tracking-wide">{label}</span>
      </div>
      <p className={`text-base font-bold ${color}`}>{value}</p>
      {sub && <p className="text-g-600 text-xs mt-0.5">{sub}</p>}
    </div>
  )
}

function StatusBadge({ status }) {
  const s = (status || '').toUpperCase()
  if (s.includes('ATIVO') || s === 'LOCADO')
    return <span className="badge-green">{status}</span>
  if (s.includes('MANUT') || s.includes('MANT'))
    return <span className="badge-amber">{status}</span>
  return <span className="badge-red">{status}</span>
}

export default function VehicleModal({ placa, year, onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getVehicle(placa, year)
      .then(setData)
      .finally(() => setLoading(false))
  }, [placa, year])

  // Close on Escape
  useEffect(() => {
    const fn = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', fn)
    return () => window.removeEventListener('keydown', fn)
  }, [onClose])

  const k = data?.kpis
  const info = data?.info
  const isLucr = k && k.margem >= 0

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-end"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-g-950/80 backdrop-blur-sm" onClick={onClose} />

      {/* Drawer */}
      <div className="relative w-full max-w-2xl h-full bg-g-900 border-l border-g-800 overflow-y-auto shadow-2xl flex flex-col">
        {/* Header */}
        <div className="sticky top-0 bg-g-900/95 backdrop-blur-sm border-b border-g-800 px-6 py-4 flex items-start justify-between z-10">
          <div>
            {loading || !info ? (
              <div className="h-6 w-40 bg-g-800 rounded animate-pulse" />
            ) : (
              <>
                <div className="flex items-center gap-2.5 mb-1">
                  <h2 className="text-g-50 font-bold text-xl font-mono">{info.placa}</h2>
                  <StatusBadge status={info.status} />
                </div>
                <p className="text-g-400 text-sm">{info.marca} · {info.modelo}</p>
                {info.valor_total > 0 && (
                  <p className="text-g-600 text-xs mt-0.5">Valor do ativo: {brl(info.valor_total)}</p>
                )}
              </>
            )}
          </div>
          <button onClick={onClose} className="p-1.5 hover:bg-g-800 rounded-lg transition-colors">
            <X className="w-4 h-4 text-g-500" />
          </button>
        </div>

        {loading && (
          <div className="flex-1 flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-g-500" />
            <p className="text-g-500 text-sm">Carregando {placa}…</p>
          </div>
        )}

        {!loading && data && k && (
          <div className="p-6 flex flex-col gap-6">
            {/* Margin highlight */}
            <div className={`rounded-xl p-4 border ${isLucr ? 'bg-g-800/50 border-g-700' : 'bg-red-950/40 border-red-900'}`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-g-500 text-xs uppercase tracking-wider mb-1">Margem Líquida</p>
                  <p className={`text-3xl font-bold ${isLucr ? 'text-g-300' : 'text-red-300'}`}>
                    {brl(k.margem)}
                  </p>
                  <p className={`text-sm mt-1 ${isLucr ? 'text-g-400' : 'text-red-400'}`}>
                    {pct(k.margem_pct)} sobre receita total
                  </p>
                </div>
                <div className={`p-3 rounded-xl ${isLucr ? 'bg-g-700' : 'bg-red-900/50'}`}>
                  {isLucr
                    ? <TrendingUp className="w-8 h-8 text-g-400" />
                    : <TrendingDown className="w-8 h-8 text-red-400" />}
                </div>
              </div>
            </div>

            {/* Revenue KPIs */}
            <div>
              <h3 className="text-g-400 text-xs font-semibold uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                <DollarSign className="w-3.5 h-3.5" />Receita
              </h3>
              <div className="grid grid-cols-3 gap-2">
                <MiniKPI label="Total" value={brl(k.receita_total)} color="text-g-200" icon={DollarSign} />
                <MiniKPI label="Locação" value={brl(k.receita_locacao)} color="text-g-300" icon={FileText} />
                <MiniKPI label="Reembolso" value={brl(k.receita_reembolso)} color="text-emerald-300" icon={ChevronRight} />
              </div>
            </div>

            {/* Cost KPIs */}
            <div>
              <h3 className="text-g-400 text-xs font-semibold uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                <Wrench className="w-3.5 h-3.5" />Custos
              </h3>
              <div className="grid grid-cols-2 gap-2">
                <MiniKPI label="Manutenção"    value={brl(k.custo_manutencao)}   color="text-orange-300" icon={Wrench} />
                <MiniKPI label="Seguro"        value={brl(k.custo_seguro)}       color="text-red-300"    icon={Shield} />
                <MiniKPI label="Impostos"      value={brl(k.custo_impostos)}     color="text-purple-300" icon={FileText} />
                <MiniKPI label="Rastreamento"  value={brl(k.custo_rastreamento)} color="text-amber-300"  icon={MapPin} />
              </div>
              <div className="mt-2 bg-g-900 rounded-lg p-3 border border-g-800 flex justify-between items-center">
                <span className="text-g-500 text-xs uppercase tracking-wide">Custo Total</span>
                <span className="text-red-300 font-bold">{brl(k.custo_total)}</span>
              </div>
            </div>

            {/* Operational KPIs */}
            <div>
              <h3 className="text-g-400 text-xs font-semibold uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />Operação
              </h3>
              <div className="grid grid-cols-3 gap-2">
                <MiniKPI label="Dias Trabalhados" value={dias(k.dias_trabalhado)} icon={Calendar} />
                <MiniKPI label="Dias Parado"      value={dias(k.dias_parado)}
                  color={k.dias_parado > k.dias_trabalhado ? 'text-amber-300' : 'text-g-100'}
                  icon={AlertTriangle} />
                <MiniKPI label="Utilização"
                  value={k.dias_trabalhado + k.dias_parado > 0
                    ? pct(k.dias_trabalhado / (k.dias_trabalhado + k.dias_parado) * 100)
                    : '—'}
                  icon={Percent} />
                <MiniKPI label="Receita / Dia" value={k.receita_por_dia > 0 ? brlShort(k.receita_por_dia) : '—'} color="text-g-300" />
                <MiniKPI label="Custo / Dia"   value={k.custo_por_dia > 0 ? brlShort(k.custo_por_dia) : '—'}   color="text-red-300" />
                <MiniKPI label="Margem / Dia"  value={k.margem_por_dia !== 0 ? brlShort(k.margem_por_dia) : '—'}
                  color={k.margem_por_dia >= 0 ? 'text-g-300' : 'text-red-300'} />
              </div>
              {k.roi !== 0 && (
                <div className="mt-2 bg-g-900 rounded-lg p-3 border border-g-800 flex justify-between items-center">
                  <span className="text-g-500 text-xs uppercase tracking-wide">ROI sobre Valor do Ativo</span>
                  <span className={`font-bold ${k.roi >= 0 ? 'text-g-300' : 'text-red-300'}`}>{pct(k.roi)}</span>
                </div>
              )}
            </div>

            {/* Monthly chart */}
            <div>
              <h3 className="text-g-400 text-xs font-semibold uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5" />Evolução Mensal
              </h3>
              <div className="card p-3">
                <VehicleMonthlyChart monthly={data.monthly} />
              </div>
            </div>

            {/* Cost breakdown */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h3 className="text-g-400 text-xs font-semibold uppercase tracking-wider mb-3">Composição de Custos</h3>
                <div className="card p-2">
                  <VehicleCostPie kpis={k} />
                </div>
              </div>

              {/* Days worked by month */}
              <div>
                <h3 className="text-g-400 text-xs font-semibold uppercase tracking-wider mb-3">Dias Trabalhados / Mês</h3>
                <div className="card p-3 space-y-1.5">
                  {data.monthly.filter(m => m.dias_trabalhado > 0).map(m => (
                    <div key={m.month} className="flex items-center gap-2">
                      <span className="text-g-500 text-xs w-7">{m.monthName}</span>
                      <div className="flex-1 bg-g-900 rounded-full h-2 overflow-hidden">
                        <div
                          className="h-full bg-g-600 rounded-full"
                          style={{ width: `${Math.min((m.dias_trabalhado / 31) * 100, 100)}%` }}
                        />
                      </div>
                      <span className="text-g-400 text-xs w-12 text-right">{Math.round(m.dias_trabalhado)}d</span>
                    </div>
                  ))}
                  {data.monthly.every(m => m.dias_trabalhado === 0) && (
                    <p className="text-g-600 text-xs text-center py-4">Sem registros de dias trabalhados</p>
                  )}
                </div>
              </div>
            </div>

            {/* Maintenance table */}
            {data.maintenance?.length > 0 && (
              <div>
                <h3 className="text-g-400 text-xs font-semibold uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <Wrench className="w-3.5 h-3.5" />
                  Histórico de Manutenção ({data.maintenance.length} OS)
                </h3>
                <div className="card overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-g-800">
                      <tr>
                        <th className="th th-left text-xs">OS</th>
                        <th className="th text-xs">Data</th>
                        <th className="th text-xs">Fornecedor</th>
                        <th className="th text-xs">Valor</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.maintenance.slice(0, 20).map((m, i) => (
                        <tr key={i} className="border-b border-g-900 hover:bg-g-800/40 transition-colors">
                          <td className="td td-left text-xs font-mono text-g-400">{m.ordem}</td>
                          <td className="td text-xs text-g-400">{m.data}</td>
                          <td className="td text-xs text-g-300 text-right truncate max-w-[120px]">{m.fornecedor}</td>
                          <td className="td text-xs text-orange-300 font-mono">{brl(m.valor)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {data.maintenance.length > 20 && (
                    <div className="px-4 py-2 text-g-600 text-xs text-center border-t border-g-900">
                      +{data.maintenance.length - 20} ordens de serviço
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
