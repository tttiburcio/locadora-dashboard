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
    <div className="bg-g-950 rounded-lg p-3 border border-g-800">
      <div className="flex items-center gap-1.5 mb-1.5">
        {Icon && <Icon className="w-3.5 h-3.5 text-g-600" />}
        <span className="text-g-600 text-xs uppercase tracking-wide font-medium">{label}</span>
      </div>
      <p className={`text-base font-bold tabular-nums ${color}`}>{value}</p>
      {sub && <p className="text-g-700 text-xs mt-0.5">{sub}</p>}
    </div>
  )
}

function StatusBadge({ status }) {
  const s = (status || '').toUpperCase()
  if (s.includes('ATIVO') || s === 'LOCADO') return <span className="badge-green">{status}</span>
  if (s.includes('MANUT') || s.includes('MANT')) return <span className="badge-amber">{status}</span>
  return <span className="badge-red">{status}</span>
}

function SectionTitle({ icon: Icon, children }) {
  return (
    <h3 className="text-g-500 text-xs font-semibold uppercase tracking-widest mb-2.5 flex items-center gap-1.5">
      {Icon && <Icon className="w-3.5 h-3.5" />}
      {children}
    </h3>
  )
}

export default function VehicleModal({ placa, year, onClose }) {
  const [data, setData]     = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getVehicle(placa, year).then(setData).finally(() => setLoading(false))
  }, [placa, year])

  useEffect(() => {
    const fn = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', fn)
    return () => window.removeEventListener('keydown', fn)
  }, [onClose])

  const k    = data?.kpis
  const info = data?.info
  const isLucr = k && k.margem >= 0

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-end"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-[2px] animate-fade-in" onClick={onClose} />

      {/* Drawer — slides in from right */}
      <div className="relative w-full max-w-2xl h-full bg-g-950 border-l border-g-800 overflow-y-auto shadow-2xl flex flex-col animate-slide-in-right">

        {/* Header */}
        <div className="sticky top-0 bg-g-950/98 backdrop-blur-sm border-b border-g-900 px-6 py-4 flex items-start justify-between z-10">
          <div>
            {loading || !info ? (
              <>
                <div className="skeleton h-6 w-36 mb-2" />
                <div className="skeleton h-4 w-48" />
              </>
            ) : (
              <>
                <div className="flex items-center gap-2.5 mb-1">
                  <h2 className="text-white font-bold text-xl font-mono tracking-wide">{info.placa}</h2>
                  <StatusBadge status={info.status} />
                </div>
                <p className="text-g-500 text-sm">{info.marca} · {info.modelo}</p>
                {info.valor_total > 0 && (
                  <p className="text-g-700 text-xs mt-0.5">Ativo: {brl(info.valor_total)}</p>
                )}
              </>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-g-800 rounded-lg transition-colors text-g-500 hover:text-g-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {loading && (
          <div className="flex-1 flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-g-600" />
            <p className="text-g-600 text-sm">Carregando {placa}…</p>
          </div>
        )}

        {!loading && data && k && (
          <div className="p-6 flex flex-col gap-6">

            {/* Margin highlight */}
            <div className={`rounded-xl p-5 border ${
              isLucr ? 'bg-white/[0.02] border-g-700' : 'bg-red-950/30 border-red-900/50'
            }`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-g-600 text-xs uppercase tracking-widest mb-1.5">Margem Líquida</p>
                  <p className={`text-3xl font-bold tabular-nums ${isLucr ? 'text-white' : 'text-red-300'}`}>
                    {brl(k.margem)}
                  </p>
                  <p className={`text-sm mt-1.5 ${isLucr ? 'text-g-400' : 'text-red-400'}`}>
                    {pct(k.margem_pct)} sobre receita total
                  </p>
                </div>
                <div className={`p-3 rounded-xl ${isLucr ? 'bg-white/5 border border-white/10' : 'bg-red-900/30 border border-red-800/40'}`}>
                  {isLucr
                    ? <TrendingUp  className="w-8 h-8 text-g-300" />
                    : <TrendingDown className="w-8 h-8 text-red-400" />}
                </div>
              </div>
            </div>

            {/* Revenue */}
            <div>
              <SectionTitle icon={DollarSign}>Receita</SectionTitle>
              <div className="grid grid-cols-3 gap-2">
                <MiniKPI label="Total"     value={brl(k.receita_total)}     color="text-white"  icon={DollarSign} />
                <MiniKPI label="Locação"   value={brl(k.receita_locacao)}   color="text-g-200"  icon={FileText} />
                <MiniKPI label="Reembolso" value={brl(k.receita_reembolso)} color="text-g-300"  icon={ChevronRight} />
              </div>
            </div>

            {/* Costs */}
            <div>
              <SectionTitle icon={Wrench}>Custos</SectionTitle>
              <div className="grid grid-cols-2 gap-2">
                <MiniKPI label="Manutenção"   value={brl(k.custo_manutencao)}   color="text-orange-300" icon={Wrench} />
                <MiniKPI label="Seguro"       value={brl(k.custo_seguro)}       color="text-red-300"    icon={Shield} />
                <MiniKPI label="Impostos"     value={brl(k.custo_impostos)}     color="text-purple-300" icon={FileText} />
                <MiniKPI label="Rastreamento" value={brl(k.custo_rastreamento)} color="text-amber-300"  icon={MapPin} />
              </div>
              <div className="mt-2 bg-g-950 rounded-lg p-3 border border-g-800 flex justify-between items-center">
                <span className="text-g-600 text-xs uppercase tracking-wide font-medium">Custo Total</span>
                <span className="text-red-300 font-bold tabular-nums">{brl(k.custo_total)}</span>
              </div>
            </div>

            {/* Operational */}
            <div>
              <SectionTitle icon={Clock}>Operação</SectionTitle>
              <div className="grid grid-cols-3 gap-2">
                <MiniKPI label="Dias Trabalhados" value={dias(k.dias_trabalhado)} icon={Calendar} />
                <MiniKPI label="Dias Parado"
                  value={dias(k.dias_parado)}
                  color={k.dias_parado > k.dias_trabalhado ? 'text-amber-300' : 'text-g-100'}
                  icon={AlertTriangle}
                />
                <MiniKPI
                  label="Utilização"
                  value={k.dias_trabalhado + k.dias_parado > 0
                    ? pct(k.dias_trabalhado / (k.dias_trabalhado + k.dias_parado) * 100)
                    : '—'}
                  icon={Percent}
                />
                <MiniKPI label="Receita / Dia" value={k.receita_por_dia > 0 ? brlShort(k.receita_por_dia) : '—'} color="text-g-200" />
                <MiniKPI label="Custo / Dia"   value={k.custo_por_dia > 0   ? brlShort(k.custo_por_dia)   : '—'} color="text-red-300" />
                <MiniKPI label="Margem / Dia"
                  value={k.margem_por_dia !== 0 ? brlShort(k.margem_por_dia) : '—'}
                  color={k.margem_por_dia >= 0 ? 'text-white' : 'text-red-300'}
                />
              </div>
              {k.roi !== 0 && (
                <div className="mt-2 bg-g-950 rounded-lg p-3 border border-g-800 flex justify-between items-center">
                  <span className="text-g-600 text-xs uppercase tracking-wide font-medium">ROI sobre Valor do Ativo</span>
                  <span className={`font-bold tabular-nums ${k.roi >= 0 ? 'text-white' : 'text-red-300'}`}>
                    {pct(k.roi)}
                  </span>
                </div>
              )}
            </div>

            {/* Monthly chart */}
            <div>
              <SectionTitle icon={Calendar}>Evolução Mensal</SectionTitle>
              <div className="card p-3">
                <VehicleMonthlyChart monthly={data.monthly} />
              </div>
            </div>

            {/* Cost breakdown + days bar */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <SectionTitle>Composição de Custos</SectionTitle>
                <div className="card p-2">
                  <VehicleCostPie kpis={k} />
                </div>
              </div>

              <div>
                <SectionTitle icon={Calendar}>Dias Trabalhados / Mês</SectionTitle>
                <div className="card p-3 space-y-2">
                  {data.monthly.filter(m => m.dias_trabalhado > 0).map(m => (
                    <div key={m.month} className="flex items-center gap-2">
                      <span className="text-g-600 text-xs w-7">{m.monthName}</span>
                      <div className="flex-1 bg-g-900 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="h-full bg-g-500 rounded-full transition-all duration-500"
                          style={{ width: `${Math.min((m.dias_trabalhado / 31) * 100, 100)}%` }}
                        />
                      </div>
                      <span className="text-g-500 text-xs w-10 text-right tabular-nums">{Math.round(m.dias_trabalhado)}d</span>
                    </div>
                  ))}
                  {data.monthly.every(m => m.dias_trabalhado === 0) && (
                    <p className="text-g-700 text-xs text-center py-4">Sem registros</p>
                  )}
                </div>
              </div>
            </div>

            {/* Maintenance table */}
            {data.maintenance?.length > 0 && (
              <div>
                <SectionTitle icon={Wrench}>
                  Histórico de Manutenção ({data.maintenance.length} OS)
                </SectionTitle>
                <div className="card overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-g-900 border-b border-g-800">
                      <tr>
                        <th className="th th-left text-xs">OS</th>
                        <th className="th text-xs">Data</th>
                        <th className="th text-xs">Fornecedor</th>
                        <th className="th text-xs">Valor</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.maintenance.slice(0, 20).map((m, i) => (
                        <tr key={i} className="border-b border-g-900 hover:bg-g-900/60 transition-colors">
                          <td className="td td-left text-xs font-mono text-g-500">{m.ordem}</td>
                          <td className="td text-xs text-g-500">{m.data}</td>
                          <td className="td text-xs text-g-300 text-right truncate max-w-[120px]">{m.fornecedor}</td>
                          <td className="td text-xs text-orange-300 font-mono font-semibold">{brl(m.valor)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {data.maintenance.length > 20 && (
                    <div className="px-4 py-2.5 text-g-600 text-xs text-center border-t border-g-900">
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
