import { useEffect, useState, useMemo, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { getMaintenanceAnalysis, dbListManutencoes, dbAtualizarManutencao, dbDeletarManutencao } from '../utils/api'
import { brl, brlShort, num, dateBR } from '../utils/format'
import KPICard from '../components/KPICard'
import AbrirManutencaoModal   from '../components/AbrirManutencaoModal'
import FinalizarManutencaoModal from '../components/FinalizarManutencaoModal'
import {
  FornecedorChart, SistemaTreemap, TipoPie,
  ImplementoRadial, TrendProjectionChart, ServicosChart,
  MonthlyBarChart,
} from '../components/charts/MaintenanceCharts'
import {
  Wrench, DollarSign, Hash, Award, Search, X,
  Calendar, AlertTriangle, ChevronDown, ChevronUp,
  Activity, Loader2, TrendingUp, Plus, CheckCircle,
  Truck, Clock, AlertCircle, Trash2, BarChart2, Pencil,
} from 'lucide-react'

// ── Status helpers ────────────────────────────────────────────────────
const STATUS_LABEL = {
  aberta:           { label: 'Aberta',            color: 'bg-blue-50 text-blue-700 border-blue-200' },
  em_andamento:     { label: 'Em andamento',       color: 'bg-amber-50 text-amber-700 border-amber-200' },
  aguardando_peca:  { label: 'Aguardando peça',    color: 'bg-orange-50 text-orange-700 border-orange-200' },
  pendente:         { label: 'Pendente',           color: 'bg-slate-100 text-slate-600 border-slate-300' },
  finalizada:       { label: 'Finalizada',         color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
}

function StatusBadge({ status }) {
  const s = STATUS_LABEL[status] || { label: status, color: 'bg-g-850 text-g-500 border-g-800' }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${s.color}`}>
      {s.label}
    </span>
  )
}

// ── Componentes de layout compartilhados ─────────────────────────────
function Section({ title, icon: Icon, children, className = '' }) {
  return (
    <section className={className}>
      <div className="flex items-center gap-2.5 mb-4">
        <div className="p-1.5 bg-g-850 border border-g-800 rounded-lg">
          <Icon className="w-4 h-4 text-g-600" />
        </div>
        <h2 className="text-g-500 font-semibold text-xs uppercase tracking-widest">{title}</h2>
        <div className="flex-1 h-px bg-g-800" />
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

// ── Helpers de filtro/ordenação ───────────────────────────────────────
function diasParados(dataEntrada, dataExecucao = null) {
  const d1 = new Date(dataEntrada)
  if (isNaN(d1)) return null
  const d2 = dataExecucao ? new Date(dataExecucao) : new Date()
  if (isNaN(d2)) return null
  return Math.max(0, Math.round((d2 - d1) / 86400000))
}

function applyFilterSort(list, filter, sortState, fields) {
  let r = list
  if (filter.trim()) {
    const q = filter.toLowerCase()
    r = r.filter(m => fields.some(f => (m[f] || '').toLowerCase().includes(q)))
  }
  if (sortState.col) {
    const { col, dir } = sortState
    r = [...r].sort((a, b) => {
      const av = a[col] ?? '', bv = b[col] ?? ''
      const an = parseFloat(av), bn = parseFloat(bv)
      if (!isNaN(an) && !isNaN(bn)) return dir === 'asc' ? an - bn : bn - an
      const as = av.toString().toLowerCase(), bs = bv.toString().toLowerCase()
      return dir === 'asc' ? (as < bs ? -1 : as > bs ? 1 : 0) : (as > bs ? -1 : as < bs ? 1 : 0)
    })
  }
  return r
}

function nextOsNumber(finalizadas) {
  const pattern = /^OS-\d{4}-(\d+)$/
  const nums = finalizadas
    .map(f => f.id_ord_serv?.match(pattern)?.[1])
    .filter(Boolean)
    .map(Number)
  const max = nums.length > 0 ? Math.max(...nums) : 0
  return `OS-${new Date().getFullYear()}-${String(max + 1).padStart(4, '0')}`
}

function SortableHeader({ label, col, sortState, onSort, className = '' }) {
  const active = sortState.col === col
  return (
    <th
      className={`th th-left cursor-pointer select-none hover:text-g-300 transition-colors ${active ? 'text-g-200' : ''} ${className}`}
      onClick={() => onSort(col)}
    >
      <span className="flex items-center gap-1">
        {label}
        {active
          ? (sortState.dir === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />)
          : <ChevronDown className="w-3 h-3 opacity-20" />}
      </span>
    </th>
  )
}

// ════════════════════════════════════════════════════════════════════
// ABA GESTÃO — tabelas CRUD
// ════════════════════════════════════════════════════════════════════
function GestaoTab() {
  const [abertas,      setAbertas]      = useState([])
  const [finalizadas,  setFinalizadas]  = useState([])
  const [loading,      setLoading]      = useState(true)
  const [subTab,       setSubTab]       = useState('em_andamento')
  const [modalAbrir,   setModalAbrir]   = useState(false)
  const [modalFin,     setModalFin]     = useState(null)
  const [modalEdit,    setModalEdit]    = useState(null)
  const [modalInsert,  setModalInsert]  = useState(false)
  const [modalEditFin, setModalEditFin] = useState(null)
  const [confirmDel,   setConfirmDel]   = useState(null)
  const [filterAberta, setFilterAberta] = useState('')
  const [filterFin,    setFilterFin]    = useState('')
  const [sortAberta,   setSortAberta]   = useState({ col: null, dir: 'asc' })
  const [sortFin,      setSortFin]      = useState({ col: null, dir: 'asc' })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [ab, fin] = await Promise.all([
        dbListManutencoes(null).then(list =>
          list.filter(m => m.status_manutencao !== 'finalizada')
        ),
        dbListManutencoes('finalizada'),
      ])
      setAbertas(ab)
      setFinalizadas(fin)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleSaved = () => {
    setModalAbrir(false)
    setModalFin(null)
    setModalEdit(null)
    setModalInsert(false)
    setModalEditFin(null)
    load()
  }

  const handleStatusChange = async (manut, newStatus) => {
    await dbAtualizarManutencao(manut.id, { status_manutencao: newStatus })
    load()
  }

  const handleDelete = async (id) => {
    await dbDeletarManutencao(id)
    setConfirmDel(null)
    load()
  }

  const sortAbertaBy = col => setSortAberta(s => s.col !== col ? { col, dir: 'asc' } : s.dir === 'asc' ? { col, dir: 'desc' } : { col: null, dir: 'asc' })
  const sortFinBy    = col => setSortFin(s => s.col !== col ? { col, dir: 'asc' } : s.dir === 'asc' ? { col, dir: 'desc' } : { col: null, dir: 'asc' })

  const emAndamento = abertas.filter(m => m.status_manutencao === 'em_andamento')
  const aguardando  = abertas.filter(m => m.status_manutencao === 'aguardando_peca')
  const pendente    = abertas.filter(m => m.status_manutencao === 'pendente')
  const todasAbertas = abertas

  const filteredAbertas = useMemo(() =>
    applyFilterSort(todasAbertas, filterAberta, sortAberta, ['placa', 'fornecedor', 'status_manutencao', 'modelo', 'sistema', 'servico']),
    [todasAbertas, filterAberta, sortAberta]
  )

  const filteredFin = useMemo(() =>
    applyFilterSort(finalizadas, filterFin, sortFin, ['placa', 'fornecedor', 'modelo', 'sistema', 'servico', 'id_ord_serv']),
    [finalizadas, filterFin, sortFin]
  )

  return (
    <div className="flex flex-col gap-6">

      {/* KPIs rápidos */}
      <div className="grid grid-cols-4 gap-3">
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg">
            <Clock className="w-4 h-4 text-amber-600" />
          </div>
          <div>
            <p className="text-g-600 text-xs uppercase tracking-wider">Em andamento</p>
            <p className="text-g-200 font-bold text-xl">{emAndamento.length}</p>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 bg-orange-50 border border-orange-200 rounded-lg">
            <AlertCircle className="w-4 h-4 text-orange-600" />
          </div>
          <div>
            <p className="text-g-600 text-xs uppercase tracking-wider">Aguardando peça</p>
            <p className="text-g-200 font-bold text-xl">{aguardando.length}</p>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 bg-slate-100 border border-slate-300 rounded-lg">
            <AlertTriangle className="w-4 h-4 text-slate-500" />
          </div>
          <div>
            <p className="text-g-600 text-xs uppercase tracking-wider">Pendente</p>
            <p className="text-g-200 font-bold text-xl">{pendente.length}</p>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 bg-emerald-50 border border-emerald-200 rounded-lg">
            <CheckCircle className="w-4 h-4 text-emerald-600" />
          </div>
          <div>
            <p className="text-g-600 text-xs uppercase tracking-wider">Finalizadas (total)</p>
            <p className="text-g-200 font-bold text-xl">{finalizadas.length}</p>
          </div>
        </div>
      </div>

      {/* Sub-tabs + botões de ação */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1 bg-g-850 border border-g-800 rounded-xl p-1">
          {[
            { key: 'em_andamento', label: `Em andamento (${todasAbertas.length})` },
            { key: 'finalizadas',  label: `Finalizadas (${finalizadas.length})` },
          ].map(t => (
            <button
              key={t.key}
              onClick={() => setSubTab(t.key)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                subTab === t.key
                  ? 'bg-white shadow-sm text-g-200 border border-g-800'
                  : 'text-g-600 hover:text-g-400'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          {subTab === 'em_andamento' && (
            <button
              onClick={() => setModalAbrir(true)}
              className="flex items-center gap-2 px-4 py-2 bg-g-100 text-white rounded-lg text-sm font-medium hover:bg-g-50 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Nova OS
            </button>
          )}
          {subTab === 'finalizadas' && (
            <button
              onClick={() => setModalInsert(true)}
              className="flex items-center gap-2 px-4 py-2 bg-g-100 text-white rounded-lg text-sm font-medium hover:bg-g-50 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Inserir OS
            </button>
          )}
        </div>
      </div>

      {/* Tabela Em Andamento */}
      {subTab === 'em_andamento' && (
        <>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-g-600" />
            <input
              value={filterAberta}
              onChange={e => setFilterAberta(e.target.value)}
              placeholder="Filtrar por placa, fornecedor, status, modelo, sistema, serviço…"
              className="w-full pl-9 pr-9 py-2 bg-g-900 border border-g-800 rounded-lg text-g-400 text-sm placeholder-g-700 focus:outline-none focus:border-g-100 transition-colors"
            />
            {filterAberta && (
              <button onClick={() => setFilterAberta('')} className="absolute right-3 top-1/2 -translate-y-1/2">
                <X className="w-3.5 h-3.5 text-g-600 hover:text-g-400" />
              </button>
            )}
          </div>
          <div className="card overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center h-32 gap-2 text-g-600 text-sm">
                <Loader2 className="w-4 h-4 animate-spin" /> Carregando…
              </div>
            ) : todasAbertas.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-40 gap-2 text-g-600">
                <Truck className="w-8 h-8 opacity-30" />
                <p className="text-sm">Nenhuma manutenção em andamento</p>
                <button onClick={() => setModalAbrir(true)} className="text-g-100 text-xs font-medium hover:underline">
                  Registrar nova OS
                </button>
              </div>
            ) : filteredAbertas.length === 0 ? (
              <div className="flex items-center justify-center h-24 gap-2 text-g-600 text-sm">
                <Search className="w-4 h-4" /> Nenhum resultado para "{filterAberta}"
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[860px]">
                  <thead className="bg-g-850 border-b border-g-800">
                    <tr>
                      <SortableHeader label="Placa"     col="placa"             sortState={sortAberta} onSort={sortAbertaBy} />
                      <SortableHeader label="Modelo"    col="modelo"            sortState={sortAberta} onSort={sortAbertaBy} />
                      <SortableHeader label="Fornecedor" col="fornecedor"       sortState={sortAberta} onSort={sortAbertaBy} />
                      <SortableHeader label="Sistema / Serviço" col="sistema"   sortState={sortAberta} onSort={sortAbertaBy} />
                      <SortableHeader label="Status"    col="status_manutencao" sortState={sortAberta} onSort={sortAbertaBy} />
                      <SortableHeader label="Entrada"   col="data_entrada"      sortState={sortAberta} onSort={sortAbertaBy} />
                      <th className="th">Dias</th>
                      <th className="th">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAbertas.map(m => {
                      const dias = m.indisponivel && m.data_entrada ? diasParados(m.data_entrada) : null
                      return (
                        <tr key={m.id} className="table-row">
                          <td className="td td-left font-mono font-bold text-g-200">{m.placa}</td>
                          <td className="td td-left text-g-500">{m.modelo || '—'}</td>
                          <td className="td td-left text-g-500">{m.fornecedor || '—'}</td>
                          <td className="td td-left">
                            <p className="text-g-400 text-xs">{m.sistema || '—'}</p>
                            <p className="text-g-600 text-xs truncate max-w-[180px]">{m.servico || '—'}</p>
                          </td>
                          <td className="td td-left">
                            <StatusBadge status={m.status_manutencao} />
                          </td>
                          <td className="td td-left text-xs text-g-500 tabular-nums">
                            {dateBR(m.data_entrada)}
                          </td>
                          <td className="td tabular-nums text-xs">
                            {dias !== null
                              ? <span className={dias > 30 ? 'text-red-500 font-semibold' : dias > 7 ? 'text-amber-500 font-medium' : 'text-g-500'}>{dias}</span>
                              : <span className="text-g-700">—</span>
                            }
                          </td>
                          <td className="td">
                            <div className="flex items-center justify-end gap-1">
                              {m.status_manutencao === 'em_andamento' && (
                                <button
                                  onClick={() => handleStatusChange(m, 'aguardando_peca')}
                                  title="Marcar como aguardando peça"
                                  className="px-2 py-1 text-xs text-orange-600 border border-orange-200 rounded-lg hover:bg-orange-50 transition-colors"
                                >
                                  Ag. peça
                                </button>
                              )}
                              {m.status_manutencao === 'aguardando_peca' && (
                                <button
                                  onClick={() => handleStatusChange(m, 'em_andamento')}
                                  title="Retomar andamento"
                                  className="px-2 py-1 text-xs text-amber-600 border border-amber-200 rounded-lg hover:bg-amber-50 transition-colors"
                                >
                                  Retomar
                                </button>
                              )}
                              {/* Editar */}
                              <button
                                onClick={() => setModalEdit(m)}
                                title="Editar OS"
                                className="p-1.5 text-g-600 hover:text-g-100 hover:bg-g-850 rounded-lg transition-colors"
                              >
                                <Pencil className="w-3.5 h-3.5" />
                              </button>
                              {/* Finalizar */}
                              <button
                                onClick={() => setModalFin(m)}
                                className="px-2 py-1 text-xs text-g-100 border border-emerald-200 rounded-lg hover:bg-emerald-50 transition-colors"
                              >
                                Finalizar
                              </button>
                              {/* Excluir */}
                              <button
                                onClick={() => setConfirmDel(m.id)}
                                className="p-1.5 text-g-700 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {/* Tabela Finalizadas */}
      {subTab === 'finalizadas' && (
        <>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-g-600" />
            <input
              value={filterFin}
              onChange={e => setFilterFin(e.target.value)}
              placeholder="Filtrar por placa, fornecedor, modelo, sistema, serviço, nº OS…"
              className="w-full pl-9 pr-9 py-2 bg-g-900 border border-g-800 rounded-lg text-g-400 text-sm placeholder-g-700 focus:outline-none focus:border-g-100 transition-colors"
            />
            {filterFin && (
              <button onClick={() => setFilterFin('')} className="absolute right-3 top-1/2 -translate-y-1/2">
                <X className="w-3.5 h-3.5 text-g-600 hover:text-g-400" />
              </button>
            )}
          </div>
          <div className="card overflow-hidden">
            {loading ? (
              <div className="flex items-center justify-center h-32 gap-2 text-g-600 text-sm">
                <Loader2 className="w-4 h-4 animate-spin" /> Carregando…
              </div>
            ) : finalizadas.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-40 gap-2 text-g-600">
                <CheckCircle className="w-8 h-8 opacity-30" />
                <p className="text-sm">Nenhuma OS finalizada registrada</p>
              </div>
            ) : filteredFin.length === 0 ? (
              <div className="flex items-center justify-center h-24 gap-2 text-g-600 text-sm">
                <Search className="w-4 h-4" /> Nenhum resultado para "{filterFin}"
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[960px]">
                  <thead className="bg-g-850 border-b border-g-800">
                    <tr>
                      <SortableHeader label="Placa"      col="placa"        sortState={sortFin} onSort={sortFinBy} />
                      <SortableHeader label="Modelo"     col="modelo"       sortState={sortFin} onSort={sortFinBy} />
                      <SortableHeader label="Nº OS"      col="id_ord_serv"  sortState={sortFin} onSort={sortFinBy} />
                      <SortableHeader label="Fornecedor" col="fornecedor"   sortState={sortFin} onSort={sortFinBy} />
                      <SortableHeader label="Sistema / Serviço" col="sistema" sortState={sortFin} onSort={sortFinBy} />
                      <SortableHeader label="Total OS"   col="total_os"     sortState={sortFin} onSort={sortFinBy} className="text-right" />
                      <th className="th">Parcelas</th>
                      <SortableHeader label="Execução"   col="data_execucao" sortState={sortFin} onSort={sortFinBy} />
                      <th className="th">Dias</th>
                      <th className="th">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredFin.map(m => {
                      const dias = m.data_execucao && m.data_entrada ? diasParados(m.data_entrada, m.data_execucao) : null
                      return (
                        <tr key={m.id} className="table-row">
                          <td className="td td-left font-mono font-bold text-g-200">{m.placa}</td>
                          <td className="td td-left text-g-500">{m.modelo || '—'}</td>
                          <td className="td td-left font-mono text-xs text-g-400">{m.id_ord_serv || '—'}</td>
                          <td className="td td-left text-g-500">{m.fornecedor || '—'}</td>
                          <td className="td td-left">
                            <p className="text-g-400 text-xs">{m.sistema || '—'}</p>
                            <p className="text-g-600 text-xs truncate max-w-[160px]">{m.servico || '—'}</p>
                          </td>
                          <td className="td font-mono font-semibold text-g-300 tabular-nums">
                            {m.total_os ? brl(m.total_os) : '—'}
                          </td>
                          <td className="td text-xs text-g-500 tabular-nums">
                            {m.parcelas?.length || 0}x
                            {m.parcelas?.length > 0 && (
                              <span className="block text-g-700">
                                {m.parcelas.filter(p => p.status_pagamento === 'Pago').length}/{m.parcelas.length} pagas
                              </span>
                            )}
                          </td>
                          <td className="td td-left text-xs text-g-500 tabular-nums">{dateBR(m.data_execucao)}</td>
                          <td className="td tabular-nums text-xs text-g-500">
                            {dias !== null ? dias : '—'}
                          </td>
                          <td className="td">
                            <div className="flex items-center justify-end">
                              <button
                                onClick={() => setModalEditFin(m)}
                                title="Editar OS finalizada"
                                className="p-1.5 text-g-600 hover:text-g-100 hover:bg-g-850 rounded-lg transition-colors"
                              >
                                <Pencil className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {/* Modal confirmação exclusão */}
      {confirmDel && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-g-900 border border-g-800 rounded-2xl shadow-xl p-6 max-w-sm w-full mx-4 animate-fade-up">
            <p className="text-g-200 font-semibold mb-2">Excluir OS?</p>
            <p className="text-g-600 text-sm mb-5">Esta ação não pode ser desfeita.</p>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setConfirmDel(null)} className="px-4 py-2 rounded-lg border border-g-800 text-g-500 text-sm hover:bg-g-850">Cancelar</button>
              <button onClick={() => handleDelete(confirmDel)} className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700">Excluir</button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {modalAbrir && (
        <AbrirManutencaoModal onClose={() => setModalAbrir(false)} onSaved={handleSaved} />
      )}
      {modalFin && (
        <FinalizarManutencaoModal manutencao={modalFin} suggestedOsNumber={nextOsNumber(finalizadas)} onClose={() => setModalFin(null)} onSaved={handleSaved} />
      )}
      {modalEdit && (
        <AbrirManutencaoModal manutencao={modalEdit} onClose={() => setModalEdit(null)} onSaved={handleSaved} />
      )}
      {modalInsert && (
        <FinalizarManutencaoModal manutencao={null} onClose={() => setModalInsert(false)} onSaved={handleSaved} />
      )}
      {modalEditFin && (
        <FinalizarManutencaoModal editData={modalEditFin} onClose={() => setModalEditFin(null)} onSaved={handleSaved} />
      )}
    </div>
  )
}

// ════════════════════════════════════════════════════════════════════
// ABA ANÁLISE — gráficos e KPIs (conteúdo original)
// ════════════════════════════════════════════════════════════════════
function AnaliseTab({ year, vehicles }) {
  const [data,        setData]        = useState(null)
  const [loading,     setLoading]     = useState(true)
  const [placa,       setPlaca]       = useState('')
  const [input,       setInput]       = useState('')
  const [upcomingOpen, setUpcomingOpen] = useState(true)

  const placas = useMemo(() =>
    [...new Set(vehicles.map(v => v.placa))].sort(), [vehicles]
  )

  const load = (yr, p) => {
    setLoading(true)
    getMaintenanceAnalysis(yr, p || undefined)
      .then(setData)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(year, placa) }, [year, placa])

  const handleSearch = () => setPlaca(input.trim().toUpperCase())
  const clearFilter  = () => { setPlaca(''); setInput('') }
  const s = data?.summary

  return (
    <div className="flex flex-col gap-8">
      {/* Filtro de placa */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-g-600" />
          <input
            list="placa-list"
            placeholder="Filtrar por placa…"
            value={input}
            onChange={e => setInput(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            className="pl-9 pr-10 py-2 bg-g-900 border border-g-800 rounded-lg text-g-400 text-sm placeholder-g-700 focus:outline-none focus:border-g-100 transition-colors w-52 font-mono"
          />
          <datalist id="placa-list">
            {placas.map(p => <option key={p} value={p} />)}
          </datalist>
          {(input || placa) && (
            <button onClick={clearFilter} className="absolute right-2.5 top-1/2 -translate-y-1/2">
              <X className="w-3.5 h-3.5 text-g-600 hover:text-g-400" />
            </button>
          )}
        </div>
        <button
          onClick={handleSearch}
          className="px-4 py-2 bg-g-850 hover:bg-g-800 border border-g-800 rounded-lg text-g-400 text-sm transition-colors"
        >
          Filtrar
        </button>
        {placa && (
          <span className="flex items-center gap-1.5 px-3 py-1.5 bg-g-850 border border-g-100/20 rounded-full text-g-100 text-xs font-mono">
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
          {/* Custo Mensal — primeiro destaque */}
          {data.monthly?.length > 0 && (
            <Section title="Custo Mensal" icon={DollarSign}>
              <ChartCard title="Custo Mensal de Manutenção" subtitle="Valor total das OS finalizadas por mês">
                <MonthlyBarChart data={data.monthly} />
              </ChartCard>
            </Section>
          )}

          <Section title="Resumo de Manutenção" icon={Wrench}>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <KPICard icon={Hash}       label="Ordens de Serviço" rawValue={s.total_os}    formatter={num}      sub="OS únicas no período" delay={0} />
              <KPICard icon={DollarSign} label="Custo Total"        rawValue={s.total_cost}  formatter={brlShort} sub="Soma todas as OS"       delay={55} />
              <KPICard icon={Activity}   label="Custo Médio / OS"   rawValue={s.avg_per_os}  formatter={brlShort} sub="Média por ordem"         delay={110} />
              <KPICard icon={Award}      label="Principal Fornecedor"
                value={s.top_fornecedor?.length > 14 ? s.top_fornecedor.slice(0,13)+'…' : s.top_fornecedor}
                sub={data.by_fornecedor?.[0] ? brl(data.by_fornecedor[0].total)+' no período' : '—'}
                accent delay={165}
              />
            </div>
          </Section>

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

          {data.by_servico?.length > 0 && (
            <Section title="Serviços Mais Executados" icon={Wrench}>
              <ChartCard title="Top Serviços por Custo" subtitle="Tipos de serviço e valor total acumulado">
                <ServicosChart data={data.by_servico} />
              </ChartCard>
            </Section>
          )}

          <Section title="Tendência e Projeção" icon={TrendingUp}>
            <ChartCard title="Histórico Mensal + Projeção Linear"
              subtitle="Barras = realizado · Linha tracejada = projeção com intervalo de confiança (±1σ)">
              <TrendProjectionChart monthly={data.monthly} projection={data.projection} />
            </ChartCard>
            {data.projection?.length > 0 && (
              <div className="grid grid-cols-4 gap-3 mt-3">
                {data.projection.map((p, i) => (
                  <div key={i} className="card p-3 stagger-child" style={{'--i': i + 1}}>
                    <p className="text-g-600 text-xs uppercase tracking-wider mb-1">Projeção M+{i+1}</p>
                    <p className="text-g-100 font-bold font-mono tabular-nums text-lg">{brlShort(p.projected)}</p>
                    <p className="text-g-700 text-xs mt-0.5">{brlShort(p.low)} – {brlShort(p.high)}</p>
                  </div>
                ))}
              </div>
            )}
          </Section>

          {data.upcoming?.length > 0 && (
            <Section title="Manutenções Programadas" icon={Calendar}>
              <div className="card overflow-hidden">
                <button
                  className="w-full flex items-center justify-between px-4 py-3 border-b border-g-800 hover:bg-g-850 transition-colors"
                  onClick={() => setUpcomingOpen(v => !v)}
                >
                  <span className="text-g-500 text-xs font-semibold uppercase tracking-wider">
                    {data.upcoming.length} pendências identificadas
                  </span>
                  {upcomingOpen ? <ChevronUp className="w-4 h-4 text-g-600" /> : <ChevronDown className="w-4 h-4 text-g-600" />}
                </button>
                {upcomingOpen && (
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[640px]">
                      <thead className="bg-g-850">
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
                          const kmAlert   = u.prox_km && u.km_atual && u.prox_km - u.km_atual < 5000
                          const dateAlert = u.prox_data && new Date(u.prox_data) <= new Date(Date.now() + 30*86400000)
                          return (
                            <tr key={i} className={`border-b border-g-800 hover:bg-g-850 transition-colors ${kmAlert || dateAlert ? 'bg-amber-50/50' : ''}`}>
                              <td className="td td-left text-xs font-mono font-bold text-g-200">{u.placa}</td>
                              <td className="td td-left text-xs text-g-500">{u.modelo?.length>18?u.modelo.slice(0,17)+'…':u.modelo}</td>
                              <td className="td td-left text-xs text-g-400">{u.servico?.length>22?u.servico.slice(0,21)+'…':u.servico}</td>
                              <td className="td td-left text-xs text-g-500">{u.sistema}</td>
                              <td className="td text-xs tabular-nums text-g-500">{u.km_atual?num(u.km_atual)+' km':'—'}</td>
                              <td className={`td text-xs tabular-nums font-semibold ${kmAlert?'text-amber-600':'text-g-400'}`}>{u.prox_km?num(u.prox_km)+' km':'—'}</td>
                              <td className={`td text-xs tabular-nums ${dateAlert?'text-amber-600 font-semibold':'text-g-400'}`}>
                                {dateBR(u.prox_data)}
                                {(kmAlert||dateAlert)&&<AlertTriangle className="inline w-3 h-3 ml-1 text-amber-500"/>}
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

// ════════════════════════════════════════════════════════════════════
// PÁGINA PRINCIPAL
// ════════════════════════════════════════════════════════════════════
export default function MaintenancePage({ year, vehicles = [] }) {
  const [tab, setTab] = useState('gestao')

  return (
    <div className="flex flex-col gap-6">
      {/* Tabs principais */}
      <div className="flex gap-1 bg-g-850 border border-g-800 rounded-xl p-1 w-fit">
        {[
          { key: 'gestao',  label: 'Gestão de OS',    icon: Wrench },
          { key: 'analise', label: 'Análise',         icon: BarChart2 },
        ].map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              tab === key
                ? 'bg-white shadow-sm text-g-200 border border-g-800'
                : 'text-g-600 hover:text-g-400'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {tab === 'gestao'  && <GestaoTab />}
      {tab === 'analise' && <AnaliseTab year={year} vehicles={vehicles} />}
    </div>
  )
}
