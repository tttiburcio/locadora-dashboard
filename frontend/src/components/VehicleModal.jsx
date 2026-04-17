import { useEffect, useState } from 'react'
import { getVehicle } from '../utils/api'
import { brl, pct, dias, brlShort, num, dateBR } from '../utils/format'
import { VehicleMonthlyChart, VehicleCostPie } from './charts/VehicleCharts'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import {
  X, TrendingUp, TrendingDown, Wrench, Shield, FileText,
  MapPin, Calendar, DollarSign, Percent, Clock, AlertTriangle,
  ChevronRight, Loader2,
} from 'lucide-react'

const TOOLTIP_STYLE = {
  background: '#18181b', border: '1px solid #3f3f46',
  borderRadius: 8, fontSize: 12, boxShadow: '0 4px 24px rgba(0,0,0,0.5)',
}

function ContractBreakdown({ contracts = [] }) {
  if (!contracts.length) return (
    <p className="text-g-700 text-sm text-center py-8">Sem dados de contratos para este veículo.</p>
  )
  const max = Math.max(...contracts.map(c => c.receita), 1)
  return (
    <div className="flex flex-col gap-3">
      {/* Bar chart */}
      <ResponsiveContainer width="100%" height={Math.min(contracts.length * 42 + 40, 300)}>
        <BarChart
          data={contracts}
          layout="vertical"
          margin={{ top: 4, right: 12, bottom: 4, left: 80 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
          <XAxis type="number" tickFormatter={brlShort}
            tick={{ fill: '#52525b', fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="contrato" width={78}
            tick={{ fill: '#a1a1aa', fontSize: 10.5 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={v => [brl(v), 'Receita']}
          />
          <Bar dataKey="receita" name="Receita" radius={[0, 4, 4, 0]} maxBarSize={22}>
            {contracts.map((_, i) => (
              <Cell key={i} fill={`hsl(${230 + i * 28}, 70%, ${55 + i * 4}%)`} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Detail table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-g-800">
              <th className="th th-left text-xs py-2">Contrato / Região</th>
              <th className="th text-xs py-2">Receita</th>
              <th className="th text-xs py-2">Dias Trab.</th>
              <th className="th text-xs py-2">Diária Média</th>
            </tr>
          </thead>
          <tbody>
            {contracts.map((c, i) => (
              <tr key={i} className="border-b border-g-900 hover:bg-g-900/60">
                <td className="td td-left py-2 font-semibold text-g-200">{c.contrato}</td>
                <td className="td py-2 font-mono tabular-nums text-g-50">{brl(c.receita)}</td>
                <td className="td py-2 tabular-nums text-g-400">{dias(c.dias_trabalhado)}</td>
                <td className="td py-2 font-mono tabular-nums text-g-300">{brl(c.diaria_media)}/dia</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

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
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab]         = useState('kpis')  // 'kpis' | 'contratos' | 'manut'

  useEffect(() => {
    setLoading(true)
    setTab('kpis')
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
                  <h2 className="text-g-50 font-bold text-xl font-mono tracking-wide">{info.placa}</h2>
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

        {/* Tabs */}
        {!loading && data && (
          <div className="flex border-b border-g-900 px-6">
            {[
              { key: 'kpis',      label: 'KPIs & Financeiro' },
              { key: 'contratos', label: 'Por Contrato / Região' },
              { key: 'manut',     label: 'Manutenção' },
            ].map(t => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`px-4 py-2.5 text-xs font-semibold uppercase tracking-wider border-b-2 transition-colors -mb-px ${
                  tab === t.key
                    ? 'border-g-500 text-g-50'
                    : 'border-transparent text-g-600 hover:text-g-300'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}

        {loading && (
          <div className="flex-1 flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-g-600" />
            <p className="text-g-600 text-sm">Carregando {placa}…</p>
          </div>
        )}

        {!loading && data && k && (
          <div className="p-6 flex flex-col gap-6">
            {/* ── Tab: Por Contrato / Região ── */}
            {tab === 'contratos' && (
              <div>
                <p className="text-g-600 text-xs mb-4">
                  Distribuição de receita e dias trabalhados por contrato/região de operação neste exercício.
                </p>
                <ContractBreakdown contracts={data.by_contract || []} />
              </div>
            )}

            {/* ── Tab: Manutenção detalhada ── */}
            {tab === 'manut' && (
              <div>
                {data.maintenance?.length > 0 ? (
                  <div className="card overflow-hidden">
                    <table className="w-full">
                      <thead className="bg-g-900 border-b border-g-800">
                        <tr>
                          <th className="th th-left text-xs">OS</th>
                          <th className="th text-xs">Data</th>
                          <th className="th th-left text-xs">Serviço / Sistema</th>
                          <th className="th text-xs">Tipo</th>
                          <th className="th th-left text-xs">Fornecedor</th>
                          <th className="th text-xs">KM</th>
                          <th className="th text-xs">Valor</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.maintenance.map((m, i) => (
                          <tr key={i} className="border-b border-g-900 hover:bg-g-900/60 transition-colors">
                            <td className="td td-left text-xs font-mono text-g-500">{m.ordem}</td>
                            <td className="td text-xs text-g-500 tabular-nums">{dateBR(m.data)}</td>
                            <td className="td td-left text-xs">
                              <p className="text-g-200">{m.servico?.length > 22 ? m.servico.slice(0,21)+'…' : m.servico}</p>
                              {m.sistema && m.sistema !== '—' && (
                                <p className="text-g-600 text-[10px]">{m.sistema}</p>
                              )}
                            </td>
                            <td className="td text-xs">
                              <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                                m.tipo === 'Preventiva' ? 'bg-indigo-950/50 text-indigo-300' :
                                m.tipo === 'Corretiva'  ? 'bg-red-950/50 text-red-300' :
                                'bg-g-800 text-g-400'
                              }`}>{m.tipo}</span>
                            </td>
                            <td className="td td-left text-xs text-g-400">
                              {m.fornecedor?.length > 16 ? m.fornecedor.slice(0,15)+'…' : m.fornecedor}
                            </td>
                            <td className="td text-xs text-g-500 tabular-nums">{m.km ? num(m.km) + ' km' : '—'}</td>
                            <td className="td text-xs text-orange-300 font-mono font-semibold tabular-nums">{brl(m.valor)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-g-700 text-sm text-center py-8">Sem ordens de serviço para este veículo no período.</p>
                )}
              </div>
            )}

            {/* ── Tab: KPIs (default) ── */}
            {tab === 'kpis' && (<>

            {/* Margin highlight */}
            <div className={`rounded-xl p-5 border ${
              isLucr ? 'bg-g-700/10 border-g-700' : 'bg-red-950/30 border-red-900/50'
            }`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-g-600 text-xs uppercase tracking-widest mb-1.5">Margem Líquida</p>
                  <p className={`text-3xl font-bold tabular-nums ${isLucr ? 'text-g-50' : 'text-red-300'}`}>
                    {brl(k.margem)}
                  </p>
                  <p className={`text-sm mt-1.5 ${isLucr ? 'text-g-400' : 'text-red-400'}`}>
                    {pct(k.margem_pct)} sobre receita total
                  </p>
                </div>
                <div className={`p-3 rounded-xl ${isLucr ? 'bg-g-700/15 border border-g-600/20' : 'bg-red-900/30 border border-red-800/40'}`}>
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
                <MiniKPI label="Total"     value={brl(k.receita_total)}     color="text-g-50"   icon={DollarSign} />
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
                  color={k.margem_por_dia >= 0 ? 'text-g-50' : 'text-red-300'}
                />
              </div>
              {k.roi !== 0 && (
                <div className="mt-2 bg-g-950 rounded-lg p-3 border border-g-800 flex justify-between items-center">
                  <span className="text-g-600 text-xs uppercase tracking-wide font-medium">ROI sobre Valor do Ativo</span>
                  <span className={`font-bold tabular-nums ${k.roi >= 0 ? 'text-g-50' : 'text-red-300'}`}>
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

            </>)}
          </div>
        )}
      </div>
    </div>
  )
}
