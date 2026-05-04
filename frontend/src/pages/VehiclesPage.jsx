import { useState, useMemo, useEffect } from 'react'
import { brl, pct, dias, brlShort } from '../utils/format'
import VehicleModal from '../components/VehicleModal'
import VehicleKmBadge from '../components/tracker/VehicleKmBadge'
import TrackerStatusBadge from '../components/tracker/TrackerStatusBadge'
import { useTrackerData } from '../hooks/useTrackerData'
import {
  Search, ChevronUp, ChevronDown, ChevronsUpDown,
  Filter, X, MapPin, Flame, AlertTriangle, ZapOff, ExternalLink,
} from 'lucide-react'
import { HIGH_USAGE_THRESHOLD, IDLE_KM_MONTH } from '../constants/trackerThresholds'
import { normalizePlaca } from '../utils/trackerApi'

const MAPWS_BASE = 'http://localhost:5174'

const STATUS_COLORS = {
  'ATIVO':      'bg-emerald-50 text-emerald-900 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-700/40 text-xs font-bold px-2 py-0.5 rounded-full inline-block select-none shadow-sm',
  'LOCADO':     'bg-emerald-50 text-emerald-900 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-700/40 text-xs font-bold px-2 py-0.5 rounded-full inline-block select-none shadow-sm',
  'FROTA':      'bg-emerald-50 text-emerald-900 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-700/40 text-xs font-bold px-2 py-0.5 rounded-full inline-block select-none shadow-sm',
  'ADM':        'bg-blue-50 text-blue-900 border border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-700/40 text-xs font-bold px-2 py-0.5 rounded-full inline-block select-none shadow-sm',
  'VENDIDO':    'bg-gray-50 text-gray-900 border border-gray-200 dark:bg-gray-900/40 dark:text-gray-300 dark:border-gray-700/40 text-xs font-bold px-2 py-0.5 rounded-full inline-block select-none shadow-sm',
  'DESATIVADO': 'bg-red-50 text-red-900 border border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-700/40 text-xs font-bold px-2 py-0.5 rounded-full inline-block select-none shadow-sm',
  'MANUT':      'bg-amber-50 text-amber-900 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-700/40 text-xs font-bold px-2 py-0.5 rounded-full inline-block select-none shadow-sm',
  'INATIVO':    'bg-red-50 text-red-900 border border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-700/40 text-xs font-bold px-2 py-0.5 rounded-full inline-block select-none shadow-sm',
  'PARADO':     'bg-red-50 text-red-900 border border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-700/40 text-xs font-bold px-2 py-0.5 rounded-full inline-block select-none shadow-sm',
}

function statusBadge(status) {
  const s = (status || '').toUpperCase()
  if (s.includes('FROTA') || s.includes('ATIVO') || s.includes('LOCADO')) {
    return <span style={{ backgroundColor: '#ecfdf5', color: '#064e3b', borderColor: '#a7f3d0', borderWidth: '1px', borderStyle: 'solid', padding: '2px 8px', borderRadius: '9999px', fontSize: '12px', fontWeight: 'bold', display: 'inline-block', whiteSpace: 'nowrap' }}>{status}</span>
  }
  if (s.includes('ADM')) {
    return <span style={{ backgroundColor: '#eff6ff', color: '#1e3a8a', borderColor: '#bfdbfe', borderWidth: '1px', borderStyle: 'solid', padding: '2px 8px', borderRadius: '9999px', fontSize: '12px', fontWeight: 'bold', display: 'inline-block', whiteSpace: 'nowrap' }}>{status}</span>
  }
  if (s.includes('VENDIDO')) {
    return <span style={{ backgroundColor: '#f9fafb', color: '#111827', borderColor: '#e5e7eb', borderWidth: '1px', borderStyle: 'solid', padding: '2px 8px', borderRadius: '9999px', fontSize: '12px', fontWeight: 'bold', display: 'inline-block', whiteSpace: 'nowrap' }}>{status}</span>
  }
  if (s.includes('DESATIVADO') || s.includes('INATIVO') || s.includes('PARADO')) {
    return <span style={{ backgroundColor: '#fef2f2', color: '#7f1d1d', borderColor: '#fecaca', borderWidth: '1px', borderStyle: 'solid', padding: '2px 8px', borderRadius: '9999px', fontSize: '12px', fontWeight: 'bold', display: 'inline-block', whiteSpace: 'nowrap' }}>{status}</span>
  }
  return <span style={{ backgroundColor: '#fffbeb', color: '#78350f', borderColor: '#fde68a', borderWidth: '1px', borderStyle: 'solid', padding: '2px 8px', borderRadius: '9999px', fontSize: '12px', fontWeight: 'bold', display: 'inline-block', whiteSpace: 'nowrap' }}>{status || '—'}</span>
}

function SortIcon({ col, sortCol, sortDir }) {
  if (sortCol !== col) return <ChevronsUpDown className="w-3 h-3 opacity-20" />
  return sortDir === 'asc'
    ? <ChevronUp   className="w-3 h-3 text-g-300" />
    : <ChevronDown className="w-3 h-3 text-g-300" />
}

const COLUMNS = [
  { key: 'placa',              label: 'Placa',        align: 'left',  fmt: v => <span className="font-mono font-bold text-g-50 text-[15px] tracking-wide">{v}</span> },
  { key: 'modelo',             label: 'Modelo',       align: 'left',  fmt: v => <span className="text-g-300 text-sm font-semibold">{v}</span> },
  { key: 'status',             label: 'Status',       align: 'left',  fmt: v => statusBadge(v) },
  { key: 'receita_total',      label: 'Receita',      align: 'left',  fmt: v => <span className="font-mono text-g-200 text-sm font-bold tabular-nums">{brl(v)}</span> },
  { key: 'custo_total',        label: 'Custo',        align: 'left',  fmt: v => <span className="font-mono text-orange-600 font-bold dark:text-orange-400 text-sm tabular-nums">{brl(v)}</span> },
  { key: 'margem',             label: 'Margem',       align: 'left',  fmt: v => (
    <span className={`font-mono font-bold text-sm tabular-nums ${v >= 0 ? 'text-g-50' : 'text-red-600 dark:text-red-400'}`}>{brl(v)}</span>
  )},
  { key: 'margem_pct',         label: '% Margem',     align: 'left',  fmt: v => (
    <span className={`text-sm font-bold tabular-nums ${v >= 0 ? 'text-g-300' : 'text-red-600 dark:text-red-400'}`}>{pct(v)}</span>
  )},
  { key: 'dias_trabalhado',    label: 'Dias Trab.',   align: 'left',  fmt: v => <span className="text-g-600 text-sm font-semibold tabular-nums">{dias(v)}</span> },
  { key: 'receita_por_dia',    label: 'R$/Dia',       align: 'left',  fmt: v => v > 0
    ? <span className="font-mono text-sm text-g-400 font-bold tabular-nums">{brlShort(v)}</span>
    : <span className="text-g-800 text-sm font-bold">—</span> },
  { key: 'custo_manutencao',   label: 'Manutenção',   align: 'left',  fmt: v => <span className="font-mono font-bold text-sm text-orange-600 dark:text-orange-400 tabular-nums">{brl(v)}</span> },
  { key: 'custo_seguro',       label: 'Seguro',       align: 'left',  fmt: v => <span className="font-mono font-bold text-sm text-red-600 dark:text-red-400 tabular-nums">{brl(v)}</span> },
  { key: 'custo_impostos',     label: 'Impostos',     align: 'left',  fmt: v => <span className="font-mono font-bold text-sm text-purple-600 dark:text-purple-400 tabular-nums">{brl(v)}</span> },
  { key: 'custo_rastreamento', label: 'Rastreamento', align: 'left',  fmt: v => <span className="font-mono font-bold text-sm text-amber-600 dark:text-amber-400 tabular-nums">{brl(v)}</span> },
  { key: '_km_mes',            label: 'KM Tracker',   align: 'left',  fmt: () => null },
]

export default function VehiclesPage({
  vehicles, year, regions = [], region, onRegionChange,
  trackerFilter = null, onTrackerFilterConsumed,
}) {
  // Enrich vehicles with tracker km so the _km_mes column is sortable
  const { trackerOnline, trackerUsage, getVehicleKm, highUsageVehicles, idleVehicles } = useTrackerData({ year })
  const [selectedPlaca, setSelectedPlaca] = useState(null)
  const [search, setSearch]               = useState('')
  const [sortCol, setSortCol]             = useState('margem')
  const [sortDir, setSortDir]             = useState('desc')
  const [filterStatus, setFilterStatus]   = useState('')
  const [showOnly, setShowOnly]           = useState(() => {
    try { return trackerFilter || localStorage.getItem('vehicles_filter') || 'all' } catch { return 'all' }
  })

  useEffect(() => {
    if (trackerFilter && onTrackerFilterConsumed) onTrackerFilterConsumed()
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  function handleShowOnly(val) {
    setShowOnly(val)
    try { localStorage.setItem('vehicles_filter', val) } catch {}
  }

  const highUsagePlacas = useMemo(
    () => new Set(highUsageVehicles.map(v => v.placa)),
    [highUsageVehicles],
  )
  const idlePlacas = useMemo(
    () => new Set(idleVehicles.map(v => v.placa)),
    [idleVehicles],
  )

  const isHighUsage = useMemo(() => {
    if (!selectedPlaca) return false
    const vkm = getVehicleKm(selectedPlaca)
    return vkm !== null && vkm.kmDia > HIGH_USAGE_THRESHOLD
  }, [selectedPlaca, getVehicleKm])

  const vehiclesEnriched = useMemo(() =>
    vehicles.map(v => {
      const isAdm = v.placa && (v.placa.toUpperCase() === 'TJW7I85' || v.placa.toUpperCase() === 'ERA6A58')
      return {
        ...v,
        status: isAdm ? 'ADM' : v.status,
        _km_mes: getVehicleKm(v.placa)?.km ?? null
      }
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [vehicles, trackerUsage],
  )

  const statuses = useMemo(() =>
    [...new Set(vehiclesEnriched.map(v => v.status).filter(Boolean))].sort(),
    [vehiclesEnriched]
  )

  const filtered = useMemo(() => {
    let list = [...vehiclesEnriched]
    if (search) {
      const q = search.toLowerCase()
      list = list.filter(v =>
        v.placa.toLowerCase().includes(q) ||
        v.modelo.toLowerCase().includes(q) ||
        v.marca.toLowerCase().includes(q)
      )
    }
    if (filterStatus) list = list.filter(v => v.status === filterStatus)
    if (showOnly === 'profit')     list = list.filter(v => v.margem >= 0)
    if (showOnly === 'loss')       list = list.filter(v => v.margem < 0)
    if (showOnly === 'high_usage') list = list.filter(v => highUsagePlacas.has(normalizePlaca(v.placa)))
    if (showOnly === 'idle')       list = list.filter(v => idlePlacas.has(normalizePlaca(v.placa)))
    list.sort((a, b) => {
      let av = a[sortCol]
      let bv = b[sortCol]
      
      // Coloca valores nulos sempre no final da lista
      if ((av === null || av === undefined) && (bv === null || bv === undefined)) return 0;
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;

      if (typeof av === 'string') return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
      return sortDir === 'asc' ? av - bv : bv - av
    })
    return list
  }, [vehiclesEnriched, search, sortCol, sortDir, filterStatus, showOnly, highUsagePlacas, idlePlacas])

  const handleSort = (col) => {
    if (sortCol === col) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortCol(col); setSortDir('desc') }
  }

  const totals = useMemo(() => ({
    receita_total:       filtered.reduce((s, v) => s + v.receita_total,       0),
    custo_total:         filtered.reduce((s, v) => s + v.custo_total,         0),
    margem:              filtered.reduce((s, v) => s + v.margem,              0),
    dias_trabalhado:     filtered.reduce((s, v) => s + v.dias_trabalhado,     0),
    custo_manutencao:    filtered.reduce((s, v) => s + v.custo_manutencao,    0),
    custo_seguro:        filtered.reduce((s, v) => s + v.custo_seguro,        0),
    custo_impostos:      filtered.reduce((s, v) => s + v.custo_impostos,      0),
    custo_rastreamento:  filtered.reduce((s, v) => s + v.custo_rastreamento,  0),
  }), [filtered])

  return (
    <div className="flex flex-col gap-4">
      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Region/contract filter */}
        {regions.length > 0 && (
          <div className="flex items-center gap-2">
            <MapPin className="w-4 h-4 text-g-500" />
            <select
              value={region || ''}
              onChange={e => onRegionChange && onRegionChange(e.target.value || null)}
              className="bg-g-900 border border-g-800 rounded-xl text-g-200 text-sm px-4 py-2.5 focus:outline-none focus:border-g-600 shadow-sm appearance-none cursor-pointer"
            >
              <option value="">Todas as regiões</option>
              {regions.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
        )}

        <div className="relative flex-1 min-w-[240px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-g-500" />
          <input
            type="text"
            placeholder="Buscar placa ou modelo…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-10 pr-3 py-2.5 bg-g-900 border border-g-800 rounded-xl text-g-100 text-sm placeholder-g-700 focus:outline-none focus:border-g-600 transition-colors shadow-sm"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2">
              <X className="w-3.5 h-3.5 text-g-600 hover:text-g-300" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-g-500" />
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            className="bg-g-900 border border-g-800 rounded-xl text-g-200 text-sm px-4 py-2.5 focus:outline-none focus:border-g-600 shadow-sm appearance-none cursor-pointer"
          >
            <option value="">Todos os status</option>
            {statuses.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        <div className="flex items-center gap-1 bg-g-900 border border-g-800 rounded-xl p-1 shadow-sm">
          {[
            { val: 'all',    label: 'Todos' },
            { val: 'profit', label: 'Lucrativos' },
            { val: 'loss',   label: 'Deficitários' },
          ].map(o => (
            <button
              key={o.val}
              onClick={() => handleShowOnly(o.val)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                showOnly === o.val
                  ? 'bg-g-700/30 text-g-50'
                  : 'text-g-600 hover:text-g-300'
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>

        <span className="text-g-700 text-xs tabular-nums">
          {filtered.length} veículo{filtered.length !== 1 ? 's' : ''}
        </span>
        <TrackerStatusBadge online={trackerOnline} />
        {trackerOnline === true && (
          <a
            href={MAPWS_BASE}
            target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide bg-indigo-50/80 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 hover:border-indigo-300 transition-all cursor-pointer shadow-sm"
          >
            <MapPin className="w-3 h-3 text-indigo-600" />
            MapWS
          </a>
        )}

        {/* Tracker quick filters — only when data available */}
        {trackerOnline === true && (highUsageVehicles.length > 0 || idleVehicles.length > 0) && (
          <div className="flex items-center gap-1 bg-g-900 border border-g-800 rounded-xl p-1 shadow-sm">
            {highUsageVehicles.length > 0 && (
              <button
                onClick={() => handleShowOnly(showOnly === 'high_usage' ? 'all' : 'high_usage')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  showOnly === 'high_usage'
                    ? 'bg-red-500/20 text-red-400'
                    : 'text-g-600 hover:text-red-400'
                }`}
              >
                <Flame className="w-3 h-3" />
                Uso Excessivo ({highUsageVehicles.length})
              </button>
            )}
            {idleVehicles.length > 0 && (
              <button
                onClick={() => handleShowOnly(showOnly === 'idle' ? 'all' : 'idle')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  showOnly === 'idle'
                    ? 'bg-amber-500/20 text-amber-400'
                    : 'text-g-600 hover:text-amber-400'
                }`}
              >
                <ZapOff className="w-3 h-3" />
                Ociosos ({idleVehicles.length})
              </button>
            )}
          </div>
        )}
      </div>

      {/* Summary totals */}
      <div className="grid grid-cols-4 gap-3">
        <div className="card p-3.5 flex flex-col gap-1">
          <span className="text-g-600 text-[10px] uppercase tracking-widest font-bold">Receita Filtrada</span>
          <span className="text-g-500 font-bold font-mono text-xl tabular-nums">{brl(totals.receita_total)}</span>
        </div>
        <div className="card p-3.5 flex flex-col gap-1">
          <span className="text-g-600 text-[10px] uppercase tracking-widest font-bold">Custo Filtrado</span>
          <span className="text-orange-500 font-bold font-mono text-xl tabular-nums">{brl(totals.custo_total)}</span>
        </div>
        <div className="card p-3.5 flex flex-col gap-1 border-l-4 border-l-emerald-500/20">
          <span className="text-g-600 text-[10px] uppercase tracking-widest font-bold">Margem Filtrada</span>
          <span className={`font-bold font-mono text-xl tabular-nums ${totals.margem >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
            {brl(totals.margem)}
          </span>
        </div>
        <div className="card p-3.5 flex flex-col gap-1">
          <span className="text-g-600 text-[10px] uppercase tracking-widest font-bold">% Margem</span>
          <span className={`font-bold font-mono text-xl tabular-nums ${totals.margem >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
            {totals.receita_total > 0 ? pct(totals.margem / totals.receita_total * 100) : '—'}
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1200px] text-left">
            <thead className="bg-g-900 border-b border-g-800 sticky top-0">
              <tr>
                {COLUMNS.map(col => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className="th text-left cursor-pointer hover:text-g-200 select-none transition-colors"
                  >
                    <div className="flex items-center gap-1">
                      <span>{col.label}</span>
                      <SortIcon col={col.key} sortCol={sortCol} sortDir={sortDir} />
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((v) => {
                const vkm = getVehicleKm(v.placa)
                return (
                  <tr
                    key={v.placa}
                    className="table-row"
                    onClick={() => setSelectedPlaca(v.placa)}
                  >
                    {COLUMNS.map(col => (
                      <td key={col.key} className="td text-left">
                        {col.key === '_km_mes'
                          ? <VehicleKmBadge kmValue={vkm?.km ?? null} dailyKm={vkm?.kmDia} isIdle={idlePlacas.has(normalizePlaca(v.placa))} />
                          : col.key === 'placa'
                          ? (
                            <span className="inline-flex items-center gap-1.5">
                              <span className="font-mono font-bold text-g-50 text-[15px] tracking-wide">{v.placa}</span>
                              {vkm?.kmDia > HIGH_USAGE_THRESHOLD && <Flame className="w-3 h-3 text-red-400" />}
                              {idlePlacas.has(normalizePlaca(v.placa)) && <ZapOff className="w-3 h-3 text-amber-500" />}
                            </span>
                          )
                          : col.fmt(v[col.key])}
                      </td>
                    ))}
                  </tr>
                )
              })}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={COLUMNS.length} className="td text-center text-g-700 py-16">
                    Nenhum veículo encontrado.
                  </td>
                </tr>
              )}
            </tbody>
            {filtered.length > 1 && (
              <tfoot className="bg-g-900/80 border-t-2 border-g-700">
                <tr>
                  <td className="td text-g-500 text-sm font-semibold uppercase tracking-wide" colSpan={3}>
                    TOTAIS ({filtered.length})
                  </td>
                  <td className="td">
                    <span className="font-mono text-g-200 font-semibold tabular-nums text-sm">{brl(totals.receita_total)}</span>
                  </td>
                  <td className="td">
                    <span className="font-mono text-orange-300 font-semibold tabular-nums text-sm">{brl(totals.custo_total)}</span>
                  </td>
                  <td className="td">
                    <span className={`font-mono font-bold tabular-nums text-sm ${totals.margem >= 0 ? 'text-g-50' : 'text-red-300'}`}>
                      {brl(totals.margem)}
                    </span>
                  </td>
                  <td className="td">
                    <span className={`text-sm font-bold tabular-nums ${totals.margem >= 0 ? 'text-g-300' : 'text-red-400'}`}>
                      {totals.receita_total > 0 ? pct(totals.margem / totals.receita_total * 100) : '—'}
                    </span>
                  </td>
                  <td className="td">
                    <span className="text-g-600 text-sm tabular-nums">{dias(totals.dias_trabalhado)}</span>
                  </td>
                  <td className="td text-g-800 text-sm">—</td>
                  <td className="td">
                    <span className="font-mono text-sm text-orange-400 tabular-nums">{brl(totals.custo_manutencao)}</span>
                  </td>
                  <td className="td">
                    <span className="font-mono text-sm text-red-400 tabular-nums">{brl(totals.custo_seguro)}</span>
                  </td>
                  <td className="td">
                    <span className="font-mono text-sm text-purple-400 tabular-nums">{brl(totals.custo_impostos)}</span>
                  </td>
                  <td className="td">
                    <span className="font-mono text-sm text-amber-400 tabular-nums">{brl(totals.custo_rastreamento)}</span>
                  </td>
                  <td className="td text-g-800 text-sm">—</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

      <p className="text-g-800 text-xs text-center">
        Clique em qualquer veículo para ver análise detalhada
      </p>

      {selectedPlaca && (
        <VehicleModal
          placa={selectedPlaca}
          year={year}
          trackerOnline={trackerOnline}
          isHighUsage={isHighUsage}
          onClose={() => setSelectedPlaca(null)}
        />
      )}
    </div>
  )
}
