import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
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
  return (
    <div className="flex flex-col gap-3">
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

function MiniKPI({ label, value, sub, color = 'text-g-100', icon: Icon, iconColor }) {
  const iCol = iconColor || color
  return (
    <div className="bg-g-950 rounded-lg p-3 border border-g-800">
      <div className="flex items-center gap-1.5 mb-1.5">
        {Icon && <Icon className={`w-3.5 h-3.5 ${iCol}`} />}
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

function formatTitle(text) {
  if (!text || text === '—') return text;
  const exceptions = ['de', 'da', 'do', 'dos', 'das', 'e', 'o', 'a', 'com', 'em', 'p/'];
  return text.toLowerCase().split(' ').map((word, i) => {
    if (i > 0 && exceptions.includes(word)) return word;
    return word.charAt(0).toUpperCase() + word.slice(1);
  }).join(' ');
}

export default function VehicleModal({ placa, year, onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('kpis')

  useEffect(() => {
    setLoading(true)
    getVehicle(placa, year).then(setData).finally(() => setLoading(false))
  }, [placa, year])

  if (!placa) return null

  const info = data?.info
  const k = data?.kpis
  const isLucr = k?.margem >= 0

  return createPortal(
    <div 
      className="fixed inset-0 z-[999] flex justify-end bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-g-950 border-l border-g-800 w-full max-w-4xl h-full shadow-2xl overflow-hidden flex flex-col animate-in slide-in-from-right duration-300">
        
        {/* Header */}
        <div className="flex items-center justify-between px-8 py-6 bg-g-900/50 border-b border-g-800">
          <div className="flex flex-col">
            {loading || !info ? (
              <div className="h-9 w-40 bg-g-800 animate-pulse rounded" />
            ) : (
              <>
                <div className="flex items-center gap-4">
                  <h2 className="text-3xl font-black text-g-50 tracking-tighter">{placa}</h2>
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-widest border ${
                    info?.status === 'Frota' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-g-800 text-g-400 border-g-700'
                  }`}>
                    {info?.status}
                  </span>
                </div>
                <p className="text-g-400 text-base mt-1">{info?.marca} · {info?.modelo}</p>
                {(info?.valor_total || 0) > 0 && (
                  <p className="text-g-600 text-sm mt-1">Ativo: {brl(info.valor_total)}</p>
                )}
              </>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-g-800 rounded-xl transition-colors text-g-500 hover:text-g-200"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {!loading && data && info && (
          <div className="flex border-b border-g-900 px-8">
            {[
              { key: 'kpis',      label: 'KPIs & Financeiro' },
              { key: 'contratos', label: 'Por Contrato / Região' },
              { key: 'manut',     label: 'Manutenção' },
            ].map(t => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`px-5 py-3.5 text-[13px] font-bold uppercase tracking-wider border-b-2 transition-colors -mb-px ${
                  tab === t.key
                    ? 'border-g-400 text-g-50'
                    : 'border-transparent text-g-600 hover:text-g-300'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}

        {loading && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4">
            <Loader2 className="w-8 h-8 animate-spin text-g-600" />
            <p className="text-g-500 text-base">Carregando dados de {placa}…</p>
          </div>
        )}

        {!loading && data && k && (
          <div className="p-8 flex-1 flex flex-col gap-8 overflow-y-auto custom-scrollbar">
            {tab === 'contratos' && (
              <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                <p className="text-g-500 text-sm mb-6">
                  Distribuição de receita e dias trabalhados por contrato/região de operação neste exercício.
                </p>
                <ContractBreakdown contracts={data.by_contract || []} />
              </div>
            )}

            {tab === 'manut' && (
              <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                {data.maintenance?.length > 0 ? (
                  <div className="card overflow-x-auto custom-scrollbar">
                    <table className="w-full text-sm min-w-[700px]">
                      <thead className="bg-g-900/50 border-b border-g-800">
                        <tr>
                          <th className="px-5 py-3 text-left font-bold text-g-500 uppercase tracking-widest text-[11px]">OS</th>
                          <th className="px-5 py-3 text-center font-bold text-g-500 uppercase tracking-widest text-[11px]">Data</th>
                          <th className="px-5 py-3 text-left font-bold text-g-500 uppercase tracking-widest text-[11px]">Sistema</th>
                          <th className="px-5 py-3 text-left font-bold text-g-500 uppercase tracking-widest text-[11px]">Serviço</th>
                          <th className="px-5 py-3 text-center font-bold text-g-500 uppercase tracking-widest text-[11px]">Tipo</th>
                          <th className="px-5 py-3 text-center font-bold text-g-500 uppercase tracking-widest text-[11px]">Notas</th>
                          <th className="px-5 py-3 text-center font-bold text-g-500 uppercase tracking-widest text-[11px]">KM</th>
                          <th className="px-5 py-3 text-right font-bold text-g-500 uppercase tracking-widest text-[11px]">Valor</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-g-900">
                        {data.maintenance.map((m, i) => (
                          <tr key={i} className="hover:bg-white/[0.02] transition-colors group">
                            <td className="px-5 py-4 font-mono text-g-500 font-medium whitespace-nowrap">{m.ordem}</td>
                            <td className="px-5 py-4 text-center text-g-500 tabular-nums whitespace-nowrap">{dateBR(m.data)}</td>
                            <td className="px-5 py-4 text-g-400 font-medium">
                              <div className="flex flex-col min-w-[100px]">
                                <span>{m.sistema || '—'}</span>
                                {m.evento === 'Revisão' && (
                                  <span className="text-[10px] text-indigo-400 font-bold uppercase tracking-tighter">Evento Revisão</span>
                                )}
                              </div>
                            </td>
                            <td className="px-5 py-4">
                              <span className="text-g-400 font-medium">{formatTitle(m.servico)}</span>
                            </td>
                            <td className="px-5 py-4 text-center">
                              <span className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase border ${
                                m.tipo === 'Preventiva' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                                m.tipo === 'Corretiva'  ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                                'bg-g-800 text-g-500 border-g-700'
                              }`}>
                                {m.tipo}
                              </span>
                            </td>
                            <td className="px-5 py-4 text-center">
                              <div className="flex items-center justify-center gap-1.5">
                                <FileText className="w-3.5 h-3.5 text-g-700" />
                                <span className="text-g-500 font-mono">{m.qtd_notas || 0}</span>
                              </div>
                            </td>
                            <td className="px-5 py-4 text-center text-g-500 tabular-nums whitespace-nowrap">{m.km ? num(m.km) + ' km' : '—'}</td>
                            <td className="px-5 py-4 text-right">
                              <span className="text-orange-400/90 font-mono font-bold tabular-nums text-base">{brl(m.valor)}</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-g-600 text-base text-center py-12 bg-g-900/20 rounded-2xl border border-dashed border-g-800">
                    Sem ordens de serviço para este veículo no período.
                  </p>
                )}
              </div>
            )}

            {tab === 'kpis' && (
              <div className="flex flex-col gap-6">
                {/* Margin Card */}
                <div className={`rounded-xl p-5 border ${
                  isLucr ? 'bg-g-950 border-g-800 shadow-sm' : 'bg-red-500/5 border-red-500/10'
                }`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-g-600 text-xs uppercase tracking-widest mb-1.5">Margem Líquida</p>
                      <h3 className={`text-3xl font-extrabold font-mono tabular-nums ${isLucr ? 'text-emerald-500' : 'text-red-500'}`}>
                        {brl(k.margem)}
                      </h3>
                      <p className={`text-sm mt-1.5 ${isLucr ? 'text-g-400' : 'text-red-400'}`}>
                        {pct(k.margem_pct)} sobre receita total
                      </p>
                    </div>
                    <div className="p-3 rounded-xl bg-g-850 border border-g-800">
                      {isLucr
                        ? <TrendingUp className="w-8 h-8 text-g-400" />
                        : <TrendingDown className="w-8 h-8 text-red-400" />}
                    </div>
                  </div>
                </div>

                {/* Revenue Section */}
                <div>
                  <SectionTitle icon={DollarSign}>Receita</SectionTitle>
                  <div className="grid grid-cols-3 gap-2">
                    <MiniKPI label="Total"     value={brl(k.receita_total)}     color="text-emerald-600" icon={DollarSign} />
                    <MiniKPI label="Locação"   value={brl(k.receita_locacao)}   color="text-g-200"       icon={FileText} iconColor="text-g-500" />
                    <MiniKPI label="Reembolso" value={brl(k.receita_reembolso)} color="text-g-200"       icon={ChevronRight} iconColor="text-g-500" />
                  </div>
                </div>

                {/* Costs Section */}
                <div>
                  <SectionTitle icon={Wrench}>Custos</SectionTitle>
                  <div className="grid grid-cols-2 gap-2">
                    <MiniKPI label="Manutenção"   value={brl(k.custo_manutencao)}   color="text-orange-400" icon={Wrench} />
                    <MiniKPI label="Seguro"       value={brl(k.custo_seguro)}       color="text-red-400"    icon={Shield} />
                    <MiniKPI label="Impostos"     value={brl(k.custo_impostos)}     color="text-purple-400" icon={FileText} />
                    <MiniKPI label="Rastreamento" value={brl(k.custo_rastreamento)} color="text-amber-400"  icon={MapPin} />
                  </div>
                  <div className="mt-2 bg-g-950 rounded-lg p-3 border border-g-800 flex justify-between items-center">
                    <span className="text-g-600 text-xs uppercase tracking-wide font-medium">Custo Total</span>
                    <span className="text-red-400 font-bold font-mono">{brl(k.custo_total)}</span>
                  </div>
                </div>

                {/* Operation Section */}
                <div>
                  <SectionTitle icon={Clock}>Operação</SectionTitle>
                  <div className="grid grid-cols-3 gap-2">
                    <MiniKPI label="Dias Trabalhados" value={dias(k.dias_trabalhado)} icon={Calendar} iconColor="text-g-500" />
                    <MiniKPI label="Dias Parado"      value={dias(k.dias_parado)} icon={AlertTriangle} iconColor="text-g-500" color="text-emerald-600" />
                    <MiniKPI label="Utilização"       value={pct(k.dias_trabalhado / (k.dias_trabalhado + k.dias_parado) * 100)} icon={Percent} iconColor="text-g-500" color="text-emerald-600" />
                    <MiniKPI label="Receita / Dia"    value={brlShort(k.receita_por_dia)} color="text-g-200" />
                    <MiniKPI label="Custo / Dia"      value={brlShort(k.custo_por_dia)}   color="text-red-400" />
                    <MiniKPI label="Margem / Dia"     value={brlShort(k.margem_por_dia)}  color="text-emerald-600" />
                  </div>
                </div>

                {/* Evolution Section */}
                <div>
                  <SectionTitle icon={Calendar}>Evolução Mensal</SectionTitle>
                  <div className="card p-4">
                    <div className="h-64">
                      <VehicleMonthlyChart monthly={data.monthly} />
                    </div>
                  </div>
                </div>

                {/* Bottom Charts */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <SectionTitle icon={Percent}>Composição de Custos</SectionTitle>
                    <div className="card p-4 h-64">
                      <VehicleCostPie kpis={k} />
                    </div>
                  </div>
                  <div>
                    <SectionTitle icon={Calendar}>Dias Trabalhados / Mês</SectionTitle>
                    <div className="card p-4 h-64 overflow-y-auto space-y-3">
                      {data.monthly.filter(m => m.dias_trabalhado > 0).map(m => (
                        <div key={m.month} className="flex items-center gap-2">
                          <span className="text-g-600 text-[10px] w-6 uppercase">{m.monthName.slice(0, 3)}</span>
                          <div className="flex-1 bg-g-850 rounded-full h-2 overflow-hidden border border-g-800">
                            <div
                              className="h-full bg-g-200 rounded-full"
                              style={{ width: `${Math.min((m.dias_trabalhado / 31) * 100, 100)}%` }}
                            />
                          </div>
                          <span className="text-g-500 text-[10px] font-mono w-8 text-right">{Math.round(m.dias_trabalhado)}d</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>,
    document.body
  )
}
