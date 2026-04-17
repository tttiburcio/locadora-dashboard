import { useState, useMemo } from 'react'
import { brl, pct, dias, brlShort } from '../utils/format'
import VehicleModal from '../components/VehicleModal'
import {
  Search, ChevronUp, ChevronDown, ChevronsUpDown,
  Filter, X, MapPin,
} from 'lucide-react'

const STATUS_COLORS = {
  'ATIVO':   'badge-green',
  'LOCADO':  'badge-green',
  'MANUT':   'badge-amber',
  'INATIVO': 'badge-red',
  'PARADO':  'badge-red',
}

function statusBadge(status) {
  const s   = (status || '').toUpperCase()
  const cls = Object.entries(STATUS_COLORS).find(([k]) => s.includes(k))?.[1] ?? 'badge-amber'
  return <span className={cls}>{status || '—'}</span>
}

function SortIcon({ col, sortCol, sortDir }) {
  if (sortCol !== col) return <ChevronsUpDown className="w-3 h-3 opacity-20" />
  return sortDir === 'asc'
    ? <ChevronUp   className="w-3 h-3 text-g-300" />
    : <ChevronDown className="w-3 h-3 text-g-300" />
}

const COLUMNS = [
  { key: 'rank',               label: '#',           align: 'right', fmt: v => <span className="text-g-700 tabular-nums">{v}</span> },
  { key: 'placa',              label: 'Placa',        align: 'left',  fmt: v => <span className="font-mono font-bold text-g-50 tracking-wide">{v}</span> },
  { key: 'modelo',             label: 'Modelo',       align: 'left',  fmt: v => <span className="text-g-300">{v}</span> },
  { key: 'status',             label: 'Status',       align: 'left',  fmt: v => statusBadge(v) },
  { key: 'receita_total',      label: 'Receita',      align: 'right', fmt: v => <span className="font-mono text-g-200 tabular-nums">{brl(v)}</span> },
  { key: 'custo_total',        label: 'Custo',        align: 'right', fmt: v => <span className="font-mono text-orange-300 tabular-nums">{brl(v)}</span> },
  { key: 'margem',             label: 'Margem',       align: 'right', fmt: v => (
    <span className={`font-mono font-semibold tabular-nums ${v >= 0 ? 'text-g-50' : 'text-red-300'}`}>{brl(v)}</span>
  )},
  { key: 'margem_pct',         label: '% Margem',     align: 'right', fmt: v => (
    <span className={`text-xs font-semibold tabular-nums ${v >= 0 ? 'text-g-300' : 'text-red-400'}`}>{pct(v)}</span>
  )},
  { key: 'dias_trabalhado',    label: 'Dias Trab.',   align: 'right', fmt: v => <span className="text-g-600 text-xs tabular-nums">{dias(v)}</span> },
  { key: 'receita_por_dia',    label: 'R$/Dia',       align: 'right', fmt: v => v > 0
    ? <span className="font-mono text-xs text-g-400 tabular-nums">{brlShort(v)}</span>
    : <span className="text-g-800">—</span> },
  { key: 'custo_manutencao',   label: 'Manutenção',   align: 'right', fmt: v => <span className="font-mono text-xs text-orange-400 tabular-nums">{brl(v)}</span> },
  { key: 'custo_seguro',       label: 'Seguro',       align: 'right', fmt: v => <span className="font-mono text-xs text-red-400 tabular-nums">{brl(v)}</span> },
  { key: 'custo_impostos',     label: 'Impostos',     align: 'right', fmt: v => <span className="font-mono text-xs text-purple-400 tabular-nums">{brl(v)}</span> },
  { key: 'custo_rastreamento', label: 'Rastreamento', align: 'right', fmt: v => <span className="font-mono text-xs text-amber-400 tabular-nums">{brl(v)}</span> },
  { key: 'roi',                label: 'ROI',          align: 'right', fmt: v => v !== 0
    ? <span className={`text-xs font-semibold tabular-nums ${v >= 0 ? 'text-g-300' : 'text-red-400'}`}>{pct(v)}</span>
    : <span className="text-g-800">—</span> },
]

export default function VehiclesPage({ vehicles, year, regions = [], region, onRegionChange }) {
  const [selectedPlaca, setSelectedPlaca] = useState(null)
  const [search, setSearch]               = useState('')
  const [sortCol, setSortCol]             = useState('margem')
  const [sortDir, setSortDir]             = useState('desc')
  const [filterStatus, setFilterStatus]   = useState('')
  const [showOnly, setShowOnly]           = useState('all')

  const statuses = useMemo(() =>
    [...new Set(vehicles.map(v => v.status).filter(Boolean))].sort(),
    [vehicles]
  )

  const filtered = useMemo(() => {
    let list = [...vehicles]
    if (search) {
      const q = search.toLowerCase()
      list = list.filter(v =>
        v.placa.toLowerCase().includes(q) ||
        v.modelo.toLowerCase().includes(q) ||
        v.marca.toLowerCase().includes(q)
      )
    }
    if (filterStatus) list = list.filter(v => v.status === filterStatus)
    if (showOnly === 'profit') list = list.filter(v => v.margem >= 0)
    if (showOnly === 'loss')   list = list.filter(v => v.margem < 0)
    list.sort((a, b) => {
      const av = a[sortCol] ?? 0
      const bv = b[sortCol] ?? 0
      if (typeof av === 'string') return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av)
      return sortDir === 'asc' ? av - bv : bv - av
    })
    return list
  }, [vehicles, search, sortCol, sortDir, filterStatus, showOnly])

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
          <div className="flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-g-700" />
            <select
              value={region || ''}
              onChange={e => onRegionChange && onRegionChange(e.target.value || null)}
              className="bg-g-900 border border-g-800 rounded-lg text-g-300 text-xs px-3 py-2 focus:outline-none focus:border-g-600"
            >
              <option value="">Todas as regiões</option>
              {regions.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
        )}

        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-g-700" />
          <input
            type="text"
            placeholder="Buscar placa ou modelo…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-200 text-sm placeholder-g-700 focus:outline-none focus:border-g-600 transition-colors"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-2.5 top-1/2 -translate-y-1/2">
              <X className="w-3 h-3 text-g-600 hover:text-g-300" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-1.5">
          <Filter className="w-3.5 h-3.5 text-g-700" />
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            className="bg-g-900 border border-g-800 rounded-lg text-g-400 text-xs px-3 py-2 focus:outline-none focus:border-g-600"
          >
            <option value="">Todos os status</option>
            {statuses.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        <div className="flex items-center gap-0.5 bg-g-900 border border-g-800 rounded-lg p-0.5">
          {[
            { val: 'all',    label: 'Todos' },
            { val: 'profit', label: 'Lucrativos' },
            { val: 'loss',   label: 'Deficit.' },
          ].map(o => (
            <button
              key={o.val}
              onClick={() => setShowOnly(o.val)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                showOnly === o.val
                  ? 'bg-g-700/30 text-g-50'
                  : 'text-g-600 hover:text-g-300'
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>

        <span className="text-g-700 text-xs ml-auto tabular-nums">
          {filtered.length} veículo{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Summary totals */}
      <div className="grid grid-cols-4 gap-2">
        <div className="card p-3 flex flex-col gap-0.5">
          <span className="text-g-700 text-xs">Receita</span>
          <span className="text-g-200 font-semibold font-mono text-sm tabular-nums">{brl(totals.receita_total)}</span>
        </div>
        <div className="card p-3 flex flex-col gap-0.5">
          <span className="text-g-700 text-xs">Custo</span>
          <span className="text-orange-300 font-semibold font-mono text-sm tabular-nums">{brl(totals.custo_total)}</span>
        </div>
        <div className="card p-3 flex flex-col gap-0.5">
          <span className="text-g-700 text-xs">Margem</span>
          <span className={`font-semibold font-mono text-sm tabular-nums ${totals.margem >= 0 ? 'text-g-50' : 'text-red-300'}`}>
            {brl(totals.margem)}
          </span>
        </div>
        <div className="card p-3 flex flex-col gap-0.5">
          <span className="text-g-700 text-xs">% Margem</span>
          <span className={`font-semibold text-sm tabular-nums ${totals.margem >= 0 ? 'text-g-200' : 'text-red-300'}`}>
            {totals.receita_total > 0 ? pct(totals.margem / totals.receita_total * 100) : '—'}
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1100px]">
            <thead className="bg-g-900 border-b border-g-800 sticky top-0">
              <tr>
                {COLUMNS.map(col => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className={`th ${col.align === 'left' ? 'th-left' : ''} cursor-pointer hover:text-g-200 select-none transition-colors`}
                  >
                    <div className={`flex items-center gap-1 ${col.align === 'right' ? 'justify-end' : ''}`}>
                      <span>{col.label}</span>
                      <SortIcon col={col.key} sortCol={sortCol} sortDir={sortDir} />
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((v) => (
                <tr
                  key={v.placa}
                  className={`table-row ${v.margem < 0 ? 'bg-red-950/10' : ''}`}
                  onClick={() => setSelectedPlaca(v.placa)}
                >
                  {COLUMNS.map(col => (
                    <td key={col.key} className={`td ${col.align === 'left' ? 'td-left' : ''}`}>
                      {col.fmt(v[col.key])}
                    </td>
                  ))}
                </tr>
              ))}
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
                  <td className="td td-left text-g-700 text-xs">—</td>
                  <td className="td td-left text-g-500 text-xs font-semibold uppercase tracking-wide" colSpan={3}>
                    TOTAIS ({filtered.length})
                  </td>
                  <td className="td"><span className="font-mono text-g-200 font-semibold tabular-nums">{brl(totals.receita_total)}</span></td>
                  <td className="td"><span className="font-mono text-orange-300 font-semibold tabular-nums">{brl(totals.custo_total)}</span></td>
                  <td className="td"><span className={`font-mono font-bold tabular-nums ${totals.margem >= 0 ? 'text-g-50' : 'text-red-300'}`}>{brl(totals.margem)}</span></td>
                  <td className="td"><span className={`text-xs font-bold tabular-nums ${totals.margem >= 0 ? 'text-g-300' : 'text-red-400'}`}>{totals.receita_total > 0 ? pct(totals.margem / totals.receita_total * 100) : '—'}</span></td>
                  <td className="td"><span className="text-g-600 text-xs tabular-nums">{dias(totals.dias_trabalhado)}</span></td>
                  <td className="td text-g-800">—</td>
                  <td className="td"><span className="font-mono text-xs text-orange-400 tabular-nums">{brl(totals.custo_manutencao)}</span></td>
                  <td className="td"><span className="font-mono text-xs text-red-400 tabular-nums">{brl(totals.custo_seguro)}</span></td>
                  <td className="td"><span className="font-mono text-xs text-purple-400 tabular-nums">{brl(totals.custo_impostos)}</span></td>
                  <td className="td"><span className="font-mono text-xs text-amber-400 tabular-nums">{brl(totals.custo_rastreamento)}</span></td>
                  <td className="td text-g-800">—</td>
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
          onClose={() => setSelectedPlaca(null)}
        />
      )}
    </div>
  )
}
