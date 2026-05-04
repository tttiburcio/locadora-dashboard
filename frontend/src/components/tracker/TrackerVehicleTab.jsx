import { Route, Gauge, Clock, MapPin, ExternalLink, AlertTriangle } from 'lucide-react'
import { km, dateBR } from '../../utils/format'
import { HIGH_USAGE_THRESHOLD } from '../../constants/trackerThresholds'

const MAPWS_BASE = 'http://localhost:5174'

const MONTHS_PT = [
  'Janeiro','Fevereiro','Março','Abril','Maio','Junho',
  'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro',
]

// ── Helpers ──────────────────────────────────────────────────────────────────

function parseDate(s) {
  if (!s) return null
  if (s.includes('/')) {
    const [d, m, y] = s.split('/').map(Number)
    return { day: d, month: m, year: y }
  }
  const [y, m, d] = s.split('-').map(Number)
  return { day: d, month: m, year: y }
}

function toISO(s) {
  const p = parseDate(s)
  if (!p) return ''
  return `${p.year}-${String(p.month).padStart(2,'0')}-${String(p.day).padStart(2,'0')}`
}

function groupByMonth(arr) {
  const map = new Map()
  for (const d of arr) {
    const p = parseDate(d.data)
    if (!p) continue
    const key = `${p.year}-${String(p.month).padStart(2,'0')}`
    if (!map.has(key)) map.set(key, { year: p.year, month: p.month, totalKm: 0, entries: [] })
    const g = map.get(key)
    const rodado = d.km_rodado ?? 0
    g.totalKm += rodado
    g.entries.push({ 
      dateStr: d.data,
      day: p.day, 
      km: rodado, 
      kmFim: d.km_fim ?? null, 
      locInicio: d.endereco_inicio || d.localizacao || '',
      locFim: d.endereco_fim || ''
    })
  }
  for (const g of map.values()) g.entries.sort((a, b) => b.day - a.day) // Decrescente (mais recente primeiro)
  return [...map.entries()]
    .sort(([a], [b]) => b.localeCompare(a)) // Meses mais recentes primeiro
    .map(([, v]) => v)
}

function MonthTable({ data }) {
  const { year, month, totalKm, entries } = data
  const monthName = MONTHS_PT[month - 1]

  return (
    <div className="card overflow-hidden">
      {/* Header do Mês */}
      <div className="bg-g-900 border-b border-g-800 px-4 py-3 flex items-center justify-between">
        <h3 className="text-g-100 font-semibold flex items-center gap-2">
          <Clock className="w-4 h-4 text-g-500" />
          {monthName} <span className="text-g-500 font-normal">{year}</span>
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-g-500 text-xs font-semibold uppercase tracking-widest">Total no Mês:</span>
          <span className={`font-mono font-bold text-sm px-2.5 py-0.5 rounded-md border ${
            totalKm === 0 
              ? 'bg-g-850 text-g-500 border-g-800' 
              : 'bg-blue-50 text-blue-600 border-blue-200'
          }`}>
            {km(totalKm)}
          </span>
        </div>
      </div>

      {/* Tabela de Dias */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-g-900/50 border-b border-g-800">
            <tr>
              <th className="th w-24">Data</th>
              <th className="th w-32">KM Rodado</th>
              <th className="th w-32">Odômetro</th>
              <th className="th">Localização / Rota</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-g-800/50">
            {entries.map((e, idx) => {
              const isHigh = e.km > HIGH_USAGE_THRESHOLD
              return (
                <tr key={idx} className="hover:bg-g-850 transition-colors group">
                  <td className="td">
                    <span className="text-g-300 font-medium">{e.dateStr.slice(0, 5)}</span>
                  </td>
                  <td className="td">
                    {e.km > 0 ? (
                      <span className={`inline-flex items-center gap-1.5 font-semibold ${isHigh ? 'text-red-500' : 'text-g-300'}`}>
                        {km(e.km)}
                        {isHigh && <AlertTriangle className="w-3 h-3 text-red-500" />}
                      </span>
                    ) : (
                      <span className="text-g-600 font-normal">—</span>
                    )}
                  </td>
                  <td className="td">
                    <span className="text-g-400 font-medium text-sm">{e.kmFim ? km(e.kmFim) : '—'}</span>
                  </td>
                  <td className="td">
                    <div className="flex flex-col gap-0.5">
                      {e.locInicio ? (
                        <div className="flex items-start gap-1.5">
                          <MapPin className="w-3.5 h-3.5 text-g-600 shrink-0 mt-0.5" />
                          <span className="text-g-400 text-xs leading-snug">{e.locInicio}</span>
                        </div>
                      ) : (
                        <span className="text-g-600 text-xs">—</span>
                      )}
                      {e.locFim && e.locFim !== e.locInicio && (
                        <div className="flex items-start gap-1.5 mt-0.5">
                          <Route className="w-3.5 h-3.5 text-g-600 shrink-0 mt-0.5" />
                          <span className="text-g-400 text-xs leading-snug">{e.locFim}</span>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function TrackerVehicleTab({ loading, kmData, placa }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-16 gap-3">
        <div className="w-5 h-5 border-2 border-g-600 border-t-g-200 rounded-full animate-spin" />
        <span className="text-g-400 text-sm font-medium">Buscando histórico de rastreamento...</span>
      </div>
    )
  }

  const hasKm = Array.isArray(kmData) && kmData.length > 0

  if (!hasKm) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-4 bg-g-900/30 rounded-2xl border border-dashed border-g-800">
        <Route className="w-8 h-8 text-g-700 mb-3" />
        <p className="text-g-400 text-sm text-center">Nenhum registro de rastreamento encontrado para este veículo no período.</p>
      </div>
    )
  }

  const sorted  = [...kmData].sort((a, b) => toISO(b.data).localeCompare(toISO(a.data)))
  const latest  = sorted[0]
  const totalKm = kmData.reduce((s, d) => s + (d.km_rodado ?? 0), 0)
  const months  = groupByMonth(kmData)

  const mapwsUrl = placa
    ? `${MAPWS_BASE}/?placa=${encodeURIComponent(placa)}`
    : MAPWS_BASE

  return (
    <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-2 duration-300">

      {/* ── Top bar: KPIs ── */}
      <div className="flex items-start gap-3">
        <div className="grid grid-cols-3 gap-3 flex-1">
          <div className="card p-4 flex flex-col gap-1.5">
            <div className="flex items-center gap-2 text-g-500 mb-1">
              <Route className="w-4 h-4" />
              <span className="text-[10px] uppercase tracking-widest font-bold">KM Acumulado</span>
            </div>
            <span className="text-g-100 font-bold font-mono text-2xl tabular-nums">{km(totalKm)}</span>
            <span className="text-g-500 text-xs">Total registrado no período</span>
          </div>

          <div className="card p-4 flex flex-col gap-1.5">
            <div className="flex items-center gap-2 text-g-500 mb-1">
              <Gauge className="w-4 h-4" />
              <span className="text-[10px] uppercase tracking-widest font-bold">Odômetro Atual</span>
            </div>
            <span className="text-g-100 font-bold font-mono text-2xl tabular-nums">{latest?.km_fim ? km(latest.km_fim) : '—'}</span>
            <span className="text-g-500 text-xs">Último registro apontado</span>
          </div>

          <div className="card p-4 flex flex-col gap-1.5">
            <div className="flex items-center gap-2 text-g-500 mb-1">
              <Clock className="w-4 h-4" />
              <span className="text-[10px] uppercase tracking-widest font-bold">Última Posição</span>
            </div>
            <span className="text-g-100 font-bold text-lg tabular-nums truncate">
              {latest?.data ? dateBR(latest.data) : '—'}
            </span>
            <span className="text-g-500 text-xs truncate" title={latest?.localizacao || latest?.endereco_inicio || ''}>
              {latest?.localizacao || latest?.endereco_inicio || 'Localização não disponível'}
            </span>
          </div>
        </div>
      </div>

      {/* ── Monthly Tables ── */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between px-1">
          <h2 className="text-g-300 text-sm font-bold uppercase tracking-widest">
            Histórico Diário de Rotas
          </h2>
          {/* MapWS redirect button correctly placed here, smaller and visible */}
          <a
            href={mapwsUrl}
            target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-g-850 hover:bg-g-800 text-g-100 border border-g-800 hover:border-g-750 text-xs font-semibold rounded-lg transition-all cursor-pointer shadow-sm"
          >
            <MapPin className="w-3.5 h-3.5 text-g-100" />
            Acessar MapWS
            <ExternalLink className="w-3 h-3 opacity-70" />
          </a>
        </div>
        {months.map(m => (
          <MonthTable key={`${m.year}-${m.month}`} data={m} />
        ))}
      </div>
    </div>
  )
}
