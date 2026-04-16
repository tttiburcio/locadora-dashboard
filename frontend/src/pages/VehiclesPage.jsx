import { useState, useMemo } from 'react'
import { brl, pct, dias, brlShort } from '../utils/format'
import VehicleModal from '../components/VehicleModal'
import {
  Search, ChevronUp, ChevronDown, ChevronsUpDown,
  TrendingUp, TrendingDown, Filter, X,
} from 'lucide-react'

const STATUS_COLORS = {
  'ATIVO':   'badge-green',
  'LOCADO':  'badge-green',
  'MANUT':   'badge-amber',
  'INATIVO': 'badge-red',
  'PARADO':  'badge-red',
}

function statusBadge(status) {
  const s = (status || '').toUpperCase()
  const cls = Object.entries(STATUS_COLORS).find(([k]) => s.includes(k))?.[1] ?? 'badge-amber'
  return <span className={cls}>{status || '—'}</span>
}

function SortIcon({ col, sortCol, sortDir }) {
  if (sortCol !== col) return <ChevronsUpDown className="w-3 h-3 opacity-30" />
  return sortDir === 'asc'
    ? <ChevronUp className="w-3 h-3 text-g-400" />
    : <ChevronDown className="w-3 h-3 text-g-400" />
}

const COLUMNS = [
  { key: 'rank',              label: '#',            align: 'right',  fmt: v => v },
  { key: 'placa',             label: 'Placa',        align: 'left',   fmt: v => <span className="font-mono font-semibold text-g-100">{v}</span> },
  { key: 'modelo',            label: 'Modelo',       align: 'left',   fmt: v => v },
  { key: 'status',            label: 'Status',       align: 'left',   fmt: v => statusBadge(v) },
  { key: 'receita_total',     label: 'Receita',      align: 'right',  fmt: v => <span className="font-mono text-g-200">{brl(v)}</span> },
  { key: 'custo_total',       label: 'Custo',        align: 'right',  fmt: v => <span className="font-mono text-orange-300">{brl(v)}</span> },
  { key: 'margem',            label: 'Margem',       align: 'right',  fmt: v => (
    <span className={`font-mono font-semibold ${v >= 0 ? 'text-g-300' : 'text-red-300'}`}>{brl(v)}</span>
  )},
  { key: 'margem_pct',        label: '% Margem',     align: 'right',  fmt: v => (
    <span className={`text-xs font-semibold ${v >= 0 ? 'text-g-400' : 'text-red-400'}`}>{pct(v)}</span>
  )},
  { key: 'dias_trabalhado',   label: 'Dias Trab.',   align: 'right',  fmt: v => <span className="text-g-500 text-xs">{dias(v)}</span> },
  { key: 'receita_por_dia',   label: 'R$/Dia',       align: 'right',  fmt: v => v > 0 ? <span className="font-mono text-xs text-g-400">{brlShort(v)}</span> : <span className="text-g-700">—</span> },
  { key: 'custo_manutencao',  label: 'Manutenção',   align: 'right',  fmt: v => <span className="font-mono text-xs text-orange-400">{brl(v)}</span> },
  { key: 'custo_seguro',      label: 'Seguro',       align: 'right',  fmt: v => <span className="font-mono text-xs text-red-400">{brl(v)}</span> },
  { key: 'custo_impostos',    label: 'Impostos',     align: 'right',  fmt: v => <span className="font-mono text-xs text-purple-400">{brl(v)}</span> },
  { key: 'custo_rastreamento',label: 'Rastreamento', align: 'right',  fmt: v => <span className="font-mono text-xs text-amber-400">{brl(v)}</span> },
  { key: 'roi',               label: 'ROI',          align: 'right',  fmt: v => v !== 0 ? (
    <span className={`text-xs font-semibold ${v >= 0 ? 'text-g-400' : 'text-red-400'}`}>{pct(v)}</span>
  ) : <span className="text-g-700">—</span> },
]

export default function VehiclesPage({ vehicles, year }) {
  const [selectedPlaca, setSelectedPlaca] = useState(null)
  const [search, setSearch]               = useState('')
  const [sortCol, setSortCol]             = useState('margem')
  const [sortDir, setSortDir]             = useState('desc')
  const [filterStatus, setFilterStatus]   = useState('')
  const [showOnly, setShowOnly]           = useState('all') // all | profit | loss

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
    receita_total:    filtered.reduce((s, v) => s + v.receita_total, 0),
    custo_total:      filtered.reduce((s, v) => s + v.custo_total, 0),
    margem:           filtered.reduce((s, v) => s + v.margem, 0),
    dias_trabalhado:  filtered.reduce((s, v) => s + v.dias_trabalhado, 0),
    custo_manutencao: filtered.reduce((s, v) => s + v.custo_manutencao, 0),
    custo_seguro:     filtered.reduce((s, v) => s + v.custo_seguro, 0),
    custo_impostos:   filtered.reduce((s, v) => s + v.custo_impostos, 0),
    custo_rastreamento: filtered.reduce((s, v) => s + v.custo_rastreamento, 0),
  }), [filtered])

  return (
    <div className="flex flex-col gap-4">
      {/* Filters bar */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-g-600" />
          <input
            type="text"
            placeholder="Buscar placa ou modelo…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-2 bg-g-850 border border-g-800 rounded-lg text-g-200 text-sm placeholder-g-600 focus:outline-none focus:border-g-600 transition-colors"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-2.5 top-1/2 -translate-y-1/2">
              <X className="w-3 h-3 text-g-500 hover:text-g-300" />
            </button>
          )}
        </div>

        {/* Status filter */}
        <div className="flex items-center gap-1.5">
          <Filter className="w-3.5 h-3.5 text-g-600" />
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            className="bg-g-850 border border-g-800 rounded-lg text-g-300 text-xs px-3 py-2 focus:outline-none focus:border-g-600"
          >
            <option value="">Todos os status</option>
            {statuses.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        {/* Profit filter */}
        <div className="flex items-center gap-1 bg-g-850 border border-g-800 rounded-lg p-0.5">
          {[
            { val: 'all',    label: 'Todos' },
            { val: 'profit', label: 'Lucrativos' },
            { val: 'loss',   label: 'Deficitários' },
          ].map(o => (
            <button
              key={o.val}
              onClick={() => setShowOnly(o.val)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                showOnly === o.val
                  ? 'bg-g-700 text-g-100'
                  : 'text-g-500 hover:text-g-300'
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>

        <span className="text-g-600 text-xs ml-auto">
          {filtered.length} veículo{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Summary totals */}
      <div className="grid grid-cols-4 gap-2">
        <div className="card p-3 flex flex-col gap-0.5">
          <span className="text-g-600 text-xs">Receita Filtrada</span>
          <span className="text-g-200 font-semibold font-mono text-sm">{brl(totals.receita_total)}</span>
        </div>
        <div className="card p-3 flex flex-col gap-0.5">
          <span className="text-g-600 text-xs">Custo Filtrado</span>
          <span className="text-orange-300 font-semibold font-mono text-sm">{brl(totals.custo_total)}</span>
        </div>
        <div className="card p-3 flex flex-col gap-0.5">
          <span className="text-g-600 text-xs">Margem Filtrada</span>
          <span className={`font-semibold font-mono text-sm ${totals.margem >= 0 ? 'text-g-300' : 'text-red-300'}`}>{brl(totals.margem)}</span>
        </div>
        <div className="card p-3 flex flex-col gap-0.5">
          <span className="text-g-600 text-xs">% Margem</span>
          <span className={`font-semibold text-sm ${totals.margem >= 0 ? 'text-g-300' : 'text-red-300'}`}>
            {totals.receita_total > 0 ? pct(totals.margem / totals.receita_total * 100) : '—'}
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1100px]">
            <thead className="bg-g-800 sticky top-0">
              <tr>
                {COLUMNS.map(col => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className={`th ${col.align === 'left' ? 'th-left' : ''} cursor-pointer hover:text-g-200 select-none`}
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
              {filtered.map((v, i) => (
                <tr
                  key={v.placa}
                  className={`table-row ${v.margem < 0 ? 'bg-red-950/10 hover:bg-red-950/20' : ''}`}
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
                  <td colSpan={COLUMNS.length} className="td text-center text-g-600 py-12">
                    Nenhum veículo encontrado com os filtros atuais.
                  </td>
                </tr>
              )}
            </tbody>
            {/* Totals row */}
            {filtered.length > 1 && (
              <tfoot className="bg-g-800/80 border-t-2 border-g-700">
                <tr>
                  <td className="td td-left text-g-600 text-xs">—</td>
                  <td className="td td-left text-g-400 text-xs font-semibold" colSpan={3}>TOTAIS ({filtered.length})</td>
                  <td className="td"><span className="font-mono text-g-200 font-semibold">{brl(totals.receita_total)}</span></td>
                  <td className="td"><span className="font-mono text-orange-300 font-semibold">{brl(totals.custo_total)}</span></td>
                  <td className="td"><span className={`font-mono font-bold ${totals.margem >= 0 ? 'text-g-300' : 'text-red-300'}`}>{brl(totals.margem)}</span></td>
                  <td className="td"><span className={`text-xs font-bold ${totals.margem >= 0 ? 'text-g-400' : 'text-red-400'}`}>{totals.receita_total > 0 ? pct(totals.margem / totals.receita_total * 100) : '—'}</span></td>
                  <td className="td"><span className="text-g-500 text-xs">{dias(totals.dias_trabalhado)}</span></td>
                  <td className="td">—</td>
                  <td className="td"><span className="font-mono text-xs text-orange-400">{brl(totals.custo_manutencao)}</span></td>
                  <td className="td"><span className="font-mono text-xs text-red-400">{brl(totals.custo_seguro)}</span></td>
                  <td className="td"><span className="font-mono text-xs text-purple-400">{brl(totals.custo_impostos)}</span></td>
                  <td className="td"><span className="font-mono text-xs text-amber-400">{brl(totals.custo_rastreamento)}</span></td>
                  <td className="td">—</td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

      <p className="text-g-700 text-xs text-center">
        Clique em qualquer veículo para ver análise detalhada · Custos por data de execução (manutenção), vencimento (seguro/rastreamento) e AnoImposto (impostos)
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
