import { useEffect, useState, useMemo, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { getMaintenanceAnalysis, dbListManutencoes, dbAtualizarManutencao, dbDeletarManutencao, dbAtualizarParcela, dbListParcelas, dbListOs, dbAtualizarOs, dbDeletarOs, dbCriarParcelaNf } from '../utils/api'
import { brl, brlShort, num, dateBR } from '../utils/format'
import KPICard from '../components/KPICard'
import AbrirManutencaoModal   from '../components/AbrirManutencaoModal'
import FinalizarManutencaoModal from '../components/FinalizarManutencaoModal'
import AbrirOsModal     from '../components/AbrirOsModal'
import FinalizarOsModal from '../components/FinalizarOsModal'
import {
  FornecedorChart, SistemaTreemap, TipoPie,
  ImplementoRadial, TrendProjectionChart, ServicosChart,
  MonthlyBarChart,
} from '../components/charts/MaintenanceCharts'
import {
  Wrench, DollarSign, Hash, Award, Search, X,
  Calendar, AlertTriangle, ChevronDown, ChevronUp,
  Activity, Loader2, TrendingUp, Plus, CheckCircle,
  Truck, Clock, AlertCircle, Trash2, BarChart2, Pencil, Bell,
  CreditCard, CalendarClock, Ban, RotateCcw,
} from 'lucide-react'

// ── Empresas ─────────────────────────────────────────────────────────
const SIGLA_EMPRESA = { '1': 'TKJ', '2': 'FINITA', '3': 'LANDKRAFT' }
function empresaSigla(empresa, empresaNome) {
  const cod = String(parseInt(parseFloat(empresa)))
  if (SIGLA_EMPRESA[cod]) return SIGLA_EMPRESA[cod]
  const n = empresaNome || ''
  if (n.includes('TKJ')) return 'TKJ'
  if (/finita/i.test(n)) return 'FINITA'
  if (/landkraft/i.test(n)) return 'LANDKRAFT'
  return n || '—'
}

// ── Date utils ───────────────────────────────────────────────────────
function parseLocalDate(s) {
  if (!s) return null
  const [y, m, d] = String(s).slice(0, 10).split('-').map(Number)
  const dt = new Date(y, m - 1, d)
  dt.setHours(0, 0, 0, 0)
  return dt
}

// ── Status helpers ────────────────────────────────────────────────────
const STATUS_LABEL = {
  aberta:                   { label: 'Aberta',              color: 'bg-blue-50 text-blue-700 border-blue-200' },
  em_andamento:             { label: 'Em andamento',         color: 'bg-amber-50 text-amber-700 border-amber-200' },
  aguardando_peca:          { label: 'Aguardando peça',      color: 'bg-orange-50 text-orange-700 border-orange-200' },
  executado_aguardando_nf:  { label: 'Aguardando NF',        color: 'bg-purple-50 text-purple-700 border-purple-200' },
  pendente:                 { label: 'Pendente',             color: 'bg-slate-100 text-slate-600 border-slate-300' },
  finalizada:               { label: 'Finalizada',           color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
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

// ── Modal de detalhes (somente leitura) ──────────────────────────────
function Field({ label, value, mono = false, full = false }) {
  return (
    <div className={full ? 'col-span-2' : ''}>
      <p className="text-g-700 text-xs mb-0.5">{label}</p>
      <p className={`text-g-300 text-sm ${mono ? 'font-mono' : ''} break-words`}>{value || '—'}</p>
    </div>
  )
}

function DetalhesManutencaoModal({ manutencao: m, onClose, onDeleted }) {
  const isFinalizada = m.status_manutencao === 'finalizada'
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleting,      setDeleting]      = useState(false)

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await dbDeletarManutencao(m.id)
      onDeleted()
    } catch {
      setDeleting(false)
      setConfirmDelete(false)
    }
  }
  const dias = m.data_entrada
    ? diasParados(m.data_entrada, isFinalizada ? m.data_execucao : null)
    : null
  const hasPneu    = m.posicao_pneu || m.espec_pneu || m.marca_pneu
  const hasParcelas = m.parcelas?.length > 0

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-g-900 border border-g-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col animate-fade-up"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-g-800">
          <div className="flex items-center gap-3">
            <div className="p-1.5 bg-g-850 border border-g-800 rounded-lg">
              <Wrench className="w-4 h-4 text-g-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-g-100 font-bold font-mono text-base">{m.placa}</span>
                <StatusBadge status={m.status_manutencao} />
              </div>
              <p className="text-g-600 text-xs mt-0.5">{m.modelo || '—'}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-g-600 hover:text-g-300 hover:bg-g-850 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto px-5 py-5 flex flex-col gap-6">

          {/* Identificação */}
          <div>
            <p className="text-g-600 text-xs font-semibold uppercase tracking-wider mb-3">Identificação</p>
            <div className="grid grid-cols-2 gap-x-6 gap-y-3">
              <Field label="Fornecedor / Oficina" value={m.fornecedor} />
              <Field label="Tipo de Manutenção"   value={m.tipo_manutencao} />
              <Field label="Sistema"              value={m.sistema} />
              <Field label="Serviço"              value={m.servico} />
              <Field label="Data de Entrada"      value={dateBR(m.data_entrada)} />
              <Field label="KM"                   value={m.km ? `${num(m.km)} km` : null} />
              <Field label="Responsável Técnico"  value={m.responsavel_tec} />
              <div>
                <p className="text-g-700 text-xs mb-0.5">Veículo Indisponível</p>
                <p className={`text-sm font-medium ${m.indisponivel ? 'text-amber-500' : 'text-g-500'}`}>
                  {m.indisponivel ? 'Sim' : 'Não'}
                </p>
              </div>
              {dias !== null && (
                <div>
                  <p className="text-g-700 text-xs mb-0.5">Dias Parados</p>
                  <p className={`text-sm font-semibold ${dias > 30 ? 'text-red-400' : dias > 7 ? 'text-amber-400' : 'text-g-300'}`}>
                    {dias} dias
                  </p>
                </div>
              )}
              {m.descricao  && <Field label="Descrição"   value={m.descricao}   full />}
              {m.observacoes && <Field label="Observações" value={m.observacoes} full />}
            </div>
          </div>

          {/* OS Finalizada */}
          {isFinalizada && (
            <div className="border-t border-g-800 pt-5">
              <p className="text-g-600 text-xs font-semibold uppercase tracking-wider mb-3">Ordem de Serviço</p>
              <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                <Field label="Nº da OS"          value={m.id_ord_serv}              mono />
                <Field label="Data de Execução"  value={dateBR(m.data_execucao)} />
                <Field label="Valor Total"        value={m.total_os ? brl(m.total_os) : null} mono />
                <Field label="Categoria"          value={m.categoria} />
                {m.qtd_itens && <Field label="Qtd. Itens" value={String(m.qtd_itens)} />}
                {m.prox_km   && <Field label="Próx. KM"   value={`${num(m.prox_km)} km`} />}
                {m.prox_data && <Field label="Próx. Data" value={dateBR(m.prox_data)} />}
              </div>
            </div>
          )}

          {/* Pneu */}
          {hasPneu && (
            <div className="border-t border-g-800 pt-5">
              <p className="text-g-600 text-xs font-semibold uppercase tracking-wider mb-3">Dados de Pneu</p>
              <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                <Field label="Posição"       value={m.posicao_pneu} />
                <Field label="Qtd."          value={m.qtd_pneu ? String(m.qtd_pneu) : null} />
                <Field label="Especificação" value={m.espec_pneu} />
                <Field label="Marca"         value={m.marca_pneu} />
                <Field label="Manejo"        value={m.manejo_pneu} />
              </div>
            </div>
          )}

          {/* Parcelas */}
          {hasParcelas && (
            <div className="border-t border-g-800 pt-5">
              <p className="text-g-600 text-xs font-semibold uppercase tracking-wider mb-3">
                Parcelas de Pagamento
                <span className="ml-2 text-g-700 normal-case font-normal">
                  ({m.parcelas.filter(p => p.status_pagamento === 'Pago').length}/{m.parcelas.length} pagas)
                </span>
              </p>
              <div className="flex flex-col gap-2">
                {m.parcelas.map((p, i) => (
                  <div key={i} className="bg-g-850 border border-g-800 rounded-xl px-4 py-2.5 flex items-center justify-between gap-4 text-xs">
                    <div className="flex items-center gap-3">
                      {p.parcela_atual && <span className="text-g-600 font-mono text-xs">Parcela {p.parcela_atual}/{p.parcela_total}</span>}
                      {p.nota && <span className="text-g-500">{p.nota}</span>}
                      {p.data_vencimento && <span className="text-g-600">Venc. {dateBR(p.data_vencimento)}</span>}
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-g-400">{p.forma_pgto}</span>
                      <span className="font-mono font-semibold text-g-200">{brl(p.valor_parcela)}</span>
                      <span className={`px-1.5 py-0.5 rounded-full text-xs font-medium border ${p.status_pagamento === 'Pago' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>
                        {p.status_pagamento}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-g-800 flex items-center justify-between">
          <div>
            {isFinalizada && !confirmDelete && (
              <button
                onClick={() => setConfirmDelete(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-red-500 text-xs hover:bg-red-500/10 border border-transparent hover:border-red-500/20 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" /> Excluir OS
              </button>
            )}
            {confirmDelete && (
              <div className="flex items-center gap-2">
                <span className="text-red-500 text-xs">Confirmar exclusão permanente?</span>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="px-3 py-1.5 rounded-lg bg-red-600 text-white text-xs font-medium hover:bg-red-500 disabled:opacity-50 transition-colors"
                >
                  {deleting ? 'Excluindo…' : 'Confirmar'}
                </button>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="px-3 py-1.5 rounded-lg border border-g-800 text-g-500 text-xs hover:bg-g-850 transition-colors"
                >
                  Cancelar
                </button>
              </div>
            )}
          </div>
          <button onClick={onClose} className="px-4 py-2 rounded-lg border border-g-800 text-g-500 text-sm hover:bg-g-850 transition-colors">
            Fechar
          </button>
        </div>
      </div>
    </div>,
    document.body
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
  const [modalDetalhe, setModalDetalhe] = useState(null)
  const [confirmDel,   setConfirmDel]   = useState(null)
  const [filterAberta, setFilterAberta] = useState('')
  const [filterFin,    setFilterFin]    = useState('')
  const [sortAberta,   setSortAberta]   = useState({ col: null, dir: 'asc' })
  const [sortFin,      setSortFin]      = useState({ col: null, dir: 'asc' })

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const all = await dbListOs()
      setAbertas(all.filter(o => o.status_os !== 'finalizada'))
      setFinalizadas(all.filter(o => o.status_os === 'finalizada'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleSaved = () => {
    setModalAbrir(false)
    setModalFin(null)
    setModalEdit(null)
    setModalDetalhe(null)
    load()
  }

  const handleStatusChange = async (os, newStatus) => {
    await dbAtualizarOs(os.id, { status_os: newStatus })
    load()
  }

  const handleDelete = async (id) => {
    await dbDeletarOs(id)
    setConfirmDel(null)
    load()
  }

  const sortAbertaBy = col => setSortAberta(s => s.col !== col ? { col, dir: 'asc' } : s.dir === 'asc' ? { col, dir: 'desc' } : { col: null, dir: 'asc' })
  const sortFinBy    = col => setSortFin(s => s.col !== col ? { col, dir: 'asc' } : s.dir === 'asc' ? { col, dir: 'desc' } : { col: null, dir: 'asc' })

  const emAndamento  = abertas.filter(o => o.status_os === 'em_andamento')
  const aguardando   = abertas.filter(o => o.status_os === 'aguardando_peca')
  const agNf         = abertas.filter(o => o.status_os === 'executado_aguardando_nf')
  const todasAbertas = abertas

  // flatten first item for filter/sort display
  const withDisplay = list => list.map(o => ({
    ...o,
    _sistema: o.itens?.[0]?.sistema || '',
    _servico: o.itens?.[0]?.servico || '',
    _totalNfs: (o.notas_fiscais || []).reduce((s, nf) => s + (nf.valor_total_nf || 0), 0),
    _allParcelas: (o.notas_fiscais || []).flatMap(nf => nf.parcelas || []),
  }))

  const filteredAbertas = useMemo(() =>
    applyFilterSort(withDisplay(todasAbertas), filterAberta, sortAberta, ['placa', 'fornecedor', 'status_os', 'modelo', '_sistema', '_servico']),
    [todasAbertas, filterAberta, sortAberta]
  )

  const filteredFin = useMemo(() =>
    applyFilterSort(withDisplay(finalizadas), filterFin, sortFin, ['placa', 'fornecedor', 'modelo', '_sistema', '_servico', 'numero_os']),
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
          <div className="p-2 bg-purple-50 border border-purple-200 rounded-lg">
            <CreditCard className="w-4 h-4 text-purple-600" />
          </div>
          <div>
            <p className="text-g-600 text-xs uppercase tracking-wider">Aguardando NF</p>
            <p className="text-g-200 font-bold text-xl">{agNf.length}</p>
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
                <p className="text-sm">Nenhuma OS em andamento</p>
                <button onClick={() => setModalAbrir(true)} className="text-g-100 text-xs font-medium hover:underline">
                  Abrir nova OS
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
                      <SortableHeader label="Placa"     col="placa"      sortState={sortAberta} onSort={sortAbertaBy} />
                      <SortableHeader label="Modelo"    col="modelo"     sortState={sortAberta} onSort={sortAbertaBy} />
                      <SortableHeader label="Fornecedor" col="fornecedor" sortState={sortAberta} onSort={sortAbertaBy} />
                      <SortableHeader label="Sistema / Serviço" col="_sistema" sortState={sortAberta} onSort={sortAbertaBy} />
                      <SortableHeader label="Status"    col="status_os"  sortState={sortAberta} onSort={sortAbertaBy} />
                      <SortableHeader label="Entrada"   col="data_entrada" sortState={sortAberta} onSort={sortAbertaBy} />
                      <th className="th">Dias</th>
                      <th className="th">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAbertas.map(o => {
                      const dias = o.indisponivel && o.data_entrada ? diasParados(o.data_entrada) : null
                      return (
                        <tr key={o.id} className="table-row cursor-pointer" onClick={() => setModalDetalhe(o)}>
                          <td className="td td-left font-mono font-bold text-g-200">{o.placa}</td>
                          <td className="td td-left text-g-500">{o.modelo || '—'}</td>
                          <td className="td td-left text-g-500">{o.fornecedor || '—'}</td>
                          <td className="td td-left">
                            <p className="text-g-400 text-xs">{o._sistema || '—'}</p>
                            <p className="text-g-600 text-xs truncate max-w-[180px]">{o._servico || '—'}</p>
                          </td>
                          <td className="td td-left">
                            <StatusBadge status={o.status_os} />
                          </td>
                          <td className="td td-left text-xs text-g-500 tabular-nums">
                            {dateBR(o.data_entrada)}
                          </td>
                          <td className="td tabular-nums text-xs">
                            {dias !== null
                              ? <span className={dias > 30 ? 'text-red-500 font-semibold' : dias > 7 ? 'text-amber-500 font-medium' : 'text-g-500'}>{dias}</span>
                              : <span className="text-g-700">—</span>
                            }
                          </td>
                          <td className="td" onClick={e => e.stopPropagation()}>
                            <div className="flex items-center justify-end gap-1">
                              {o.status_os === 'em_andamento' && (
                                <button
                                  onClick={() => handleStatusChange(o, 'aguardando_peca')}
                                  title="Marcar como aguardando peça"
                                  className="px-2 py-1 text-xs text-orange-600 border border-orange-200 rounded-lg hover:bg-orange-50 transition-colors"
                                >
                                  Ag. peça
                                </button>
                              )}
                              {o.status_os === 'aguardando_peca' && (
                                <button
                                  onClick={() => handleStatusChange(o, 'em_andamento')}
                                  title="Retomar andamento"
                                  className="px-2 py-1 text-xs text-amber-600 border border-amber-200 rounded-lg hover:bg-amber-50 transition-colors"
                                >
                                  Retomar
                                </button>
                              )}
                              {/* Editar */}
                              <button
                                onClick={() => setModalEdit(o)}
                                title="Editar OS"
                                className="p-1.5 text-g-600 hover:text-g-100 hover:bg-g-850 rounded-lg transition-colors"
                              >
                                <Pencil className="w-3.5 h-3.5" />
                              </button>
                              {/* Finalizar */}
                              <button
                                onClick={() => setModalFin(o)}
                                className="px-2 py-1 text-xs text-g-100 border border-emerald-200 rounded-lg hover:bg-emerald-50 transition-colors"
                              >
                                Finalizar
                              </button>
                              {/* Excluir */}
                              <button
                                onClick={() => setConfirmDel(o.id)}
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
                      <SortableHeader label="Placa"      col="placa"       sortState={sortFin} onSort={sortFinBy} />
                      <SortableHeader label="Modelo"     col="modelo"      sortState={sortFin} onSort={sortFinBy} />
                      <SortableHeader label="Nº OS"      col="numero_os"   sortState={sortFin} onSort={sortFinBy} />
                      <SortableHeader label="Fornecedor" col="fornecedor"  sortState={sortFin} onSort={sortFinBy} />
                      <SortableHeader label="Sistema / Serviço" col="_sistema" sortState={sortFin} onSort={sortFinBy} />
                      <SortableHeader label="Total NFs"  col="_totalNfs"   sortState={sortFin} onSort={sortFinBy} className="text-right" />
                      <th className="th">Parcelas</th>
                      <SortableHeader label="Execução"   col="data_execucao" sortState={sortFin} onSort={sortFinBy} />
                      <th className="th">Dias</th>
                      <th className="th">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredFin.map(o => {
                      const dias = o.data_execucao && o.data_entrada ? diasParados(o.data_entrada, o.data_execucao) : null
                      const pagas = o._allParcelas.filter(p => p.status_pagamento === 'Pago').length
                      return (
                        <tr key={o.id} className="table-row cursor-pointer" onClick={() => setModalDetalhe(o)}>
                          <td className="td td-left font-mono font-bold text-g-200">{o.placa}</td>
                          <td className="td td-left text-g-500">{o.modelo || '—'}</td>
                          <td className="td td-left font-mono text-xs text-g-400">{o.numero_os || '—'}</td>
                          <td className="td td-left text-g-500">{o.fornecedor || '—'}</td>
                          <td className="td td-left">
                            <p className="text-g-400 text-xs">{o._sistema || '—'}</p>
                            <p className="text-g-600 text-xs truncate max-w-[160px]">{o._servico || '—'}</p>
                          </td>
                          <td className="td font-mono font-semibold text-g-300 tabular-nums">
                            {o._totalNfs ? brl(o._totalNfs) : '—'}
                          </td>
                          <td className="td text-xs text-g-500 tabular-nums">
                            {o._allParcelas.length > 0
                              ? <><span>{o._allParcelas.length}x</span><span className="block text-g-700">{pagas}/{o._allParcelas.length} pagas</span></>
                              : '—'
                            }
                          </td>
                          <td className="td td-left text-xs text-g-500 tabular-nums">{dateBR(o.data_execucao)}</td>
                          <td className="td tabular-nums text-xs text-g-500">
                            {dias !== null ? dias : '—'}
                          </td>
                          <td className="td" onClick={e => e.stopPropagation()}>
                            <div className="flex items-center justify-end gap-1">
                              <button
                                onClick={() => setModalEdit(o)}
                                title="Editar OS"
                                className="p-1.5 text-g-600 hover:text-g-100 hover:bg-g-850 rounded-lg transition-colors"
                              >
                                <Pencil className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => setConfirmDel(o.id)}
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
        <AbrirOsModal onClose={() => setModalAbrir(false)} onSaved={handleSaved} />
      )}
      {modalFin && (
        <FinalizarOsModal os={modalFin} onClose={() => setModalFin(null)} onSaved={handleSaved} />
      )}
      {modalEdit && (
        <AbrirOsModal os={modalEdit} onClose={() => setModalEdit(null)} onSaved={handleSaved} />
      )}
      {modalDetalhe && (
        <DetalhesManutencaoModal manutencao={modalDetalhe} onClose={() => setModalDetalhe(null)} onDeleted={() => { setModalDetalhe(null); load() }} />
      )}
    </div>
  )
}

// ════════════════════════════════════════════════════════════════════
// ABA FINANCEIRO — helpers
// ════════════════════════════════════════════════════════════════════

function statusFinanceiro(p) {
  if (p.status_pagamento === 'Pago') return 'pago'
  if (p.prorrogada) return 'prorrogada'
  const hoje = new Date(); hoje.setHours(0, 0, 0, 0)
  if (!p.data_vencimento) return 'pendente'
  const venc = parseLocalDate(p.data_vencimento)
  if (venc < hoje) return 'vencida'
  if (venc.getTime() === hoje.getTime()) return 'vence_hoje'
  return 'pendente'
}

function calcValorComEncargos(valorBase, multaPct, jurosDiarioPct, dataVenc) {
  if (!valorBase) return valorBase
  const hoje = new Date(); hoje.setHours(0, 0, 0, 0)
  const venc = parseLocalDate(dataVenc)
  if (!venc) return valorBase
  const diasAtraso = Math.max(0, Math.round((hoje - venc) / 86400000))
  const multa = valorBase * ((parseFloat(multaPct) || 0) / 100)
  const juros = valorBase * ((parseFloat(jurosDiarioPct) || 0) / 100) * diasAtraso
  return valorBase + multa + juros
}

function calcDataCartorio(dataVenc, diasCartorio) {
  if (!dataVenc || !diasCartorio) return null
  const d = parseLocalDate(dataVenc)
  if (!d) return null
  d.setDate(d.getDate() + parseInt(diasCartorio))
  return d.toISOString().slice(0, 10)
}

const FIN_STATUS = {
  pago:        { label: 'Pago',         color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  pendente:    { label: 'Pendente',     color: 'bg-blue-50 text-blue-700 border-blue-200' },
  vence_hoje:  { label: 'Vence hoje',   color: 'bg-orange-50 text-orange-700 border-orange-200' },
  vencida:     { label: 'Vencida',      color: 'bg-red-50 text-red-700 border-red-200' },
  prorrogada:  { label: 'Prorrogada',   color: 'bg-purple-50 text-purple-700 border-purple-200' },
}

function FinBadge({ status }) {
  const s = FIN_STATUS[status] || FIN_STATUS.pendente
  return <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium border ${s.color}`}>{s.label}</span>
}

// ── Modal: alerta contas do dia ──────────────────────────────────────
function AlertContasDiaModal({ parcelas, onCiente, onLembrarDepois }) {
  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-g-900 border border-orange-500/30 rounded-2xl shadow-2xl w-full max-w-lg animate-fade-up">
        <div className="flex items-center gap-3 px-5 py-4 border-b border-g-800">
          <div className="p-1.5 bg-orange-50 border border-orange-200 rounded-lg">
            <Bell className="w-4 h-4 text-orange-600" />
          </div>
          <div>
            <h2 className="text-g-200 font-semibold text-sm">Contas com vencimento hoje</h2>
            <p className="text-g-600 text-xs">{parcelas.length} parcela{parcelas.length !== 1 ? 's' : ''} pendente{parcelas.length !== 1 ? 's' : ''}</p>
          </div>
        </div>
        <div className="px-5 py-4 flex flex-col gap-2 max-h-72 overflow-y-auto">
          {parcelas.map(p => (
            <div key={p.id} className="bg-g-850 border border-orange-500/20 rounded-xl px-4 py-2.5 flex items-center justify-between text-xs">
              <div className="flex items-center gap-3">
                <span className="font-mono font-bold text-g-200">{p.placa}</span>
                {p.id_ord_serv && <span className="text-g-600 font-mono">{p.id_ord_serv}</span>}
                {p.fornecedor && <span className="text-g-500 truncate max-w-[140px]">{p.fornecedor}</span>}
              </div>
              <span className="font-mono font-semibold text-orange-400">{brl(p.valor_parcela)}</span>
            </div>
          ))}
        </div>
        <div className="px-5 py-4 border-t border-g-800 flex justify-end gap-2">
          <button
            onClick={onLembrarDepois}
            className="px-4 py-2 rounded-lg border border-g-800 text-g-500 text-sm hover:bg-g-850 transition-colors"
          >
            Lembrar mais tarde
          </button>
          <button
            onClick={onCiente}
            className="px-5 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-500 transition-colors"
          >
            Ciente
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}

// ── Modal: prorrogar parcela ─────────────────────────────────────────
function ProrrogarParcelaModal({ parcela: p, onClose, onSaved }) {
  const FIELD = 'w-full px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm placeholder-g-700 focus:outline-none focus:border-g-100 transition-colors'
  const LABEL = 'text-g-600 text-xs font-medium mb-1 block'

  const modoInicial = p.prorrogada
    ? (p.dias_cartorio ? 'cartorio' : p.isento_encargos ? 'prorrogada_isenta' : 'prorrogada_encargos')
    : null

  const [modo,   setModo]   = useState(modoInicial)
  const [saving, setSaving] = useState(false)
  const [error,  setError]  = useState(null)
  const [form,   setForm]   = useState({
    nova_data:               p.prorrogada ? (p.data_vencimento || '') : '',
    tipo_pgto:               p.tipo_pgto_prorrogacao || 'boleto',
    chave_pix:               p.chave_pix || '',
    multa_pct:               p.multa_pct != null ? String(p.multa_pct) : '',
    juros_diario_pct:        p.juros_diario_pct != null ? String(p.juros_diario_pct) : '',
    data_prevista_pagamento: p.data_prevista_pagamento || '',
    dias_cartorio:           p.dias_cartorio != null ? String(p.dias_cartorio) : '',
  })
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const valorBase = parseFloat(p.valor_parcela) || 0
  const dataVencRef = p.data_vencimento_original || p.data_vencimento

  const valorEncargos = useMemo(() => {
    if (modo === 'prorrogada_encargos' || modo === 'cartorio') {
      return calcValorComEncargos(valorBase, form.multa_pct, form.juros_diario_pct, dataVencRef)
    }
    return null
  }, [modo, form.multa_pct, form.juros_diario_pct, valorBase, dataVencRef])

  const dataCartorio = useMemo(() =>
    calcDataCartorio(dataVencRef, form.dias_cartorio),
    [dataVencRef, form.dias_cartorio]
  )

  const handleSave = async () => {
    setError(null)
    let payload = {}
    if (modo === 'prorrogada_isenta') {
      if (!form.nova_data) { setError('Informe a nova data de vencimento'); return }
      payload = {
        data_vencimento_original: p.data_vencimento_original || p.data_vencimento,
        data_vencimento: form.nova_data,
        prorrogada: true,
        isento_encargos: true,
        tipo_pgto_prorrogacao: form.tipo_pgto,
        chave_pix: form.tipo_pgto === 'pix' ? form.chave_pix : null,
      }
    } else if (modo === 'prorrogada_encargos') {
      if (!form.nova_data) { setError('Informe a nova data de vencimento'); return }
      payload = {
        data_vencimento_original: p.data_vencimento_original || p.data_vencimento,
        data_vencimento: form.nova_data,
        prorrogada: true,
        isento_encargos: false,
        multa_pct: parseFloat(form.multa_pct) || null,
        juros_diario_pct: parseFloat(form.juros_diario_pct) || null,
        data_prevista_pagamento: form.data_prevista_pagamento || null,
        valor_atualizado: valorEncargos,
      }
    } else if (modo === 'cartorio') {
      if (!form.dias_cartorio) { setError('Informe a quantidade de dias'); return }
      payload = {
        dias_cartorio: parseInt(form.dias_cartorio),
        data_prevista_pagamento: dataCartorio,
        multa_pct: parseFloat(form.multa_pct) || null,
        juros_diario_pct: parseFloat(form.juros_diario_pct) || null,
        valor_atualizado: valorEncargos,
      }
    }
    setSaving(true)
    try {
      await dbAtualizarParcela(p.id, payload)
      onSaved()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar')
      setSaving(false)
    }
  }

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in">
      <div className="bg-g-900 border border-g-800 rounded-2xl shadow-2xl w-full max-w-lg animate-fade-up">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-g-800">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 bg-g-850 border border-g-800 rounded-lg">
              <CalendarClock className="w-4 h-4 text-g-400" />
            </div>
            <div>
              <h2 className="text-g-200 font-semibold text-sm">{p.prorrogada ? 'Editar Prorrogação' : 'Prorrogar Parcela'}</h2>
              <p className="text-g-600 text-xs font-mono">{p.placa} · {p.id_ord_serv || '—'} · {brl(p.valor_parcela)}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-g-600 hover:text-g-300 hover:bg-g-850 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="px-5 py-5 flex flex-col gap-5">

          {/* Seleção de modo */}
          {!modo && (
            <div className="flex flex-col gap-3">
              <p className="text-g-500 text-sm font-medium">A parcela será prorrogada?</p>
              <div className="flex flex-col gap-2">
                <button
                  onClick={() => setModo('prorrogada_isenta')}
                  className="flex items-center gap-3 px-4 py-3 bg-g-850 border border-g-800 rounded-xl hover:border-emerald-500/40 hover:bg-emerald-50/5 transition-colors text-left"
                >
                  <CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" />
                  <div>
                    <p className="text-g-300 text-sm font-medium">Sim, isenta de encargos</p>
                    <p className="text-g-600 text-xs">Nova data, sem multa ou juros</p>
                  </div>
                </button>
                <button
                  onClick={() => setModo('prorrogada_encargos')}
                  className="flex items-center gap-3 px-4 py-3 bg-g-850 border border-g-800 rounded-xl hover:border-amber-500/40 hover:bg-amber-50/5 transition-colors text-left"
                >
                  <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
                  <div>
                    <p className="text-g-300 text-sm font-medium">Sim, com encargos</p>
                    <p className="text-g-600 text-xs">Multa e/ou juros serão aplicados</p>
                  </div>
                </button>
                <button
                  onClick={() => setModo('cartorio')}
                  className="flex items-center gap-3 px-4 py-3 bg-g-850 border border-g-800 rounded-xl hover:border-red-500/40 hover:bg-red-50/5 transition-colors text-left"
                >
                  <Ban className="w-4 h-4 text-red-500 shrink-0" />
                  <div>
                    <p className="text-g-300 text-sm font-medium">Não — envio ao cartório</p>
                    <p className="text-g-600 text-xs">Calcular data de protesto</p>
                  </div>
                </button>
              </div>
            </div>
          )}

          {/* Tela: prorrogada isenta */}
          {modo === 'prorrogada_isenta' && (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={LABEL}>Nova data de vencimento *</label>
                  <input type="date" value={form.nova_data} onChange={e => set('nova_data', e.target.value)} className={FIELD} />
                </div>
                <div>
                  <label className={LABEL}>Forma de pagamento</label>
                  <select value={form.tipo_pgto} onChange={e => set('tipo_pgto', e.target.value)} className={FIELD}>
                    <option value="boleto">Boleto atualizado</option>
                    <option value="pix">PIX</option>
                  </select>
                </div>
              </div>
              {form.tipo_pgto === 'pix' && (
                <div>
                  <label className={LABEL}>Chave PIX</label>
                  <input value={form.chave_pix} onChange={e => set('chave_pix', e.target.value)} placeholder="CPF, CNPJ, e-mail, telefone ou aleatória…" className={FIELD} />
                </div>
              )}
            </div>
          )}

          {/* Tela: prorrogada com encargos */}
          {modo === 'prorrogada_encargos' && (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={LABEL}>Nova data de vencimento *</label>
                  <input type="date" value={form.nova_data} onChange={e => set('nova_data', e.target.value)} className={FIELD} />
                </div>
                <div>
                  <label className={LABEL}>Data prevista de pagamento</label>
                  <input type="date" value={form.data_prevista_pagamento} onChange={e => set('data_prevista_pagamento', e.target.value)} className={FIELD} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={LABEL}>Multa (%)</label>
                  <input type="number" step="0.01" placeholder="Ex: 2,00" value={form.multa_pct} onChange={e => set('multa_pct', e.target.value)} className={FIELD} />
                </div>
                <div>
                  <label className={LABEL}>Juros diário (%)</label>
                  <input type="number" step="0.001" placeholder="Ex: 0,033" value={form.juros_diario_pct} onChange={e => set('juros_diario_pct', e.target.value)} className={FIELD} />
                </div>
              </div>
              {valorEncargos !== null && (
                <div className="bg-g-850 border border-g-800 rounded-xl px-4 py-3 text-xs flex flex-col gap-1">
                  <div className="flex justify-between text-g-600"><span>Valor base</span><span className="font-mono">{brl(valorBase)}</span></div>
                  <div className="flex justify-between text-g-600"><span>Multa ({form.multa_pct || 0}%)</span><span className="font-mono">{brl(valorBase * ((parseFloat(form.multa_pct) || 0) / 100))}</span></div>
                  <div className="flex justify-between text-g-600 border-t border-g-800 pt-1 mt-1"><span>Valor atualizado</span><span className="font-mono font-semibold text-amber-400">{brl(valorEncargos)}</span></div>
                </div>
              )}
            </div>
          )}

          {/* Tela: cartório */}
          {modo === 'cartorio' && (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={LABEL}>Dias corridos para envio *</label>
                  <input type="number" placeholder="Ex: 15" value={form.dias_cartorio} onChange={e => set('dias_cartorio', e.target.value)} className={FIELD} />
                </div>
                <div>
                  <label className={LABEL}>Data de envio ao cartório</label>
                  <input
                    value={dataCartorio ? dateBR(dataCartorio) : '—'}
                    disabled
                    className={`${FIELD} bg-g-850 text-g-500 cursor-default opacity-70`}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={LABEL}>Multa (%)</label>
                  <input type="number" step="0.01" placeholder="Ex: 2,00" value={form.multa_pct} onChange={e => set('multa_pct', e.target.value)} className={FIELD} />
                </div>
                <div>
                  <label className={LABEL}>Juros diário (%)</label>
                  <input type="number" step="0.001" placeholder="Ex: 0,033" value={form.juros_diario_pct} onChange={e => set('juros_diario_pct', e.target.value)} className={FIELD} />
                </div>
              </div>
              {valorEncargos !== null && (
                <div className="bg-g-850 border border-g-800 rounded-xl px-4 py-3 text-xs flex flex-col gap-1">
                  <div className="flex justify-between text-g-600"><span>Valor base</span><span className="font-mono">{brl(valorBase)}</span></div>
                  <div className="flex justify-between text-g-600"><span>Encargos acumulados</span><span className="font-mono">{brl(valorEncargos - valorBase)}</span></div>
                  <div className="flex justify-between text-g-600 border-t border-g-800 pt-1 mt-1"><span>Valor com encargos</span><span className="font-mono font-semibold text-red-400">{brl(valorEncargos)}</span></div>
                </div>
              )}
            </div>
          )}

          {error && <p className="text-red-600 text-xs bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-g-800 flex justify-between items-center">
          <div>
            {modo && (
              <button onClick={() => { setModo(null); setError(null) }} className="text-g-600 text-xs hover:text-g-400 transition-colors">
                ← Voltar
              </button>
            )}
          </div>
          <div className="flex gap-2">
            <button onClick={onClose} className="px-4 py-2 rounded-lg border border-g-800 text-g-500 text-sm hover:bg-g-850 transition-colors">
              Cancelar
            </button>
            {modo && (
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-5 py-2 rounded-lg bg-g-100 text-white text-sm font-medium hover:bg-g-50 disabled:opacity-50 transition-colors flex items-center gap-2"
              >
                {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Salvar
              </button>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body
  )
}

// ── Modal: detalhe de parcela ─────────────────────────────────────────
function DetalheParcelaModal({ parcela: p, onClose, onSaved }) {
  const LABEL = 'text-g-700 text-xs mb-0.5'
  const VAL   = 'text-g-300 text-sm break-words'

  const [reemb, setReemb] = useState({
    sera_reembolsado:    p.sera_reembolsado    || false,
    valor_reembolso:     p.valor_reembolso     ?? '',
    qtd_itens_reembolso: p.qtd_itens_reembolso ?? '',
    motivo_reembolso:    p.motivo_reembolso    || '',
  })
  const [reembDirty, setReembDirty] = useState(false)
  const [saving, setSaving]         = useState(false)
  const [error,  setError]          = useState(null)

  const setR = (k, v) => { setReemb(r => ({ ...r, [k]: v })); setReembDirty(true) }

  const handleSaveReemb = async () => {
    setSaving(true); setError(null)
    try {
      await dbAtualizarParcela(p.id, {
        sera_reembolsado:    reemb.sera_reembolsado,
        valor_reembolso:     reemb.valor_reembolso     !== '' ? parseFloat(reemb.valor_reembolso)     : null,
        qtd_itens_reembolso: reemb.qtd_itens_reembolso !== '' ? parseInt(reemb.qtd_itens_reembolso)   : null,
        motivo_reembolso:    reemb.motivo_reembolso    || null,
      })
      onSaved()
    } catch {
      setError('Erro ao salvar reembolso')
      setSaving(false)
    }
  }

  const Field = ({ label, value, mono = false, full = false }) => (
    <div className={full ? 'col-span-2' : ''}>
      <p className={LABEL}>{label}</p>
      <p className={`${VAL}${mono ? ' font-mono' : ''}`}>{value || '—'}</p>
    </div>
  )

  const tipoProrr = p.isento_encargos === true  ? 'Isenta de encargos'
                  : p.isento_encargos === false ? 'Com encargos'
                  : p.dias_cartorio            ? 'Envio ao cartório'
                  : '—'

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in">
      <div className="bg-g-900 border border-g-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col animate-fade-up">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-g-800">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-g-850 border border-g-800 rounded-lg">
              <CreditCard className="w-4 h-4 text-g-400" />
            </div>
            <div>
              <h2 className="text-g-100 font-semibold text-base">Detalhe da Parcela</h2>
              <p className="text-g-600 text-xs font-mono">{p.placa} · {p.id_ord_serv || 'sem OS'}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-g-600 hover:text-g-300 hover:bg-g-850 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto px-5 py-5 flex flex-col gap-5">

          {/* Seção OS */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Wrench className="w-3.5 h-3.5 text-g-600" />
              <span className="text-g-500 text-xs font-semibold uppercase tracking-wider">Ordem de Serviço</span>
            </div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-3">
              <Field label="Placa"       value={p.placa}       mono />
              <Field label="Fornecedor"  value={p.fornecedor} />
              <Field label="Nº OS"       value={p.id_ord_serv} mono />
              <Field label="Data Execução" value={dateBR(p.data_execucao)} />
              <Field label="Empresa"     value={empresaSigla(p.empresa, p.empresa_nome)} />
              <Field label="Modelo"      value={p.modelo} />
              {p.fornecedor_os && p.fornecedor && p.fornecedor_os !== p.fornecedor && (
                <Field label="Fornecedor da OS" value={p.fornecedor_os} />
              )}
              {p.tipo_custo && <Field label="Tipo de custo" value={p.tipo_custo} />}
              {p.descricao && <Field label="Descrição" value={p.descricao} full />}
              {p.contrato_nome && (
                <>
                  <Field label="Contratante"   value={p.contrato_nome} full />
                  <Field label="Cidade/Região"  value={p.contrato_cidade} />
                  <Field label="Período contratual"
                         value={p.contrato_inicio && p.contrato_fim
                           ? `${dateBR(p.contrato_inicio)} → ${dateBR(p.contrato_fim)}`
                           : p.contrato_inicio ? `Desde ${dateBR(p.contrato_inicio)}` : null} />
                  <Field label="Status do contrato" value={p.contrato_status} />
                </>
              )}
            </div>
          </div>

          {/* Seção Parcela */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <CreditCard className="w-3.5 h-3.5 text-g-600" />
              <span className="text-g-500 text-xs font-semibold uppercase tracking-wider">Parcela</span>
            </div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-3">
              <Field label="Nota Fiscal" value={p.nota} />
              <Field label="Parcela"     value={p.parcela_atual && p.parcela_total ? `${p.parcela_atual} de ${p.parcela_total}` : null} />
              <Field label={p.prorrogada ? 'Vencimento original' : 'Vencimento'}
                     value={dateBR(p.prorrogada ? p.data_vencimento_original : p.data_vencimento)} />
              <Field label="Valor original" value={brl(p.valor_parcela)} mono />
              <Field label="Forma Pgto"  value={p.forma_pgto} />
              <Field label="Status"      value={FIN_STATUS[statusFinanceiro(p)]?.label} />
            </div>
          </div>

          {/* Seção Prorrogação */}
          {p.prorrogada && (
            <div>
              <div className="flex items-center gap-2 mb-3">
                <CalendarClock className="w-3.5 h-3.5 text-purple-500" />
                <span className="text-purple-400 text-xs font-semibold uppercase tracking-wider">Prorrogação</span>
              </div>
              <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                <Field label="Tipo"          value={tipoProrr} />
                <Field label="Nova data"     value={dateBR(p.data_vencimento)} />
                {p.tipo_pgto_prorrogacao && <Field label="Forma Pgto"  value={p.tipo_pgto_prorrogacao === 'pix' ? 'PIX' : 'Boleto'} />}
                {p.chave_pix              && <Field label="Chave PIX"  value={p.chave_pix} mono />}
                {p.multa_pct != null      && <Field label="Multa"      value={`${p.multa_pct}%`} />}
                {p.juros_diario_pct != null && <Field label="Juros/dia"  value={`${p.juros_diario_pct}%`} />}
                {p.valor_atualizado != null && <Field label="Valor atualizado" value={brl(p.valor_atualizado)} mono />}
                {p.data_prevista_pagamento  && <Field label="Previsão Pgto"    value={dateBR(p.data_prevista_pagamento)} />}
                {p.dias_cartorio            && <Field label="Dias p/ cartório" value={`${p.dias_cartorio} dias`} />}
              </div>
            </div>
          )}

          {/* Aviso para entradas sintéticas (NFs sem parcelas explícitas) */}
          {p._isSintetica && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg px-4 py-3 text-amber-400 text-xs">
              Esta entrada representa o total da NF. Crie parcelas explícitas na OS para registrar pagamentos e prorrogações.
            </div>
          )}

          {/* Seção Reembolso */}
          {!p._isSintetica && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <RotateCcw className="w-3.5 h-3.5 text-g-600" />
              <span className="text-g-500 text-xs font-semibold uppercase tracking-wider">Reembolso</span>
            </div>
            <div className="flex flex-col gap-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={reemb.sera_reembolsado}
                  onChange={e => setR('sera_reembolsado', e.target.checked)}
                  className="w-4 h-4 rounded border-g-700 bg-g-900 text-g-100 focus:ring-g-400"
                />
                <span className="text-g-400 text-sm">Será reembolsado pelo cliente</span>
              </label>
              {reemb.sera_reembolsado && (
                <div className="grid grid-cols-2 gap-3 pl-6">
                  <div>
                    <label className="text-g-600 text-xs font-medium mb-1 block">Valor a reembolsar (R$)</label>
                    <input
                      type="number" step="0.01"
                      value={reemb.valor_reembolso}
                      onChange={e => setR('valor_reembolso', e.target.value)}
                      placeholder="0,00"
                      className="w-full px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm focus:outline-none focus:border-g-100 transition-colors"
                    />
                  </div>
                  <div>
                    <label className="text-g-600 text-xs font-medium mb-1 block">Qtd de itens reembolsados</label>
                    <input
                      type="number"
                      value={reemb.qtd_itens_reembolso}
                      onChange={e => setR('qtd_itens_reembolso', e.target.value)}
                      placeholder="0"
                      className="w-full px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm focus:outline-none focus:border-g-100 transition-colors"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="text-g-600 text-xs font-medium mb-1 block">Motivo do reembolso</label>
                    <textarea
                      value={reemb.motivo_reembolso}
                      onChange={e => setR('motivo_reembolso', e.target.value)}
                      placeholder="Descreva o motivo…"
                      rows={3}
                      className="w-full px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm focus:outline-none focus:border-g-100 transition-colors resize-none"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
          )}

          {error && <p className="text-red-500 text-xs bg-red-50/10 border border-red-500/20 rounded-lg px-3 py-2">{error}</p>}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-g-800 flex items-center justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 rounded-lg border border-g-800 text-g-500 text-sm hover:bg-g-850 transition-colors">
            Fechar
          </button>
          {reembDirty && !p._isSintetica && (
            <button
              onClick={handleSaveReemb}
              disabled={saving}
              className="px-5 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-500 disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Salvar Reembolso
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body
  )
}

// ── Aba Financeiro ────────────────────────────────────────────────────
function FinanceiroTab({ year, alertDismissed, onAlertDismiss }) {
  const [parcelas,       setParcelas]       = useState([])
  const [osList,         setOsList]         = useState([])
  const [loading,        setLoading]        = useState(true)
  const [viewMode,       setViewMode]       = useState('parcelas')   // 'parcelas' | 'notas'
  const [categoria,      setCategoria]      = useState('pendente')
  const [alertVisible,   setAlertVisible]   = useState(false)
  const [modalProrrogar, setModalProrrogar] = useState(null)
  const [modalDetalhe,   setModalDetalhe]   = useState(null)
  const [filterText,     setFilterText]     = useState('')
  const [filterEmpresa,  setFilterEmpresa]  = useState('')
  const [filterMes,      setFilterMes]      = useState('')
  const [sort,           setSort]           = useState({ col: 'data_vencimento', dir: 'asc' })
  const [expandedNfs,    setExpandedNfs]    = useState(new Set())

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [parcelasReal, osListData] = await Promise.all([dbListParcelas(year), dbListOs()])
      const osList = osListData

      // NFs que já têm parcelas explícitas (usa nf.parcelas do OS para cobrir todos os anos,
      // não apenas o ano filtrado — evita dupla contagem inter-anos)
      const nfIdsComParcelas = new Set(
        osList.flatMap(os => (os.notas_fiscais || []).filter(nf => nf.parcelas?.length > 0).map(nf => nf.id))
      )
      const anoSelecionado = year ? parseInt(year) : null

      // Status de OS que representam obrigação financeira (finalizada ou aguardando NF)
      const STATUS_FINANCEIROS = new Set(['finalizada', 'executado_aguardando_nf'])

      const sinteticas = []
      for (const os of osList) {
        if (!STATUS_FINANCEIROS.has(os.status_os)) continue
        for (const nf of os.notas_fiscais || []) {
          if (nfIdsComParcelas.has(nf.id)) continue
          if (!nf.valor_total_nf) continue

          // Data de referência para filtro de ano: data_emissao da NF ou data_execucao da OS
          const dataRef = nf.data_emissao || os.data_execucao
          if (anoSelecionado) {
            if (!dataRef) continue  // sem data, não é possível atribuir ao ano
            if (parseInt(String(dataRef).slice(0, 4)) !== anoSelecionado) continue
          }

          const descricao = (os.itens || [])
            .map(it => it.servico || it.sistema).filter(Boolean).join('; ') || null

          sinteticas.push({
            id: `nf-${nf.id}`,
            _isSintetica: true,
            nf_id: nf.id,
            manutencao_id: null,
            nota: nf.numero_nf,
            fornecedor: nf.fornecedor || os.fornecedor,
            fornecedor_os: os.fornecedor,
            valor_parcela: nf.valor_total_nf,
            valor_item_total: nf.valor_total_nf,
            valor_atualizado: null,
            // Sem data_vencimento → statusFinanceiro retorna 'pendente' e evita "vencida" falso
            data_vencimento: null,
            data_vencimento_original: null,
            status_pagamento: 'Pendente',
            prorrogada: false,
            placa: os.placa,
            modelo: os.modelo,
            empresa: os.empresa,
            empresa_nome: null,
            id_contrato: os.id_contrato,
            id_ord_serv: os.numero_os,
            data_execucao: os.data_execucao,
            descricao,
            nf_ordem: null,
            parcela_atual: null,
            parcela_total: null,
            forma_pgto: null,
            isento_encargos: null, tipo_pgto_prorrogacao: null, chave_pix: null,
            multa_pct: null, juros_diario_pct: null, data_prevista_pagamento: null,
            dias_cartorio: null, sera_reembolsado: false, valor_reembolso: null,
            qtd_itens_reembolso: null, motivo_reembolso: null,
            contrato_nome: null, contrato_cidade: null, contrato_inicio: null,
            contrato_fim: null, contrato_status: null,
          })
        }
      }
      setOsList(osList)
      setParcelas([...parcelasReal, ...sinteticas])
    } finally {
      setLoading(false)
    }
  }, [year])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (loading || alertDismissed) return
    const hoje = new Date(); hoje.setHours(0, 0, 0, 0)
    const venceHoje = parcelas.filter(p => {
      if (p.status_pagamento !== 'Pendente') return false
      if (!p.data_vencimento) return false
      const v = parseLocalDate(p.data_vencimento)
      return v && v.getTime() === hoje.getTime()
    })
    if (venceHoje.length > 0) setAlertVisible(true)
  }, [loading, parcelas, alertDismissed])

  const enriched = useMemo(() =>
    parcelas.map(p => ({ ...p, _status: statusFinanceiro(p) })),
    [parcelas]
  )

  const empresas = useMemo(() => {
    const seen = new Map()
    enriched.forEach(p => {
      const cod = String(parseInt(parseFloat(p.empresa)))
      if (!isNaN(parseInt(cod)) && !seen.has(cod))
        seen.set(cod, empresaSigla(p.empresa, p.empresa_nome))
    })
    return [...seen.entries()].sort((a, b) => a[1].localeCompare(b[1]))
  }, [enriched])

  const CATS = [
    { key: 'todas',      label: 'Total' },
    { key: 'vence_hoje', label: 'Vencendo hoje' },
    { key: 'pendente',   label: 'Pendentes' },
    { key: 'prorrogada', label: 'Prorrogadas' },
    { key: 'vencida',    label: 'Vencidas' },
    { key: 'pago',       label: 'Pagas' },
  ]

  // Base: applies empresa + mês + texto — sem categoria. Usado nos KPIs e contagens.
  const baseFiltered = useMemo(() => {
    let r = enriched
    if (filterEmpresa) r = r.filter(p => String(parseInt(parseFloat(p.empresa))) === filterEmpresa)
    if (filterMes) r = r.filter(p => {
      const dateStr = p.data_prevista_pagamento || p.data_vencimento
      if (!dateStr) return false
      return parseInt(String(dateStr).slice(5, 7)) === parseInt(filterMes)
    })
    if (filterText.trim()) {
      const q = filterText.toLowerCase()
      r = r.filter(p =>
        [p.placa, p.fornecedor, p.id_ord_serv, p.nota, p.modelo, p.empresa_nome, p.contrato_nome]
          .some(f => (f || '').toLowerCase().includes(q))
      )
    }
    return r
  }, [enriched, filterText, filterEmpresa, filterMes])

  const filtered = useMemo(() => {
    let r = categoria === 'todas' ? baseFiltered : baseFiltered.filter(p => p._status === categoria)
    if (sort.col) {
      const isDateStr = v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}/.test(v)
      r = [...r].sort((a, b) => {
        const av = a[sort.col] ?? '', bv = b[sort.col] ?? ''
        if (!isDateStr(av) && !isDateStr(bv)) {
          const an = parseFloat(av), bn = parseFloat(bv)
          if (!isNaN(an) && !isNaN(bn)) return sort.dir === 'asc' ? an - bn : bn - an
        }
        return sort.dir === 'asc'
          ? av.toString().localeCompare(bv.toString())
          : bv.toString().localeCompare(av.toString())
      })
    }
    return r
  }, [enriched, categoria, filterText, filterEmpresa, filterMes, sort])

  const venceHojeList = useMemo(() => baseFiltered.filter(p => p._status === 'vence_hoje'), [baseFiltered])

  // ── Agrupamento por Nota Fiscal ────────────────────────────────────
  const nfGroups = useMemo(() => {
    const nfMeta = new Map()
    for (const os of osList) {
      for (const nf of os.notas_fiscais || []) {
        if (!nfMeta.has(nf.id)) {
          nfMeta.set(nf.id, {
            nf_id:       nf.id,
            numero_nf:   nf.numero_nf,
            fornecedor:  nf.fornecedor || os.fornecedor,
            fornecedor_os: os.fornecedor,
            placa:       os.placa,
            modelo:      os.modelo,
            empresa:     os.empresa,
            empresa_nome: null,
            id_contrato: os.id_contrato,
            numero_os:   os.numero_os,
            valor_total_nf: nf.valor_total_nf,
            data_emissao:   nf.data_emissao,
            data_execucao:  os.data_execucao,
            parcelas:    [],
          })
        }
      }
    }
    for (const p of baseFiltered) {
      if (p.nf_id && nfMeta.has(p.nf_id)) {
        nfMeta.get(p.nf_id).parcelas.push(p)
      }
    }
    return [...nfMeta.values()]
      .filter(g => g.parcelas.length > 0)
      .map(g => {
        const totalPago     = g.parcelas.filter(p => p._status === 'pago').reduce((s, p) => s + (parseFloat(p.valor_atualizado ?? p.valor_parcela) || 0), 0)
        const totalPendente = g.parcelas.filter(p => p._status !== 'pago').reduce((s, p) => s + (parseFloat(p.valor_atualizado ?? p.valor_parcela) || 0), 0)
        const hasVencida    = g.parcelas.some(p => p._status === 'vencida')
        const hasVenceHoje  = g.parcelas.some(p => p._status === 'vence_hoje')
        const allPago       = g.parcelas.every(p => p._status === 'pago')
        return { ...g, totalPago, totalPendente, hasVencida, hasVenceHoje, allPago }
      })
      .sort((a, b) => {
        const aDate = a.parcelas.map(p => p.data_vencimento).filter(Boolean).sort()[0] || ''
        const bDate = b.parcelas.map(p => p.data_vencimento).filter(Boolean).sort()[0] || ''
        return aDate.localeCompare(bDate)
      })
  }, [baseFiltered, osList])

  const hoje = new Date(); hoje.setHours(0, 0, 0, 0)
  const totalPendente  = baseFiltered.filter(p => p._status !== 'pago').reduce((s, p) => s + (parseFloat(p.valor_atualizado ?? p.valor_parcela) || 0), 0)
  const totalVencidas  = baseFiltered.filter(p => p._status === 'vencida').length
  const totalVenceHoje = venceHojeList.length
  const totalPago      = baseFiltered.filter(p => p._status === 'pago').reduce((s, p) => s + (parseFloat(p.valor_atualizado ?? p.valor_parcela) || 0), 0)

  const toggleSort = (col) => setSort(s => ({ col, dir: s.col === col && s.dir === 'asc' ? 'desc' : 'asc' }))
  const SortIcon = ({ col }) => sort.col === col
    ? (sort.dir === 'asc' ? <ChevronUp className="w-3 h-3 inline ml-0.5" /> : <ChevronDown className="w-3 h-3 inline ml-0.5" />)
    : <ChevronDown className="w-3 h-3 inline ml-0.5 opacity-20" />

  const handleMarcarPago = async (p) => {
    await dbAtualizarParcela(p.id, { status_pagamento: 'Pago' })
    load()
  }

  const handleMarcarPagoSintetica = async (p) => {
    await dbCriarParcelaNf(p.nf_id, {
      valor_parcela: p.valor_parcela,
      status_pagamento: 'Pago',
      nota: p.nota,
      fornecedor: p.fornecedor,
      valor_item_total: p.valor_item_total,
      data_vencimento: p.data_vencimento,
    })
    load()
  }

  return (
    <div className="flex flex-col gap-6">

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-3">
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg">
            <CreditCard className="w-4 h-4 text-amber-600" />
          </div>
          <div>
            <p className="text-g-600 text-xs uppercase tracking-wider">Total Pendente</p>
            <p className="text-g-200 font-bold text-lg font-mono tabular-nums">{brl(totalPendente)}</p>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 bg-red-50 border border-red-200 rounded-lg">
            <AlertCircle className="w-4 h-4 text-red-600" />
          </div>
          <div>
            <p className="text-g-600 text-xs uppercase tracking-wider">Vencidas</p>
            <p className="text-g-200 font-bold text-xl">{totalVencidas}</p>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 bg-orange-50 border border-orange-200 rounded-lg">
            <Bell className="w-4 h-4 text-orange-600" />
          </div>
          <div>
            <p className="text-g-600 text-xs uppercase tracking-wider">Vencendo hoje</p>
            <p className="text-g-200 font-bold text-xl">{totalVenceHoje}</p>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 bg-emerald-50 border border-emerald-200 rounded-lg">
            <CheckCircle className="w-4 h-4 text-emerald-600" />
          </div>
          <div>
            <p className="text-g-600 text-xs uppercase tracking-wider">Total Pago</p>
            <p className="text-g-200 font-bold text-lg font-mono tabular-nums">{brl(totalPago)}</p>
          </div>
        </div>
      </div>

      {/* Filtro de categoria + busca + empresa */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between gap-3">
          <div className="flex gap-1 bg-g-850 border border-g-800 rounded-xl p-1 w-fit">
            {CATS.map(c => {
              const count = c.key === 'todas' ? baseFiltered.length : baseFiltered.filter(p => p._status === c.key).length
              return (
                <button
                  key={c.key}
                  onClick={() => setCategoria(c.key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    categoria === c.key
                      ? 'bg-white shadow-sm text-g-200 border border-g-800'
                      : 'text-g-600 hover:text-g-400'
                  }`}
                >
                  {c.label} <span className="opacity-60">({count})</span>
                </button>
              )
            })}
          </div>
          <div className="flex gap-1 bg-g-850 border border-g-800 rounded-xl p-1">
            {[{ k: 'parcelas', label: 'Parcelas' }, { k: 'notas', label: 'Por Nota' }].map(({ k, label }) => (
              <button
                key={k}
                onClick={() => setViewMode(k)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  viewMode === k
                    ? 'bg-white shadow-sm text-g-200 border border-g-800'
                    : 'text-g-600 hover:text-g-400'
                }`}
              >{label}</button>
            ))}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative flex-1 min-w-52">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-g-600" />
            <input
              value={filterText}
              onChange={e => setFilterText(e.target.value)}
              placeholder="Filtrar por placa, fornecedor, nº OS, empresa…"
              className="w-full pl-9 pr-9 py-2 bg-g-900 border border-g-800 rounded-lg text-g-400 text-sm placeholder-g-700 focus:outline-none focus:border-g-100 transition-colors"
            />
            {filterText && (
              <button onClick={() => setFilterText('')} className="absolute right-3 top-1/2 -translate-y-1/2">
                <X className="w-3.5 h-3.5 text-g-600 hover:text-g-400" />
              </button>
            )}
          </div>
          {empresas.length > 0 && (
            <select
              value={filterEmpresa}
              onChange={e => setFilterEmpresa(e.target.value)}
              className="py-2 px-3 bg-g-900 border border-g-800 rounded-lg text-g-400 text-sm focus:outline-none focus:border-g-100 transition-colors"
            >
              <option value="">Todas as empresas</option>
              {empresas.map(([cod, sigla]) => <option key={cod} value={cod}>{sigla}</option>)}
            </select>
          )}
          <select
            value={filterMes}
            onChange={e => setFilterMes(e.target.value)}
            className="py-2 px-3 bg-g-900 border border-g-800 rounded-lg text-g-400 text-sm focus:outline-none focus:border-g-100 transition-colors"
          >
            <option value="">Todos os meses</option>
            {['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'].map((m, i) => (
              <option key={i+1} value={i+1}>{m}</option>
            ))}
          </select>
        </div>
      </div>

      {/* View: Por Nota Fiscal */}
      {!loading && viewMode === 'notas' && (
        <div className="flex flex-col gap-3">
          {nfGroups.length === 0 ? (
            <div className="card flex items-center justify-center h-32 gap-2 text-g-600 text-sm">
              <Search className="w-4 h-4" /> Nenhuma nota nesta categoria
            </div>
          ) : nfGroups.map(g => {
            const expanded = expandedNfs.has(g.nf_id)
            const toggleExpand = () => setExpandedNfs(prev => {
              const next = new Set(prev)
              expanded ? next.delete(g.nf_id) : next.add(g.nf_id)
              return next
            })
            const statusColor = g.hasVencida    ? 'border-l-red-500'
                               : g.hasVenceHoje  ? 'border-l-orange-400'
                               : g.allPago       ? 'border-l-emerald-500'
                               : 'border-l-g-700'
            return (
              <div key={g.nf_id} className={`card border-l-4 ${statusColor} overflow-hidden`}>
                {/* Header da NF */}
                <button
                  onClick={toggleExpand}
                  className="w-full flex items-center gap-3 p-4 hover:bg-g-850 transition-colors text-left"
                >
                  <div className="flex-1 grid grid-cols-[auto_1fr_1fr_1fr_auto_auto] gap-x-4 items-center min-w-0">
                    <span className="font-mono font-bold text-g-200 text-sm">{g.placa}</span>
                    <span className="text-g-500 text-xs truncate">{g.fornecedor || '—'}</span>
                    <span className="text-g-600 text-xs font-mono truncate">{g.numero_os || '—'}</span>
                    <span className="text-g-500 text-xs truncate">
                      NF <span className="text-g-300 font-medium">{g.numero_nf || '—'}</span>
                    </span>
                    <div className="text-right">
                      <span className="font-mono font-bold text-g-200 text-sm tabular-nums">{brl(g.valor_total_nf)}</span>
                      {g.totalPago > 0 && g.totalPago < (g.valor_total_nf || 0) && (
                        <span className="block text-emerald-600 text-xs">{brl(g.totalPago)} pago</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 ml-2">
                      <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${
                        g.hasVencida   ? 'bg-red-50/20 text-red-400 border-red-400/30'
                        : g.hasVenceHoje ? 'bg-orange-50/20 text-orange-400 border-orange-400/30'
                        : g.allPago    ? 'bg-emerald-50/20 text-emerald-500 border-emerald-500/30'
                        : 'bg-slate-50/10 text-g-500 border-g-700'
                      }`}>
                        {g.hasVencida ? 'Vencida' : g.hasVenceHoje ? 'Vence hoje' : g.allPago ? 'Pago' : 'Pendente'}
                      </span>
                      {expanded
                        ? <ChevronUp className="w-3.5 h-3.5 text-g-600" />
                        : <ChevronDown className="w-3.5 h-3.5 text-g-600" />}
                    </div>
                  </div>
                </button>

                {/* Parcelas expandidas */}
                {expanded && (
                  <div className="border-t border-g-800">
                    <table className="w-full">
                      <thead className="bg-g-850">
                        <tr>
                          <th className="th th-left text-[10px]">Parcela</th>
                          <th className="th th-left text-[10px]">Vencimento</th>
                          <th className="th text-[10px]">Valor</th>
                          <th className="th text-[10px]">Status</th>
                          <th className="th th-left text-[10px]">Previsão Pgto</th>
                          <th className="th text-[10px]">Ações</th>
                        </tr>
                      </thead>
                      <tbody>
                        {g.parcelas.map(p => {
                          const previsao = p.prorrogada
                            ? (p.data_prevista_pagamento || p.data_vencimento)
                            : p.data_prevista_pagamento
                          const prevAtrasada = previsao && p.status_pagamento !== 'Pago' && new Date(previsao) < hoje
                          return (
                            <tr
                              key={p.id}
                              onClick={() => setModalDetalhe(p)}
                              className="border-b border-g-800 hover:bg-g-850 transition-colors cursor-pointer"
                            >
                              <td className="td td-left text-xs text-g-600 tabular-nums">
                                {p.parcela_atual && p.parcela_total ? `${p.parcela_atual} / ${p.parcela_total}` : '—'}
                              </td>
                              <td className="td td-left text-xs text-g-500 tabular-nums">
                                <span className="flex items-center gap-1">
                                  {p.prorrogada ? dateBR(p.data_vencimento_original) : dateBR(p.data_vencimento)}
                                  {p.prorrogada && <span className="text-purple-500 text-xs" title={`Nova data: ${dateBR(p.data_vencimento)}`}>↻</span>}
                                  {p._status === 'vencida' && <AlertTriangle className="w-3 h-3 text-red-500" />}
                                </span>
                              </td>
                              <td className="td font-mono font-semibold text-g-300 tabular-nums text-sm">
                                {brl(p.valor_atualizado ?? p.valor_parcela)}
                                {p.valor_atualizado && p.valor_atualizado !== p.valor_parcela && (
                                  <span className="block text-g-700 text-xs font-normal">{brl(p.valor_parcela)} orig.</span>
                                )}
                              </td>
                              <td className="td"><FinBadge status={p._status} /></td>
                              <td className="td td-left text-xs tabular-nums">
                                {previsao ? (
                                  <span className={`flex items-center gap-1 ${prevAtrasada ? 'text-red-500 font-medium' : 'text-g-500'}`}>
                                    {dateBR(previsao)}{prevAtrasada && <AlertTriangle className="w-3 h-3" />}
                                  </span>
                                ) : '—'}
                              </td>
                              <td className="td" onClick={e => e.stopPropagation()}>
                                {p._isSintetica ? (
                                  <div className="flex items-center justify-end gap-1">
                                    <span className="text-[10px] text-g-700 italic px-1">via NF</span>
                                    <button onClick={() => handleMarcarPagoSintetica(p)} className="px-2 py-1 text-xs text-emerald-700 border border-emerald-200 rounded-lg hover:bg-emerald-50 transition-colors">Pago</button>
                                  </div>
                                ) : (
                                  <div className="flex items-center justify-end gap-1">
                                    {p._status !== 'pago' && (
                                      <button onClick={() => setModalProrrogar(p)} className="px-2 py-1 text-xs text-g-400 border border-g-800 rounded-lg hover:bg-g-850 hover:text-g-200 transition-colors flex items-center gap-1">
                                        <CalendarClock className="w-3 h-3" /> Prorrogar
                                      </button>
                                    )}
                                    {p._status !== 'pago' && (
                                      <button onClick={() => handleMarcarPago(p)} className="px-2 py-1 text-xs text-emerald-700 border border-emerald-200 rounded-lg hover:bg-emerald-50 transition-colors">Pago</button>
                                    )}
                                  </div>
                                )}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                      <tfoot className="bg-g-850 border-t border-g-700">
                        <tr>
                          <td colSpan={2} className="td td-left text-xs text-g-600 font-semibold uppercase tracking-wider">
                            {g.parcelas.length} {g.parcelas.length === 1 ? 'parcela' : 'parcelas'}
                          </td>
                          <td className="td font-mono font-bold text-g-200 tabular-nums text-sm">
                            {brl(g.totalPendente + g.totalPago)}
                            {g.totalPago > 0 && <span className="block text-emerald-600 text-xs font-normal">{brl(g.totalPago)} pago</span>}
                          </td>
                          <td colSpan={3} />
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                )}
              </div>
            )
          })}
          {nfGroups.length > 0 && (
            <div className="card p-4 flex items-center justify-between">
              <span className="text-g-600 text-xs font-semibold uppercase tracking-wider">
                {nfGroups.length} {nfGroups.length === 1 ? 'nota fiscal' : 'notas fiscais'}
              </span>
              <span className="font-mono font-bold text-g-200 tabular-nums">
                {brl(nfGroups.reduce((s, g) => s + g.totalPendente + g.totalPago, 0))}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Tabela de parcelas */}
      {!loading && viewMode === 'parcelas' && (
      <div className="card overflow-hidden">
        {filtered.length === 0 ? (
          <div className="flex items-center justify-center h-32 gap-2 text-g-600 text-sm">
            <Search className="w-4 h-4" />
            {filterText ? `Nenhum resultado para "${filterText}"` : 'Nenhuma parcela nesta categoria'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1000px]">
              <thead className="bg-g-850 border-b border-g-800">
                <tr>
                  {[
                    { key: 'placa',            label: 'Placa',         cls: 'th-left' },
                    { key: 'empresa_nome',      label: 'Empresa',       cls: 'th-left' },
                    { key: 'fornecedor',        label: 'Fornecedor',    cls: 'th-left' },
                    { key: 'id_ord_serv',       label: 'Nº OS',         cls: 'th-left' },
                    { key: 'nota',              label: 'Nota Fiscal',   cls: 'th-left' },
                    { key: 'parcela_atual',     label: 'Parcela',       cls: '' },
                    { key: 'data_vencimento',   label: 'Vencimento',    cls: 'th-left' },
                    { key: 'valor_parcela',     label: 'Valor',         cls: '' },
                    { key: 'status_pagamento',  label: 'Status',        cls: '' },
                    { key: 'data_prevista_pagamento', label: 'Previsão Pgto', cls: 'th-left' },
                  ].map(({ key, label, cls }) => (
                    <th key={key} onClick={() => toggleSort(key)} className={`th ${cls} cursor-pointer select-none hover:text-g-300 transition-colors`}>
                      {label}<SortIcon col={key} />
                    </th>
                  ))}
                  <th className="th">Ações</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(p => {
                  const previsao = p.prorrogada
                    ? (p.data_prevista_pagamento || p.data_vencimento)
                    : p.data_prevista_pagamento
                  const prevAtrasada = previsao
                    && p.status_pagamento !== 'Pago'
                    && new Date(previsao) < hoje
                  const rowBg = p._status === 'vencida'    ? 'bg-red-50/20'
                              : p._status === 'vence_hoje' ? 'bg-orange-50/20'
                              : p._status === 'prorrogada' ? 'bg-purple-50/10'
                              : ''
                  return (
                    <tr
                      key={p.id}
                      onClick={() => setModalDetalhe(p)}
                      className={`border-b border-g-800 hover:bg-g-850 transition-colors cursor-pointer ${rowBg}`}
                    >
                      <td className="td td-left font-mono font-bold text-g-200">{p.placa}</td>
                      <td className="td td-left text-xs text-g-500 tabular-nums" title={p.empresa_nome || ''}>{empresaSigla(p.empresa, p.empresa_nome)}</td>
                      <td className="td td-left text-g-500 truncate max-w-[140px]" title={p.fornecedor_os && p.fornecedor_os !== p.fornecedor ? `OS: ${p.fornecedor_os}` : ''}>
                        <span className="flex items-center gap-1">
                          <span className="truncate">{p.fornecedor || '—'}</span>
                          {p.fornecedor_os && p.fornecedor && p.fornecedor_os !== p.fornecedor && (
                            <span className="text-[10px] text-amber-500 bg-amber-500/10 border border-amber-500/30 rounded px-1">≠OS</span>
                          )}
                        </span>
                      </td>
                      <td className="td td-left font-mono text-xs text-g-400">{p.id_ord_serv || '—'}</td>
                      <td className="td td-left text-xs text-g-500">{p.nota || '—'}</td>
                      <td className="td text-xs text-g-600 tabular-nums text-center">
                        {p.parcela_atual && p.parcela_total ? `${p.parcela_atual} / ${p.parcela_total}` : '—'}
                      </td>
                      <td className="td td-left text-xs text-g-500 tabular-nums">
                        <span className="flex items-center gap-1">
                          {p.prorrogada ? dateBR(p.data_vencimento_original) : dateBR(p.data_vencimento)}
                          {p.prorrogada && <span className="text-purple-500 text-xs" title={`Nova data: ${dateBR(p.data_vencimento)}`}>↻</span>}
                          {p._status === 'vencida' && <AlertTriangle className="w-3 h-3 text-red-500" />}
                        </span>
                      </td>
                      <td className="td font-mono font-semibold text-g-300 tabular-nums text-sm">
                        {brl(p.valor_atualizado ?? p.valor_parcela)}
                        {p.valor_atualizado && p.valor_atualizado !== p.valor_parcela && (
                          <span className="block text-g-700 text-xs font-normal">{brl(p.valor_parcela)} orig.</span>
                        )}
                      </td>
                      <td className="td"><FinBadge status={p._status} /></td>
                      <td className="td td-left text-xs tabular-nums">
                        {previsao ? (
                          <span className={`flex items-center gap-1 ${prevAtrasada ? 'text-red-500 font-medium' : 'text-g-500'}`}>
                            {dateBR(previsao)}
                            {prevAtrasada && <AlertTriangle className="w-3 h-3" />}
                          </span>
                        ) : '—'}
                      </td>
                      <td className="td" onClick={e => e.stopPropagation()}>
                        {p._isSintetica ? (
                          <div className="flex items-center justify-end gap-1">
                            <span className="text-[10px] text-g-700 italic px-1">via NF</span>
                            <button
                              onClick={() => handleMarcarPagoSintetica(p)}
                              title="Registrar como pago"
                              className="px-2 py-1 text-xs text-emerald-700 border border-emerald-200 rounded-lg hover:bg-emerald-50 transition-colors"
                            >Pago</button>
                          </div>
                        ) : (
                          <div className="flex items-center justify-end gap-1">
                            {p._status !== 'pago' && (
                              <button
                                onClick={() => setModalProrrogar(p)}
                                title="Prorrogar"
                                className="px-2 py-1 text-xs text-g-400 border border-g-800 rounded-lg hover:bg-g-850 hover:text-g-200 transition-colors flex items-center gap-1"
                              >
                                <CalendarClock className="w-3 h-3" /> Prorrogar
                              </button>
                            )}
                            {p._status !== 'pago' && (
                              <button
                                onClick={() => handleMarcarPago(p)}
                                title="Marcar como pago"
                                className="px-2 py-1 text-xs text-emerald-700 border border-emerald-200 rounded-lg hover:bg-emerald-50 transition-colors"
                              >
                                Pago
                              </button>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
              {filtered.length > 0 && (() => {
                const somaValor = filtered.reduce((s, p) => s + (parseFloat(p.valor_atualizado ?? p.valor_parcela) || 0), 0)
                const somaPago  = filtered.filter(p => p._status === 'pago').reduce((s, p) => s + (parseFloat(p.valor_atualizado ?? p.valor_parcela) || 0), 0)
                const qtdCols = 11
                return (
                  <tfoot className="bg-g-850 border-t-2 border-g-700">
                    <tr>
                      <td colSpan={qtdCols - 2} className="td td-left">
                        <span className="text-g-600 text-xs font-semibold uppercase tracking-wider">
                          {filtered.length} {filtered.length === 1 ? 'parcela' : 'parcelas'}
                        </span>
                      </td>
                      <td className="td font-mono font-bold text-g-200 tabular-nums text-sm" colSpan={2}>
                        <span className="block">{brl(somaValor)}</span>
                        {somaPago > 0 && somaPago < somaValor && (
                          <span className="block text-emerald-600 text-xs font-normal">{brl(somaPago)} pago</span>
                        )}
                      </td>
                      <td className="td" />
                    </tr>
                  </tfoot>
                )
              })()}
            </table>
          </div>
        )}
      </div>
      )}

      {/* Modal alerta contas do dia */}
      {alertVisible && !alertDismissed && (
        <AlertContasDiaModal
          parcelas={venceHojeList}
          onCiente={() => { onAlertDismiss(); setAlertVisible(false) }}
          onLembrarDepois={() => setAlertVisible(false)}
        />
      )}

      {/* Modal prorrogar */}
      {modalProrrogar && (
        <ProrrogarParcelaModal
          parcela={modalProrrogar}
          onClose={() => setModalProrrogar(null)}
          onSaved={() => { setModalProrrogar(null); load() }}
        />
      )}

      {/* Modal detalhe de parcela */}
      {modalDetalhe && (
        <DetalheParcelaModal
          parcela={modalDetalhe}
          onClose={() => setModalDetalhe(null)}
          onSaved={() => { setModalDetalhe(null); load() }}
        />
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
  const [finAlertDismissed, setFinAlertDismissed] = useState(false)

  return (
    <div className="flex flex-col gap-6">
      {/* Tabs principais */}
      <div className="flex gap-1 bg-g-850 border border-g-800 rounded-xl p-1 w-fit">
        {[
          { key: 'gestao',      label: 'Gestão de OS',    icon: Wrench },
          { key: 'financeiro',  label: 'Financeiro',      icon: DollarSign },
          { key: 'analise',     label: 'Análise',         icon: BarChart2 },
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

      {tab === 'gestao'     && <GestaoTab />}
      {tab === 'financeiro' && <FinanceiroTab year={year} alertDismissed={finAlertDismissed} onAlertDismiss={() => setFinAlertDismissed(true)} />}
      {tab === 'analise'    && <AnaliseTab year={year} vehicles={vehicles} />}
    </div>
  )
}
