import { useEffect, useState, useMemo, useCallback, useRef, Fragment } from 'react'
import { createPortal } from 'react-dom'
import html2pdf from 'html2pdf.js'
import { getMaintenanceAnalysis, getImplementoAnalysis, getIntervalosAnalysis, dbListManutencoes, dbAtualizarManutencao, dbDeletarManutencao, dbAtualizarParcela, dbListParcelas, dbListOs, dbAtualizarOs, dbDeletarOs, dbCriarParcelaNf, createPneuRodizio, deletePneuRodizio } from '../utils/api'
import { brl, brlShort, num, dateBR, titleCase, shortenProviderName } from '../utils/format'
import KPICard from '../components/KPICard'
import AbrirManutencaoModal from '../components/AbrirManutencaoModal'
import FinalizarManutencaoModal from '../components/FinalizarManutencaoModal'
import AbrirOsModal from '../components/AbrirOsModal'
import FinalizarOsModal from '../components/FinalizarOsModal'
import DetalhesOsModal from '../components/DetalhesOsModal'
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
  CreditCard, CalendarClock, Ban, RotateCcw, Printer, FileText, ArrowRight,
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
  aberta: { label: 'Aberta', color: 'bg-blue-50 text-blue-700 border-blue-200' },
  em_andamento: { label: 'Em andamento', color: 'bg-amber-50 text-amber-700 border-amber-200' },
  aguardando_peca: { label: 'Aguardando peça', color: 'bg-orange-50 text-orange-700 border-orange-200' },
  executado_aguardando_nf: { label: 'Aguardando NF', color: 'bg-purple-50 text-purple-700 border-purple-200' },
  pendente: { label: 'Pendente', color: 'bg-slate-100 text-slate-600 border-slate-300' },
  finalizada: { label: 'Finalizada', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
}



const EMPRESA_NOME_MAP = {
  'TKJ': 'TKJ', 'FINITA': 'FINITA', 'LANDKRAFT': 'LANDKRAFT',
  '1': 'TKJ', '2': 'FINITA', '3': 'LANDKRAFT',
}
const MONTHS_BR = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

function resolveEmpresaNome(cod) {
  if (!cod) return null
  const key = String(cod).toUpperCase().trim()
  return EMPRESA_NOME_MAP[key] || EMPRESA_NOME_MAP[String(parseInt(cod))] || String(cod).toUpperCase()
}
function getEmpresasFaturadas(os) {
  if (!os.notas_fiscais || os.notas_fiscais.length === 0) return '—';
  const emp = new Set(os.notas_fiscais.map(nf => resolveEmpresaNome(nf.empresa_faturada)).filter(Boolean));
  if (emp.size === 0) return '—';
  return Array.from(emp).join(' · ');
}

function getFornecedoresUnicos(os) {
  if (!os.notas_fiscais || os.notas_fiscais.length === 0) return os.fornecedor || '—';
  const forns = new Set(os.notas_fiscais.map(nf => nf.fornecedor).filter(Boolean));
  if (forns.size === 0) return os.fornecedor || '—';
  return Array.from(forns).join(' / ');
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
      // Try date comparison first (ISO strings like 2026-04-22)
      const ad = Date.parse(av), bd = Date.parse(bv)
      if (!isNaN(ad) && !isNaN(bd)) return dir === 'asc' ? ad - bd : bd - ad
      // Numeric comparison
      const an = parseFloat(av), bn = parseFloat(bv)
      if (!isNaN(an) && !isNaN(bn)) return dir === 'asc' ? an - bn : bn - an
      // String comparison
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
  const [deleting, setDeleting] = useState(false)

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
  const hasPneu = m.posicao_pneu || m.espec_pneu || m.marca_pneu
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
              <Field label="Tipo de Manutenção" value={m.tipo_manutencao} />
              <Field label="Sistema" value={m.sistema} />
              <Field label="Serviço" value={m.servico} />
              <Field label="Data de Entrada" value={dateBR(m.data_entrada)} />
              <Field label="KM" value={m.km ? `${num(m.km)} km` : null} />
              <Field label="Responsável Técnico" value={m.responsavel_tec} />
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
              {m.descricao && <Field label="Descrição" value={m.descricao} full />}
              {m.observacoes && <Field label="Observações" value={m.observacoes} full />}
            </div>
          </div>

          {/* OS Finalizada */}
          {isFinalizada && (
            <div className="border-t border-g-800 pt-5">
              <p className="text-g-600 text-xs font-semibold uppercase tracking-wider mb-3">Ordem de Serviço</p>
              <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                <Field label="Nº da OS" value={m.id_ord_serv} mono />
                <Field label="Data de Execução" value={dateBR(m.data_execucao)} />
                <Field label="Valor Total" value={m.total_os ? brl(m.total_os) : null} mono />
                <Field label="Categoria" value={m.categoria} />
                {m.qtd_itens && <Field label="Qtd. Itens" value={String(m.qtd_itens)} />}
                {m.prox_km && <Field label="Próx. KM" value={`${num(m.prox_km)} km`} />}
                {m.prox_data && <Field label="Próx. Data" value={dateBR(m.prox_data)} />}
              </div>
            </div>
          )}

          {/* Pneu */}
          {hasPneu && (
            <div className="border-t border-g-800 pt-5">
              <p className="text-g-600 text-xs font-semibold uppercase tracking-wider mb-3">Dados de Pneu</p>
              <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                <Field label="Posição" value={m.posicao_pneu} />
                <Field label="Qtd." value={m.qtd_pneu ? String(m.qtd_pneu) : null} />
                <Field label="Especificação" value={m.espec_pneu} />
                <Field label="Marca" value={m.marca_pneu} />
                <Field label="Manejo" value={m.manejo_pneu} />
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
function GestaoTab({ year }) {
  const [abertas, setAbertas] = useState([])
  const [finalizadas, setFinalizadas] = useState([])
  const [loading, setLoading] = useState(true)
  const [subTab, setSubTab] = useState('em_andamento')
  const [modalAbrir, setModalAbrir] = useState(false)
  const [modalFin, setModalFin] = useState(null)
  const [modalEdit, setModalEdit] = useState(null)
  const [modalDetalhe, setModalDetalhe] = useState(null)
  const [confirmDel, setConfirmDel] = useState(null)
  const [filterAberta, setFilterAberta] = useState('')
  const [filterFin, setFilterFin] = useState('')
  const [sortAberta, setSortAberta] = useState({ col: 'data_entrada', dir: 'desc' })
  const [sortFin, setSortFin] = useState({ col: 'data_execucao', dir: 'desc' })
  const [filterTipo, setFilterTipo] = useState('todos')
  const [dossieOpen, setDossieOpen] = useState(false)
  const [dossiePlaca, setDossiePlaca] = useState('')
  const [isDossieGenerating, setIsDossieGenerating] = useState(false)
  const dossieRef = useRef(null)

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
    try {
      await dbDeletarOs(id)
      setConfirmDel(null)
      load()
    } catch (err) {
      alert(err.response?.data?.detail || 'Erro ao excluir OS')
      setConfirmDel(null)
    }
  }

  const sortAbertaBy = col => setSortAberta(s => s.col !== col ? { col, dir: 'asc' } : s.dir === 'asc' ? { col, dir: 'desc' } : { col: null, dir: 'asc' })
  const sortFinBy = col => setSortFin(s => s.col !== col ? { col, dir: 'asc' } : s.dir === 'asc' ? { col, dir: 'desc' } : { col: null, dir: 'asc' })

  const emAndamento = abertas.filter(o => o.status_os === 'em_andamento')
  const aguardando = abertas.filter(o => o.status_os === 'aguardando_peca')
  const agNf = abertas.filter(o => o.status_os === 'executado_aguardando_nf')
  const todasAbertas = abertas

  // flatten first item for filter/sort display
  const withDisplay = list => list.map(o => {
    const allParcelas = (o.notas_fiscais || []).flatMap(nf => nf.parcelas || [])

    // Agrupar parcelas por data de vencimento (mesmo boleto)
    const boletosUnicos = []
    const mapaBoletos = {}
    allParcelas.forEach(p => {
      if (p.data_vencimento) {
        if (!mapaBoletos[p.data_vencimento]) {
          mapaBoletos[p.data_vencimento] = []
          boletosUnicos.push(mapaBoletos[p.data_vencimento])
        }
        mapaBoletos[p.data_vencimento].push(p)
      } else {
        boletosUnicos.push([p])
      }
    })

    const totalParcelas = boletosUnicos.length
    const pagas = boletosUnicos.filter(grupo => grupo.every(p => p.status_pagamento === 'Pago')).length

    return {
      ...o,
      _sistema: [...new Set((o.itens || []).map(i => i.sistema).filter(Boolean))].join(' · ') || '',
      _servico: [...new Set((o.itens || []).map(i => i.servico).filter(Boolean))].join(' · ') || '',
      _categorias: [...new Set((o.itens || []).map(i => (i.categoria || '').toLowerCase()).filter(Boolean))],
      _sistemas: [...new Set((o.itens || []).map(i => (i.sistema || '').toLowerCase()).filter(Boolean))],
      _totalNfs: (o.notas_fiscais || []).reduce((s, nf) => s + (nf.valor_total_nf || 0), 0),
      _allParcelas: allParcelas,
      _totalParcelas: totalParcelas,
      _pagas: pagas,
    }
  })

  const applyTipoFilter = list => list.filter(o => {
    if (filterTipo === 'todos') return true
    if (filterTipo === 'implemento') return o._sistemas.some(s => s === 'implemento')
    return o._categorias.includes(filterTipo)
  })

  const filteredAbertas = useMemo(() =>
    applyTipoFilter(applyFilterSort(withDisplay(todasAbertas), filterAberta, sortAberta, ['placa', 'fornecedor', 'status_os', 'modelo', '_sistema', '_servico'])),
    [todasAbertas, filterAberta, sortAberta, filterTipo]
  )

  const filteredFin = useMemo(() => {
    const byYear = year
      ? finalizadas.filter(o => {
        const dateStr = o.data_execucao || o.data_entrada || o.criado_em || (o.notas_fiscais?.[0]?.data_emissao)
        if (!dateStr) return true // Para evitar que a OS suma do sistema
        return new Date(dateStr).getFullYear() === parseInt(year)
      })
      : finalizadas
    return applyTipoFilter(applyFilterSort(withDisplay(byYear), filterFin, sortFin, ['placa', 'fornecedor', 'modelo', '_sistema', '_servico', 'numero_os']))
  }, [finalizadas, filterFin, sortFin, year, filterTipo])

  const allPlacas = useMemo(() =>
    [...new Set([...abertas, ...finalizadas].map(o => o.placa).filter(Boolean))].sort(),
    [abertas, finalizadas]
  )

  const handleDossie = async () => {
    if (!dossiePlaca) return
    setIsDossieGenerating(true)
    try {
      await html2pdf().set({
        margin: [10, 10],
        filename: `Dossie_${dossiePlaca}_${year || 'Todos'}.pdf`,
        image: { type: 'png' },
        html2canvas: { scale: 3, useCORS: true, logging: false },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait', compress: true },
        pagebreak: { mode: ['avoid-all', 'css', 'legacy'] },
      }).from(dossieRef.current).save()
    } finally {
      setIsDossieGenerating(false)
      setDossieOpen(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">

      {/* KPIs rápidos */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
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
            { key: 'finalizadas', label: `Finalizadas (${finalizadas.length})` },
          ].map(t => (
            <button
              key={t.key}
              onClick={() => setSubTab(t.key)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${subTab === t.key
                  ? 'bg-white shadow-sm text-g-200 border border-g-800'
                  : 'text-g-600 hover:text-g-400'
                }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setDossieOpen(true)}
            className="flex items-center gap-2 px-3 py-2 bg-g-850 border border-g-800 text-g-300 rounded-lg text-sm font-medium hover:bg-g-800 hover:text-g-100 transition-colors"
          >
            <FileText className="w-4 h-4" /> Dossiê por Placa
          </button>
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

      {/* Filtro por tipo de item */}
      <div className="flex gap-1 bg-g-850 border border-g-800 rounded-xl p-1 self-start">
        {[
          { key: 'todos', label: 'Todos' },
          { key: 'serviço', label: 'Serviço' },
          { key: 'compra', label: 'Compra' },
          { key: 'implemento', label: 'Implemento' },
        ].map(t => (
          <button
            key={t.key}
            onClick={() => setFilterTipo(t.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${filterTipo === t.key
              ? 'bg-white shadow-sm text-g-200 border border-g-800'
              : 'text-g-600 hover:text-g-400'
            }`}
          >{t.label}</button>
        ))}
      </div>

      {/* Tabela Em Andamento */}
      {subTab === 'em_andamento' && (
        <>
          <div className="flex items-center gap-3 relative">
            <div className="relative flex-1">
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
            <select
              value={`${sortAberta.col || 'data_entrada'}-${sortAberta.dir}`}
              onChange={e => {
                const [col, dir] = e.target.value.split('-');
                setSortAberta({ col, dir });
              }}
              className="w-48 px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm focus:outline-none focus:border-g-100 transition-colors cursor-pointer"
            >
              <option value="data_entrada-desc">Mais recentes</option>
              <option value="data_entrada-asc">Mais antigas</option>
              <option value="placa-asc">Placa (A-Z)</option>
              <option value="status_os-asc">Status</option>
            </select>
          </div>
          <div>
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
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
                {filteredAbertas.map(o => {
                  const dias = o.indisponivel && o.data_entrada ? diasParados(o.data_entrada) : null;
                  const borderCol = o.status_os === 'aguardando_peca' ? 'border-orange-500' :
                    o.status_os === 'executado_aguardando_nf' ? 'border-purple-500' :
                      'border-amber-500';

                  return (
                    <div
                      key={o.id}
                      onClick={() => setModalDetalhe(o)}
                      className={`border-l-4 ${borderCol} rounded-xl bg-white shadow-sm hover:shadow-md transition-all cursor-pointer p-6 flex flex-col gap-5 relative group`}
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between pb-3 border-b border-g-800">
                        <div>
                          <div className="flex items-center gap-3 mb-1.5">
                            <span className="font-mono font-bold text-g-100 text-xl tracking-tight">{o.placa}</span>
                            <span className="text-g-500 text-[10px] px-2 py-0.5 bg-g-900 rounded-md border border-g-800 font-mono uppercase font-bold">
                              {o.numero_os || 'Sem OS'}
                            </span>
                          </div>
                          <span className="text-g-500 text-xs font-semibold uppercase tracking-wider">{o.modelo || 'Sem modelo'}</span>
                        </div>
                        <div className="flex flex-col items-end gap-1.5">
                          <StatusBadge status={o.status_os} />
                          {dias !== null && (
                            <span className={`text-[10px] font-bold uppercase tracking-wider ${dias > 30 ? 'text-red-500' : dias > 7 ? 'text-amber-500' : 'text-g-500'}`}>
                              {dias} dias na oficina
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Body Info */}
                      <div className="flex-1 flex flex-col gap-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="bg-g-950/30 p-3 rounded-lg border border-g-900/50">
                            <span className="block text-g-600 text-[10px] uppercase font-bold mb-1 tracking-widest">Entrada</span>
                            <span className="text-g-200 text-sm font-medium">{dateBR(o.data_entrada) || '—'}</span>
                          </div>
                          <div className="bg-g-950/30 p-3 rounded-lg border border-g-900/50">
                            <span className="block text-g-600 text-[10px] uppercase font-bold mb-1 tracking-widest">Mecânico</span>
                            <span className="text-g-200 text-sm font-medium truncate block">{o.responsavel_tec || 'Não definido'}</span>
                          </div>
                        </div>

                        <div>
                          <span className="block text-g-600 text-[10px] uppercase font-bold mb-1 tracking-widest">Fornecedores</span>
                          <span className="text-g-300 text-sm font-medium truncate block" title={getFornecedoresUnicos(o)}>{getFornecedoresUnicos(o)}</span>
                        </div>

                        <div>
                          <span className="block text-g-600 text-[10px] uppercase font-bold mb-1 tracking-widest">Serviço Principal</span>
                          <div className="text-g-400 text-sm line-clamp-2 leading-relaxed" title={`${o._sistema || ''} - ${o._servico || ''}`}>
                            {o._sistema && <span className="text-g-200 font-semibold">{o._sistema}</span>}
                            {o._servico && <span className="text-g-500 text-xs"> · {o._servico}</span>}
                            {!o._sistema && !o._servico && <span className="text-g-700 italic text-xs">Não informado</span>}
                          </div>
                        </div>

                        {(o.km || o.prox_km) && (
                          <div className="flex items-center gap-3 pt-1">
                            {o.km && <span className="text-xs font-mono text-g-500 border border-g-800 px-2 py-0.5 rounded font-bold">KM {num(o.km)}</span>}
                            {o.prox_km && <span className="text-xs font-mono text-blue-500 border border-blue-200 px-2 py-0.5 rounded bg-blue-50 font-bold">Próx: {num(o.prox_km)}</span>}
                          </div>
                        )}
                      </div>

                      {/* Footer Actions */}
                      <div className="flex items-center justify-between border-t border-g-800 pt-3 mt-1" onClick={e => e.stopPropagation()}>
                        <div className="flex items-center gap-1.5">
                          {o.status_os === 'em_andamento' && (
                            <button
                              onClick={() => handleStatusChange(o, 'aguardando_peca')}
                              title="Aguardando peça"
                              className="px-2.5 py-1.5 text-xs font-semibold text-orange-600 bg-orange-50 hover:bg-orange-100 rounded-lg transition-colors"
                            >
                              Ag. peça
                            </button>
                          )}
                          {o.status_os === 'aguardando_peca' && (
                            <button
                              onClick={() => handleStatusChange(o, 'em_andamento')}
                              title="Retomar andamento"
                              className="px-2.5 py-1.5 text-xs font-semibold text-amber-600 bg-amber-50 hover:bg-amber-100 rounded-lg transition-colors"
                            >
                              Retomar
                            </button>
                          )}
                        </div>

                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => setModalEdit(o)}
                            title="Editar OS"
                            className="p-2 text-g-500 bg-g-900 border border-g-800 hover:text-g-100 hover:bg-g-850 rounded-lg transition-colors"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => setModalFin(o)}
                            className="px-3 py-1.5 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors border border-emerald-500 shadow-sm"
                          >
                            Finalizar
                          </button>
                          <button
                            onClick={() => setConfirmDel(o.id)}
                            className="p-2 text-g-500 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors ml-1"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </>
      )}

      {/* Tabela Finalizadas */}
      {subTab === 'finalizadas' && (
        <>
          <div className="flex items-center gap-3 relative">
            <div className="relative flex-1">
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
            <select
              value={`${sortFin.col || 'data_execucao'}-${sortFin.dir}`}
              onChange={e => {
                const [col, dir] = e.target.value.split('-');
                setSortFin({ col, dir });
              }}
              className="w-48 px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm focus:outline-none focus:border-g-100 transition-colors cursor-pointer"
            >
              <option value="data_execucao-desc">Mais recentes</option>
              <option value="data_execucao-asc">Mais antigas</option>
              <option value="placa-asc">Placa (A-Z)</option>
              <option value="_totalNfs-desc">Maior valor</option>
              <option value="_totalNfs-asc">Menor valor</option>
            </select>
          </div>
          <div>
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
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
                {filteredFin.map(o => {
                  const dias = o.indisponivel && o.data_entrada && o.data_execucao ? diasParados(o.data_entrada, o.data_execucao) : null
                  const totalParcelas = o._totalParcelas ?? 0
                  const pagas = o._pagas ?? 0
                  const pgtoProgresso = totalParcelas > 0 ? Math.round((pagas / totalParcelas) * 100) : 0
                  const pagoTotal = totalParcelas > 0 && pagas === totalParcelas
                  const pagoNenhum = pagas === 0 || totalParcelas === 0
                  const pagoParc = !pagoTotal && !pagoNenhum

                  // Bar top color: green = quitado, purple = parcial, gray = não pago
                  const barTopColor = pagoTotal ? '#10b981' : pagoParc ? '#615cf6' : '#6b7280'
                  const pgBarFill = pagoTotal ? '#10b981' : pagoParc ? '#615cf6' : '#9ca3af'
                  const pgStatusLabel = pagoTotal ? 'Quitado' : pagoParc ? `${pagas} de ${totalParcelas} pagas` : 'Não pago'
                  const pgLabelStyle = pagoTotal
                    ? { color: '#10b981', background: 'rgba(16,185,129,0.1)' }
                    : pagoParc
                      ? { color: '#615cf6', background: 'rgba(139,92,246,0.1)' }
                      : { color: '#9ca3af', background: 'rgba(107,114,128,0.1)' }

                  // Minimal brand indicators: colored dot + text, no background
                  const empColor = (nome) => {
                    if (!nome) return '#6b7280'
                    if (nome === 'TKJ') return '#04674b'
                    if (nome === 'LANDKRAFT') return '#8c7900'
                    return '#94a3b8'
                  }

                  const empresas = o.notas_fiscais
                    ? [...new Set(o.notas_fiscais.map(nf => resolveEmpresaNome(nf.empresa_faturada)).filter(Boolean))]
                    : []

                  return (
                    <div
                      key={o.id}
                      onClick={() => setModalDetalhe(o)}
                      className="rounded-xl bg-white shadow-md hover:shadow-xl transition-all cursor-pointer flex flex-col overflow-hidden"
                      style={{ border: '1px solid rgba(0,0,0,0.07)' }}
                    >
                      {/* Barra colorida no TOPO */}
                      <div style={{ height: '5px', background: barTopColor, flexShrink: 0 }} />

                      {/* Header */}
                      <div className="px-5 pt-4 pb-3">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <div className="flex items-center gap-2 mb-0.5">
                              <span className="font-mono font-extrabold text-g-100" style={{ fontSize: '1.2rem', letterSpacing: '-0.02em' }}>{o.placa}</span>
                              <span className="text-g-600 font-mono text-[10px] font-bold uppercase tracking-wider">
                                {o.numero_os || ''}
                              </span>
                            </div>
                            <span className="text-g-500 text-[10px] font-semibold uppercase tracking-widest">{o.modelo || 'Sem modelo'}</span>
                          </div>
                          <div className="text-right shrink-0">
                            <div className="font-mono font-extrabold text-g-100 text-base">{brl(o._totalNfs)}</div>
                            <div className="text-g-600 text-xs mt-0.5">{dateBR(o.data_execucao) || '—'}</div>
                          </div>
                        </div>

                        {/* Empresas: ponto colorido + nome simples */}
                        <div className="flex items-center gap-3 flex-wrap mt-2">
                          {empresas.length > 0
                            ? empresas.map(emp => (
                              <span key={emp} className="flex items-center gap-1.5 text-xs font-semibold" style={{ color: empColor(emp), letterSpacing: '0.04em' }}>
                                <span style={{ width: 6, height: 6, borderRadius: '50%', background: empColor(emp), display: 'inline-block', flexShrink: 0 }} />
                                {emp}
                              </span>
                            ))
                            : <span className="text-g-700 text-xs">—</span>
                          }
                        </div>
                      </div>


                      {/* Divisor */}
                      <div style={{ height: '1px', background: 'rgba(0,0,0,0.06)', margin: '0 20px' }} />

                      {/* Corpo */}
                      <div className="px-5 py-3 flex flex-col gap-2.5 flex-1">
                        <div>
                          <div className="text-g-600 text-[10px] font-bold uppercase tracking-widest mb-1">Fornecedor</div>
                          <div className="text-g-300 text-sm font-medium truncate" title={getFornecedoresUnicos(o)}>{getFornecedoresUnicos(o)}</div>
                        </div>

                        <div>
                          <div className="text-g-600 text-[10px] font-bold uppercase tracking-widest mb-1">Serviço</div>
                          <div className="text-g-400 text-sm line-clamp-2 leading-relaxed">
                            {o._sistema && <span className="text-g-200 font-semibold">{o._sistema}</span>}
                            {o._servico && <span className="text-g-500 text-xs"> · {o._servico}</span>}
                            {!o._sistema && !o._servico && <span className="text-g-700 italic text-xs">Não informado</span>}
                          </div>
                        </div>

                        {(o.km || dias !== null) && (
                          <div className="flex items-center gap-2 flex-wrap">
                            {o.km && (
                              <span className="text-xs font-mono text-g-500 border border-g-800 px-2 py-0.5 rounded">{num(o.km)} km</span>
                            )}
                            {dias !== null && (
                              <span className="text-xs text-g-600 border border-g-800 px-2 py-0.5 rounded">{dias}d na oficina</span>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Footer: status pagamento */}
                      <div className="px-5 pb-4 pt-3" style={{ borderTop: '1px solid rgba(0,0,0,0.06)' }}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[10px] font-bold text-g-500 uppercase tracking-widest">Pagamento</span>
                          <span className="text-xs font-bold px-2.5 py-0.5 rounded-full" style={pgLabelStyle}>{pgStatusLabel}</span>
                        </div>
                        <div style={{ height: '5px', background: 'rgba(0,0,0,0.06)', borderRadius: '999px', overflow: 'hidden' }}>
                          <div style={{ width: `${pgtoProgresso}%`, height: '100%', background: pgBarFill, borderRadius: '999px', transition: 'width 0.5s ease' }} />
                        </div>
                        <div className="flex items-center justify-end gap-1 mt-2.5" onClick={e => e.stopPropagation()}>
                          <button onClick={() => setModalEdit(o)} title="Editar" className="p-1.5 text-g-600 hover:text-g-300 rounded-lg hover:bg-g-900 transition-colors">
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button onClick={() => setConfirmDel(o.id)} className="p-1.5 text-g-700 hover:text-red-500 rounded-lg hover:bg-red-50/10 transition-colors">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
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
      {modalEdit && modalEdit.status_os === 'finalizada' ? (
        <FinalizarOsModal os={modalEdit} onClose={() => setModalEdit(null)} onSaved={handleSaved} editMode={true} />
      ) : modalEdit ? (
        <AbrirOsModal os={modalEdit} onClose={() => setModalEdit(null)} onSaved={handleSaved} />
      ) : null}

      {modalDetalhe && (
        <DetalhesOsModal manutencao={modalDetalhe} onClose={() => setModalDetalhe(null)} onDeleted={() => { setModalDetalhe(null); load() }} />
      )}

      {/* Modal Dossiê por Placa */}
      {dossieOpen && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-g-900 border border-g-800 rounded-2xl shadow-2xl p-6 w-full max-w-sm mx-4 animate-fade-up">
            <div className="flex items-center justify-between mb-5">
              <div>
                <p className="text-g-100 font-bold text-base">Dossiê por Placa</p>
                <p className="text-g-600 text-xs mt-0.5">Relatório completo de manutenções{year ? ` — ${year}` : ''}</p>
              </div>
              <button onClick={() => setDossieOpen(false)} className="p-1.5 text-g-600 hover:text-g-300 rounded-lg hover:bg-g-850">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex flex-col gap-3">
              <select
                value={dossiePlaca}
                onChange={e => setDossiePlaca(e.target.value)}
                className="w-full px-3 py-2.5 bg-g-850 border border-g-800 rounded-lg text-g-200 text-sm focus:outline-none focus:border-g-100"
              >
                <option value="">Selecione uma placa…</option>
                {allPlacas.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
              <button
                onClick={handleDossie}
                disabled={!dossiePlaca || isDossieGenerating}
                className="flex items-center justify-center gap-2 w-full px-4 py-2.5 bg-g-100 text-white rounded-lg text-sm font-bold hover:bg-g-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isDossieGenerating ? <><Loader2 className="w-4 h-4 animate-spin" /> Gerando…</> : <><Printer className="w-4 h-4" /> Gerar PDF</>}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Template oculto do Dossiê */}
      <div style={{ position: 'absolute', left: '-9999px', top: 0 }}>
        <div ref={dossieRef} style={{ fontFamily: 'Arial, sans-serif', fontSize: '11px', color: '#1a1a1a', background: '#fff', padding: '20px', width: '794px' }}>
          {/* Cabeçalho */}
          <div style={{ borderBottom: '2px solid #0f4a27', paddingBottom: '12px', marginBottom: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h1 style={{ fontSize: '18px', fontWeight: 'bold', color: '#0f4a27', margin: 0 }}>Dossiê de Manutenções</h1>
                <p style={{ color: '#555', fontSize: '12px', margin: '4px 0 0' }}>Placa: <strong>{dossiePlaca}</strong>{year ? ` · Período: ${year}` : ''}</p>
              </div>
              <p style={{ color: '#888', fontSize: '10px', textAlign: 'right', margin: 0 }}>
                Gerado em {new Date().toLocaleString('pt-BR')}<br />
                Total de OS: {[...abertas, ...finalizadas].filter(o => o.placa === dossiePlaca).length}
              </p>
            </div>
          </div>

          {/* OS por placa */}
          {[...abertas, ...finalizadas]
            .filter(o => o.placa === dossiePlaca)
            .sort((a, b) => {
              const da = a.data_execucao || a.data_entrada || ''
              const db2 = b.data_execucao || b.data_entrada || ''
              return db2.localeCompare(da)
            })
            .map((o, idx) => {
              const totalNfs = (o.notas_fiscais || []).reduce((s, nf) => s + (nf.valor_total_nf || 0), 0)
              return (
                <div key={o.id} style={{ marginBottom: '24px', pageBreakInside: 'avoid', border: '1px solid #e5e7eb', borderRadius: '8px', overflow: 'hidden' }}>
                  {/* Header OS */}
                  <div style={{ background: '#f0fdf4', borderBottom: '1px solid #d1fae5', padding: '10px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <span style={{ fontWeight: 'bold', fontSize: '13px', color: '#065f46' }}>OS #{o.numero_os || 'S/N'}</span>
                      <span style={{ color: '#6b7280', fontSize: '11px', marginLeft: '10px' }}>{o.modelo || ''}</span>
                    </div>
                    <div style={{ display: 'flex', gap: '12px', fontSize: '10px', color: '#374151' }}>
                      <span>Status: <strong>{o.status_os || '—'}</strong></span>
                      {o.data_entrada && <span>Entrada: <strong>{dateBR(o.data_entrada)}</strong></span>}
                      {o.data_execucao && <span>Execução: <strong>{dateBR(o.data_execucao)}</strong></span>}
                      {totalNfs > 0 && <span style={{ color: '#065f46', fontWeight: 'bold' }}>Total: {brl(totalNfs)}</span>}
                    </div>
                  </div>

                  <div style={{ padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {/* Informações gerais */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', fontSize: '10px' }}>
                      {o.fornecedor && <div><span style={{ color: '#6b7280', display: 'block' }}>Fornecedor</span><strong>{o.fornecedor}</strong></div>}
                      {o.responsavel_tec && <div><span style={{ color: '#6b7280', display: 'block' }}>Mecânico</span><strong>{o.responsavel_tec}</strong></div>}
                      {o.km && <div><span style={{ color: '#6b7280', display: 'block' }}>KM</span><strong>{num(o.km)}</strong></div>}
                      {o.prox_km && <div><span style={{ color: '#6b7280', display: 'block' }}>Próx. KM</span><strong>{num(o.prox_km)}</strong></div>}
                    </div>

                    {/* Itens */}
                    {(o.itens || []).length > 0 && (
                      <div>
                        <p style={{ fontWeight: 'bold', fontSize: '10px', color: '#374151', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Itens / Serviços</p>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '10px' }}>
                          <thead>
                            <tr style={{ background: '#f9fafb' }}>
                              <th style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'left' }}>Categoria</th>
                              <th style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'left' }}>Sistema</th>
                              <th style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'left' }}>Serviço</th>
                              <th style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'left' }}>Descrição</th>
                              <th style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'center' }}>Qtd</th>
                            </tr>
                          </thead>
                          <tbody>
                            {o.itens.map((it, i) => (
                              <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#f9fafb' }}>
                                <td style={{ border: '1px solid #e5e7eb', padding: '4px 6px' }}>{it.categoria || '—'}</td>
                                <td style={{ border: '1px solid #e5e7eb', padding: '4px 6px' }}>{it.sistema || '—'}</td>
                                <td style={{ border: '1px solid #e5e7eb', padding: '4px 6px' }}>{it.servico || '—'}</td>
                                <td style={{ border: '1px solid #e5e7eb', padding: '4px 6px' }}>{it.descricao || '—'}</td>
                                <td style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'center' }}>{it.qtd_itens || '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Notas Fiscais */}
                    {(o.notas_fiscais || []).length > 0 && (
                      <div>
                        <p style={{ fontWeight: 'bold', fontSize: '10px', color: '#374151', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Notas Fiscais</p>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '10px' }}>
                          <thead>
                            <tr style={{ background: '#f9fafb' }}>
                              <th style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'left' }}>Nº NF</th>
                              <th style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'left' }}>Fornecedor</th>
                              <th style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'left' }}>Emissão</th>
                              <th style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'right' }}>Valor</th>
                              <th style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'left' }}>Tipo</th>
                            </tr>
                          </thead>
                          <tbody>
                            {o.notas_fiscais.map((nf, i) => (
                              <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#f9fafb' }}>
                                <td style={{ border: '1px solid #e5e7eb', padding: '4px 6px' }}>{nf.numero_nf || '—'}</td>
                                <td style={{ border: '1px solid #e5e7eb', padding: '4px 6px' }}>{nf.fornecedor || '—'}</td>
                                <td style={{ border: '1px solid #e5e7eb', padding: '4px 6px' }}>{dateBR(nf.data_emissao) || '—'}</td>
                                <td style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'right', fontWeight: 'bold' }}>{brl(nf.valor_total_nf)}</td>
                                <td style={{ border: '1px solid #e5e7eb', padding: '4px 6px' }}>{nf.tipo_nf || '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>

                        {/* Parcelas */}
                        {o.notas_fiscais.some(nf => (nf.parcelas || []).length > 0) && (
                          <div style={{ marginTop: '6px' }}>
                            <p style={{ fontWeight: 'bold', fontSize: '10px', color: '#374151', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Parcelas</p>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '10px' }}>
                              <thead>
                                <tr style={{ background: '#f9fafb' }}>
                                  <th style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'left' }}>NF</th>
                                  <th style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'left' }}>Vencimento</th>
                                  <th style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'right' }}>Valor</th>
                                  <th style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'left' }}>Status</th>
                                </tr>
                              </thead>
                              <tbody>
                                {o.notas_fiscais.flatMap((nf, ni) =>
                                  (nf.parcelas || []).map((p, pi) => (
                                    <tr key={`${ni}-${pi}`} style={{ background: (ni + pi) % 2 === 0 ? '#fff' : '#f9fafb' }}>
                                      <td style={{ border: '1px solid #e5e7eb', padding: '4px 6px' }}>{nf.numero_nf || '—'}</td>
                                      <td style={{ border: '1px solid #e5e7eb', padding: '4px 6px' }}>{dateBR(p.data_vencimento) || '—'}</td>
                                      <td style={{ border: '1px solid #e5e7eb', padding: '4px 6px', textAlign: 'right' }}>{brl(p.valor_parcela)}</td>
                                      <td style={{ border: '1px solid #e5e7eb', padding: '4px 6px', color: p.status_pagamento === 'Pago' ? '#065f46' : '#b91c1c', fontWeight: 'bold' }}>{p.status_pagamento || '—'}</td>
                                    </tr>
                                  ))
                                )}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Observações */}
                    {o.observacoes && (
                      <div>
                        <p style={{ fontWeight: 'bold', fontSize: '10px', color: '#374151', marginBottom: '2px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Observações</p>
                        <p style={{ fontSize: '10px', color: '#4b5563', background: '#f9fafb', padding: '6px 8px', borderRadius: '4px', border: '1px solid #e5e7eb' }}>{o.observacoes}</p>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
        </div>
      </div>
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

function calcValorComEncargos(valorBase, multaPct, jurosDiarioPct, dataVenc, dataFim = null) {
  if (!valorBase) return valorBase
  const venc = parseLocalDate(dataVenc)
  if (!venc) return valorBase

  const fim = dataFim ? parseLocalDate(dataFim) : new Date()
  if (!dataFim) fim.setHours(0, 0, 0, 0)

  const diasAtraso = Math.max(0, Math.round((fim - venc) / 86400000))
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
  pago: { label: 'Pago', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  pendente: { label: 'Pendente', color: 'bg-blue-50 text-blue-700 border-blue-200' },
  vence_hoje: { label: 'Vence hoje', color: 'bg-orange-50 text-orange-700 border-orange-200' },
  vencida: { label: 'Vencida', color: 'bg-red-50 text-red-700 border-red-200' },
  prorrogada: { label: 'Prorrogada', color: 'bg-purple-50 text-purple-700 border-purple-200' },
}

function FinBadge({ status }) {
  const s = FIN_STATUS[status] || FIN_STATUS.pendente
  return <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium border ${s.color}`}>{s.label}</span>
}

// ── Modal: alerta contas do dia ──────────────────────────────────────
function AlertContasDiaModal({ parcelas, onCiente, onLembrarDepois }) {
  const total = parcelas.reduce((sum, p) => sum + (parseFloat(p.valor_atualizado ?? p.valor_parcela) || 0), 0)

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-g-900 border border-orange-500/30 rounded-2xl shadow-2xl w-full max-w-lg animate-fade-up">
        <div className="flex items-center justify-between px-5 py-4 border-b border-g-800">
          <div className="flex items-center gap-3">
            <div className="p-1.5 bg-orange-50 border border-orange-200 rounded-lg">
              <Bell className="w-4 h-4 text-orange-600" />
            </div>
            <div>
              <h2 className="text-g-200 font-semibold text-sm">Contas vencidas ou com vencimento hoje</h2>
              <p className="text-g-600 text-xs">{parcelas.length} parcela{parcelas.length !== 1 ? 's' : ''} pendente{parcelas.length !== 1 ? 's' : ''}</p>
            </div>
          </div>
          <div className="text-right">
            <span className="block text-[10px] text-g-600 uppercase font-bold tracking-wider">Total a Pagar</span>
            <span className="text-lg font-mono font-bold text-orange-400">{brl(total)}</span>
          </div>
        </div>
        <div className="px-5 py-4 flex flex-col gap-2 max-h-72 overflow-y-auto">
          {parcelas.map(p => {
            const isVencida = p._status === 'vencida'
            const isHoje = p._status === 'vence_hoje'
            return (
              <div key={p.id} className={`bg-g-850 border rounded-xl px-4 py-2.5 flex items-center justify-between text-xs ${isVencida ? 'border-red-500/30' : isHoje ? 'border-orange-500/30' : 'border-g-800'}`}>
                <div className="flex items-center gap-3">
                  <span className="font-mono font-bold text-g-200">{p.placa}</span>
                  {isVencida && <span className="text-[10px] bg-red-500/10 text-red-500 border border-red-500/20 px-1 rounded uppercase font-bold">Vencida</span>}
                  {isHoje && <span className="text-[10px] bg-orange-500/10 text-orange-500 border border-orange-500/20 px-1 rounded uppercase font-bold">Vence Hoje</span>}
                  {p.fornecedor && <span className="text-g-500 truncate max-w-[140px]">{p.fornecedor}</span>}
                </div>
                <span className={`font-mono font-semibold ${isVencida ? 'text-red-400' : 'text-orange-400'}`}>{brl(p.valor_parcela)}</span>
              </div>
            )
          })}
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

  const [modo, setModo] = useState(modoInicial)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const [form, setForm] = useState({
    nova_data: p.prorrogada ? (p.data_vencimento || '') : '',
    tipo_pgto: p.tipo_pgto_prorrogacao || 'boleto',
    chave_pix: p.chave_pix || '',
    multa_pct: p.multa_pct != null ? String(p.multa_pct) : '',
    juros_diario_pct: p.juros_diario_pct != null ? String(p.juros_diario_pct) : '',
    data_prevista_pagamento: p.data_prevista_pagamento || '',
    dias_cartorio: p.dias_cartorio != null ? String(p.dias_cartorio) : '',
  })
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const valorBase = parseFloat(p.valor_parcela) || 0
  const dataVencRef = p.data_vencimento_original || p.data_vencimento

  const dataCartorio = useMemo(() =>
    calcDataCartorio(dataVencRef, form.dias_cartorio),
    [dataVencRef, form.dias_cartorio]
  )

  const dataAlvoEncargos = form.data_prevista_pagamento || form.nova_data || null

  const valorEncargos = useMemo(() => {
    if (modo === 'prorrogada_encargos' || modo === 'cartorio') {
      const alvo = modo === 'cartorio' ? dataCartorio : dataAlvoEncargos
      return calcValorComEncargos(valorBase, form.multa_pct, form.juros_diario_pct, dataVencRef, alvo)
    }
    return null
  }, [modo, form.multa_pct, form.juros_diario_pct, valorBase, dataVencRef, dataAlvoEncargos, dataCartorio])

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
                  {(() => {
                    const alvo = modo === 'cartorio' ? dataCartorio : dataAlvoEncargos
                    if (!alvo || !dataVencRef) return null
                    const v = parseLocalDate(dataVencRef)
                    const f = parseLocalDate(alvo)
                    if (!v || !f) return null
                    const dias = Math.max(0, Math.round((f - v) / 86400000))
                    const juros = valorBase * ((parseFloat(form.juros_diario_pct) || 0) / 100) * dias
                    return (
                      <div className="flex justify-between text-g-600">
                        <span>Juros ({form.juros_diario_pct || 0}% x {dias} dias)</span>
                        <span className="font-mono">{brl(juros)}</span>
                      </div>
                    )
                  })()}
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
  const VAL = 'text-g-300 text-sm break-words'

  const [reemb, setReemb] = useState({
    sera_reembolsado: p.sera_reembolsado || false,
    valor_reembolso: p.valor_reembolso ?? '',
    qtd_itens_reembolso: p.qtd_itens_reembolso ?? '',
    motivo_reembolso: p.motivo_reembolso || '',
  })
  const [reembDirty, setReembDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const setR = (k, v) => { setReemb(r => ({ ...r, [k]: v })); setReembDirty(true) }

  const handleSaveReemb = async () => {
    setSaving(true); setError(null)
    try {
      await dbAtualizarParcela(p.id, {
        sera_reembolsado: reemb.sera_reembolsado,
        valor_reembolso: reemb.valor_reembolso !== '' ? parseFloat(reemb.valor_reembolso) : null,
        qtd_itens_reembolso: reemb.qtd_itens_reembolso !== '' ? parseInt(reemb.qtd_itens_reembolso) : null,
        motivo_reembolso: reemb.motivo_reembolso || null,
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

  const tipoProrr = p.isento_encargos === true ? 'Isenta de encargos'
    : p.isento_encargos === false ? 'Com encargos'
      : p.dias_cartorio ? 'Envio ao cartório'
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
              <Field label="Placa" value={p.placa} mono />
              <Field label="Fornecedor" value={p.fornecedor} />
              <Field label="Nº OS" value={p.id_ord_serv} mono />
              <Field label="Data Execução" value={dateBR(p.data_execucao)} />
              <Field label="Empresa" value={empresaSigla(p.empresa, p.empresa_nome)} />
              <Field label="Modelo" value={p.modelo} />
              {p.fornecedor_os && p.fornecedor && p.fornecedor_os !== p.fornecedor && (
                <Field label="Fornecedor da OS" value={p.fornecedor_os} />
              )}
              {p.tipo_custo && <Field label="Tipo de custo" value={p.tipo_custo} />}
              <Field label="Sistema" value={titleCase(p.sistema)} full />
              {p.descricao && <Field label="Descrição" value={titleCase(p.descricao)} full />}
              {p.contrato_nome && (
                <>
                  <Field label="Contratante" value={p.contrato_nome} full />
                  <Field label="Cidade/Região" value={p.contrato_cidade} />
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
              <Field label="Parcela" value={p.parcela_atual && p.parcela_total ? `${p.parcela_atual} de ${p.parcela_total}` : null} />
              <Field label={p.prorrogada ? 'Vencimento original' : 'Vencimento'}
                value={dateBR(p.prorrogada ? p.data_vencimento_original : p.data_vencimento)} />
              <Field label="Valor original" value={brl(p.valor_parcela)} mono />
              <Field label="Forma Pgto" value={p.forma_pgto} />
              <Field label="Status" value={FIN_STATUS[statusFinanceiro(p)]?.label} />
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
                <Field label="Tipo" value={tipoProrr} />
                <Field label="Nova data" value={dateBR(p.data_vencimento)} />
                {p.tipo_pgto_prorrogacao && <Field label="Forma Pgto" value={p.tipo_pgto_prorrogacao === 'pix' ? 'PIX' : 'Boleto'} />}
                {p.chave_pix && <Field label="Chave PIX" value={p.chave_pix} mono />}
                {p.multa_pct != null && <Field label="Multa" value={`${p.multa_pct}%`} />}
                {p.juros_diario_pct != null && <Field label="Juros/dia" value={`${p.juros_diario_pct}%`} />}
                {p.valor_atualizado != null && <Field label="Valor atualizado" value={brl(p.valor_atualizado)} mono />}
                {p.data_prevista_pagamento && <Field label="Previsão Pgto" value={dateBR(p.data_prevista_pagamento)} />}
                {p.dias_cartorio && <Field label="Dias p/ cartório" value={`${p.dias_cartorio} dias`} />}
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
  const [parcelas, setParcelas] = useState([])
  const [osList, setOsList] = useState([])
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState('notas')   // 'parcelas' | 'notas'
  const [categoria, setCategoria] = useState('pendente')
  const [alertVisible, setAlertVisible] = useState(false)
  const [modalProrrogar, setModalProrrogar] = useState(null)
  const [modalDetalhe, setModalDetalhe] = useState(null)
  const [filterText, setFilterText] = useState('')
  const [filterEmpresa, setFilterEmpresa] = useState('')
  const [filterDataDe, setFilterDataDe] = useState('')
  const [filterDataAte, setFilterDataAte] = useState('')
  const [sort, setSort] = useState({ col: 'data_vencimento', dir: 'asc' })
  const [expandedNfs, setExpandedNfs] = useState(new Set())
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false)
  const [showReportDropdown, setShowReportDropdown] = useState(false)
  const [showInstallmentsInReport, setShowInstallmentsInReport] = useState(true)
  const reportRef = useRef(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [parcelasReal, osListData] = await Promise.all([dbListParcelas(year), dbListOs()])
      const osList = osListData

      const anoSelecionado = year ? parseInt(year) : null

      const sinteticas = []
      for (const os of osList) {
        // Removido filtro de status_os: se tem NF, deve constar no financeiro
        for (const nf of os.notas_fiscais || []) {
          // Pula NFs que já possuem parcelas registradas em QUALQUER ano.
          // dbListOs carrega nf.parcelas sem filtro de ano (selectinload sem where),
          // então nf.parcelas.length > 0 é a verificação correta — evita criar entradas
          // sintéticas para NFs cujas parcelas caem em outro ano (ex: dez/2025 pago em jan/2026).
          if ((nf.parcelas || []).length > 0) continue
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
    { key: 'pendente', label: 'Pendentes' },
    { key: 'vence_hoje', label: 'Vencendo hoje' },
    { key: 'prorrogada', label: 'Prorrogadas' },
    { key: 'vencida', label: 'Vencidas' },
    { key: 'pago', label: 'Pagas' },
    { key: 'todas', label: 'Total' },
  ]

  // Base: applies empresa + mês + texto — sem categoria. Usado nos KPIs e contagens.
  const baseFiltered = useMemo(() => {
    let r = enriched
    if (filterEmpresa) {
      r = r.filter(p => {
        const cod = String(parseInt(parseFloat(p.empresa)))
        const sigla = empresaSigla(p.empresa, p.empresa_nome)
        return cod === filterEmpresa || sigla === filterEmpresa
      })
    }
    if (filterDataDe || filterDataAte) r = r.filter(p => {
      const dateStr = p.data_vencimento
      if (!dateStr) return false
      if (filterDataDe && dateStr < filterDataDe) return false
      if (filterDataAte && dateStr > filterDataAte) return false
      return true
    })
    if (filterText.trim()) {
      const q = filterText.toLowerCase()
      r = r.filter(p =>
        [p.placa, p.fornecedor, p.id_ord_serv, p.nota, p.modelo, p.empresa_nome, p.contrato_nome]
          .some(f => (f || '').toLowerCase().includes(q))
      )
    }
    return r
  }, [enriched, filterText, filterEmpresa, filterDataDe, filterDataAte])

  const filtered = useMemo(() => {
    let r = baseFiltered
    if (categoria !== 'todas') {
      r = r.filter(p => {
        if (categoria === 'pendente') return ['pendente', 'prorrogada', 'vencida', 'vence_hoje'].includes(p._status)
        return p._status === categoria
      })
    }
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
  }, [baseFiltered, categoria, sort])

  // Filtro para Por Nota: aplica empresa, texto, categoria e intervalo de datas
  const nfFiltered = useMemo(() => {
    let r = enriched
    if (filterEmpresa) {
      r = r.filter(p => {
        const cod = String(parseInt(parseFloat(p.empresa)))
        const sigla = empresaSigla(p.empresa, p.empresa_nome)
        return cod === filterEmpresa || sigla === filterEmpresa
      })
    }
    if (filterDataDe || filterDataAte) r = r.filter(p => {
      const dateStr = p.data_vencimento
      if (!dateStr) return false
      if (filterDataDe && dateStr < filterDataDe) return false
      if (filterDataAte && dateStr > filterDataAte) return false
      return true
    })
    if (filterText.trim()) {
      const q = filterText.toLowerCase()
      r = r.filter(p =>
        [p.placa, p.fornecedor, p.id_ord_serv, p.nota, p.modelo, p.empresa_nome, p.contrato_nome]
          .some(f => (f || '').toLowerCase().includes(q))
      )
    }
    if (categoria !== 'todas') {
      r = r.filter(p => {
        if (categoria === 'pendente') return ['pendente', 'prorrogada', 'vencida', 'vence_hoje'].includes(p._status)
        return p._status === categoria
      })
    }
    return r
  }, [enriched, filterText, filterEmpresa, filterDataDe, filterDataAte, categoria])

  const venceHojeList = useMemo(() => baseFiltered.filter(p => p._status === 'vence_hoje' || p._status === 'vencida'), [baseFiltered])

  useEffect(() => {
    if (loading || alertDismissed) return
    const alertas = enriched.filter(p => p._status === 'vencida' || p._status === 'vence_hoje')
    if (alertas.length > 0) setAlertVisible(true)
  }, [loading, enriched, alertDismissed])


  // Agrupamento por Mês e depois por Nota Fiscal
  const nfGroupsByMonth = useMemo(() => {
    const monthsMap = new Map() // Map<number, Map<string, object>>

    // 1. Mapeia as parcelas para seus respectivos meses e grupos de NF
    for (const p of nfFiltered) {
      const date = p.data_prevista_pagamento || p.data_vencimento
      const month = date ? parseInt(date.slice(5, 7)) : 0 // 0 = Sem data

      if (!monthsMap.has(month)) monthsMap.set(month, new Map())
      const monthGroup = monthsMap.get(month)

      const nfKey = `${p.nota || 'S/N'}|${p.fornecedor || 'Desconhecido'}`.toLowerCase()

      if (!monthGroup.has(nfKey)) {
        monthGroup.set(nfKey, {
          nfKey,
          numero_nf: p.nota,
          fornecedor: p.fornecedor,
          placas: new Set(),
          osList: new Set(),
          parcelas: [],
          sistemas: new Set(),
          month,
        })
      }

      const g = monthGroup.get(nfKey)
      g.parcelas.push(p)
      if (p.placa) g.placas.add(p.placa)
      if (p.id_ord_serv) g.osList.add(p.id_ord_serv)
      if (p.sistema) g.sistemas.add(p.sistema)
    }

    // 2. Transforma em array e enriquece com metadados e subtotais
    const result = []
    const sortedMonths = Array.from(monthsMap.keys()).sort((a, b) => a - b)

    for (const mIdx of sortedMonths) {
      const invoicesMap = monthsMap.get(mIdx)
      const invoices = Array.from(invoicesMap.values()).map(g => {
        const pList = g.parcelas
        const empresaNome = pList[0]?.empresa_nome || pList[0]?.empresa || 'Empresa não identificada'

        const hasVencida = pList.some(p => p._status === 'vencida')
        const hasVenceHoje = pList.some(p => p._status === 'vence_hoje')
        const hasProrrogada = pList.some(p => p._status === 'prorrogada')

        // Dados globais da NF para o contador total (pode haver parcelas em outros meses)
        const globalNfParcelas = enriched.filter(p =>
          `${p.nota || 'S/N'}|${p.fornecedor || 'Desconhecido'}`.toLowerCase() === g.nfKey
        )
        const globalPago = globalNfParcelas.filter(p => p._status === 'pago').length
        const globalTotal = globalNfParcelas.length
        const allPagoGlobal = globalTotal > 0 && globalPago === globalTotal

        const pendentes = pList.filter(p => p._status !== 'pago').sort((a, b) => (a.data_vencimento || '').localeCompare(b.data_vencimento || ''))
        const nextPending = pendentes[0]
        const nextVencimento = nextPending ? nextPending.data_vencimento : pList[0]?.data_vencimento
        const nextValor = nextVencimento
          ? pendentes
              .filter(p => p.data_vencimento === nextVencimento)
              .reduce((s, p) => s + (parseFloat(p.valor_atualizado ?? p.valor_parcela) || 0), 0)
          : 0

        return {
          ...g,
          placasList: Array.from(g.placas).sort(),
          osList: Array.from(g.osList).sort(),
          sistemasList: Array.from(g.sistemas).sort(),
          nextVencimento,
          nextValor,
          totalGeral: pList.reduce((s, p) => s + (parseFloat(p.valor_atualizado ?? p.valor_parcela) || 0), 0),
          countPago: globalPago,
          countTotal: globalTotal,
          allPago: allPagoGlobal,
          empresa: empresaNome,
          hasVencida, hasVenceHoje, hasProrrogada
        }
      }).sort((a, b) => (a.nextVencimento || '').localeCompare(b.nextVencimento || ''))

      result.push({
        month: mIdx,
        monthName: mIdx ? MONTHS_BR[mIdx - 1] : 'Sem data',
        invoices,
        subtotal: invoices.reduce((s, inv) => s + inv.totalGeral, 0)
      })
    }
    return result
  }, [nfFiltered, enriched])

  const hoje = new Date(); hoje.setHours(0, 0, 0, 0)
  const totalPendente = baseFiltered.filter(p => p._status !== 'pago').reduce((s, p) => s + (parseFloat(p.valor_atualizado ?? p.valor_parcela) || 0), 0)
  const totalVencidas = baseFiltered.filter(p => p._status === 'vencida').length
  const totalVenceHoje = venceHojeList.length
  const totalPago = baseFiltered.filter(p => p._status === 'pago').reduce((s, p) => s + (parseFloat(p.valor_atualizado ?? p.valor_parcela) || 0), 0)

  const pendingByCompany = useMemo(() => {
    const map = new Map()
    baseFiltered.filter(p => p._status !== 'pago').forEach(p => {
      const company = p.empresa_nome || p.empresa || 'Outros'
      const val = (parseFloat(p.valor_atualizado ?? p.valor_parcela) || 0)
      map.set(company, (map.get(company) || 0) + val)
    })
    return Array.from(map.entries()).sort((a, b) => b[1] - a[1])
  }, [baseFiltered])

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

  const handlePrint = (withInstallments = true) => {
    if (isGeneratingPdf) return
    setShowInstallmentsInReport(withInstallments)
    setIsGeneratingPdf(true)
    setShowReportDropdown(false)

    // Opções do html2pdf
    const opt = {
      margin: [10, 10],
      filename: `Relatorio_Financeiro_${year || 'Geral'}.pdf`,
      image: { type: 'png' },
      html2canvas: { scale: 4, useCORS: true, letterRendering: true, logging: false },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait', compress: true },
      pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
    }

    // Pequeno delay para garantir que o estado de "gerando" foi processado (opcional)
    setTimeout(() => {
      const element = reportRef.current
      html2pdf().set(opt).from(element).save().then(() => {
        setIsGeneratingPdf(false)
      })
    }, 500)
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
              const count = c.key === 'todas' ? baseFiltered.length
                : c.key === 'pendente' ? baseFiltered.filter(p => p._status === 'pendente' || p._status === 'prorrogada').length
                  : baseFiltered.filter(p => p._status === c.key).length
              return (
                <button
                  key={c.key}
                  onClick={() => setCategoria(c.key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${categoria === c.key
                      ? 'bg-white shadow-sm text-g-200 border border-g-800'
                      : 'text-g-600 hover:text-g-400'
                    }`}
                >
                  {c.label} <span className="opacity-60">({count})</span>
                </button>
              )
            })}
          </div>
          <div className="flex items-center gap-2">
            <div className="flex gap-1 bg-g-850 border border-g-800 rounded-xl p-1">
              {[{ k: 'notas', label: 'Por Nota' }, { k: 'parcelas', label: 'Parcelas' }].map(({ k, label }) => (
                <button
                  key={k}
                  onClick={() => setViewMode(k)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${viewMode === k
                      ? 'bg-white shadow-sm text-g-200 border border-g-800'
                      : 'text-g-600 hover:text-g-400'
                    }`}
                >{label}</button>
              ))}
            </div>

            <div className="relative bg-g-850 border border-g-800 rounded-xl p-1">
              <button
                onClick={() => setShowReportDropdown(!showReportDropdown)}
                disabled={isGeneratingPdf}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold uppercase tracking-widest transition-all no-print ${isGeneratingPdf
                    ? 'bg-g-800 text-g-500 cursor-not-allowed'
                    : 'text-g-200 hover:text-white hover:bg-g-800 shadow-sm'
                  }`}
              >
                {isGeneratingPdf ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Printer className="w-3.5 h-3.5" />}
                {isGeneratingPdf ? 'Gerando...' : 'Relatório'}
                <ChevronDown className={`w-3 h-3 transition-transform ${showReportDropdown ? 'rotate-180' : ''}`} />
              </button>

              {showReportDropdown && !isGeneratingPdf && (
                <>
                  <div className="fixed inset-0 z-[80] no-print" onClick={() => setShowReportDropdown(false)} />
                  <div className="absolute right-0 mt-2 w-64 bg-g-900 border border-g-800 rounded-xl shadow-2xl z-[90] overflow-hidden animate-fade-in no-print">
                    <div className="p-2 flex flex-col gap-1">
                      <button
                        onClick={() => handlePrint(true)}
                        className="flex items-center gap-3 w-full p-3 hover:bg-g-850 rounded-lg transition-colors group text-left"
                      >
                        <div className="p-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg group-hover:bg-emerald-500 transition-colors">
                          <FileText className="w-4 h-4 text-emerald-500 group-hover:text-white" />
                        </div>
                        <div>
                          <p className="text-g-100 text-[11px] font-bold uppercase tracking-wider">Com Detalhamento</p>
                          <p className="text-g-600 text-[9px] mt-0.5">Relatório completo com parcelas</p>
                        </div>
                      </button>

                      <button
                        onClick={() => handlePrint(false)}
                        className="flex items-center gap-3 w-full p-3 hover:bg-g-850 rounded-lg transition-colors group text-left"
                      >
                        <div className="p-2 bg-blue-500/10 border border-blue-500/20 rounded-lg group-hover:bg-blue-500 transition-colors">
                          <Printer className="w-4 h-4 text-blue-500 group-hover:text-white" />
                        </div>
                        <div>
                          <p className="text-g-100 text-[11px] font-bold uppercase tracking-wider">Apenas Resumo</p>
                          <p className="text-g-600 text-[9px] mt-0.5">Listagem simplificada de notas</p>
                        </div>
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
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
          <div className="flex items-center gap-1.5">
            <span className="text-g-600 text-xs font-medium whitespace-nowrap">De</span>
            <input
              type="date"
              value={filterDataDe}
              onChange={e => setFilterDataDe(e.target.value)}
              className="py-2 px-3 bg-g-900 border border-g-800 rounded-lg text-g-400 text-sm focus:outline-none focus:border-g-100 transition-colors"
            />
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-g-600 text-xs font-medium whitespace-nowrap">Até</span>
            <input
              type="date"
              value={filterDataAte}
              onChange={e => setFilterDataAte(e.target.value)}
              className="py-2 px-3 bg-g-900 border border-g-800 rounded-lg text-g-400 text-sm focus:outline-none focus:border-g-100 transition-colors"
            />
          </div>
          {(filterDataDe || filterDataAte) && (
            <button
              onClick={() => { setFilterDataDe(''); setFilterDataAte('') }}
              className="p-2 rounded-lg text-g-600 hover:text-g-300 hover:bg-g-850 transition-colors"
              title="Limpar filtro de data"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* View: Por Nota Fiscal */}
      {!loading && viewMode === 'notas' && (
        <div className="flex flex-col gap-3">
          {nfGroupsByMonth.length === 0 ? (
            <div className="card flex items-center justify-center h-32 gap-2 text-g-600 text-sm">
              <Search className="w-4 h-4" /> Nenhuma nota nesta categoria
            </div>
          ) : nfGroupsByMonth.map(mGroup => (
            <div key={mGroup.month} className="flex flex-col gap-3">
              {/* Cabeçalho do Mês */}
              <div className="flex items-center gap-3 mb-2">
                <span className="text-g-500 text-[10px] uppercase font-bold tracking-[0.2em] whitespace-nowrap">
                  {mGroup.monthName}
                </span>
                <div className="h-px w-full bg-g-800/60" />
              </div>

              {/* Lista de Notas do Mês */}
              {mGroup.invoices.map(g => {
                const expanded = expandedNfs.has(g.nfKey)
                const toggleExpand = () => setExpandedNfs(prev => {
                  const next = new Set(prev)
                  expanded ? next.delete(g.nfKey) : next.add(g.nfKey)
                  return next
                })
                const statusColor = g.hasVencida ? 'border-l-red-500'
                  : g.hasVenceHoje ? 'border-l-orange-400'
                    : g.hasProrrogada ? 'border-l-purple-500'
                      : g.allPago ? 'border-l-emerald-500'
                        : 'border-l-blue-500'

                return (
                  <div key={`${mGroup.month}-${g.nfKey}`} className={`card border-l-4 ${statusColor} overflow-hidden mb-1`}>
                    {/* Header da NF */}
                    <button
                      onClick={toggleExpand}
                      className="w-full flex items-center gap-3 p-4 hover:bg-g-850 transition-colors text-left"
                    >
                      <div className="flex-1 grid grid-cols-[100px_140px_1.5fr_1.2fr_110px_110px_110px_auto] gap-x-4 items-center min-w-0">
                        {/* Vencimento */}
                        <div>
                          <span className="text-g-600 text-[10px] uppercase font-bold tracking-widest block mb-0.5">Vencimento</span>
                          <div className="flex flex-col leading-none">
                            <span className="text-emerald-600 text-lg font-black font-mono tracking-tighter">
                              {g.nextVencimento ? dateBR(g.nextVencimento).slice(0, 5) : '—'}
                            </span>
                            <span className="text-emerald-600/60 text-xs font-mono mt-0.5">
                              {g.nextVencimento ? `/${dateBR(g.nextVencimento).slice(6)}` : ''}
                            </span>
                          </div>
                        </div>

                        {/* Placas */}
                        <div className="flex flex-wrap gap-1.5">
                          {g.placasList.map(p => (
                            <span key={p} className="px-2 py-1 bg-g-800/40 border border-g-700/50 rounded-md font-mono text-sm font-black text-g-400 shadow-sm">
                              {p}
                            </span>
                          ))}
                        </div>

                        {/* Fornecedor */}
                        <div className="min-w-0">
                          <span className="text-g-200 text-sm font-bold truncate block">{g.fornecedor || '—'}</span>
                          <span className="text-g-500 text-xs uppercase tracking-wider block truncate font-medium">
                            {g.osList.length > 1 ? `${g.osList.length} Ordens de Serviço` : g.osList[0] || 'Sem OS'}
                          </span>
                        </div>

                        {/* NF + Parcelas */}
                        <div>
                          <span className="text-g-500 text-sm truncate block font-medium">
                            NF <span className="text-g-200 font-black">{g.numero_nf || '—'}</span>
                          </span>
                          <span className="text-g-600 text-xs font-mono block">
                            {g.countPago} / {g.countTotal} parcelas pagas
                          </span>
                        </div>

                        {/* Valor Parcela Atual */}
                        <div>
                          <span className="text-g-600 text-[10px] uppercase font-bold tracking-tighter block mb-0.5">Parcela Atual</span>
                          <span className="text-g-400 text-base font-mono font-black block">
                            {g.nextValor > 0 ? brl(g.nextValor) : '—'}
                          </span>
                        </div>

                        {/* Valor Total NF */}
                        <div>
                          <span className="text-g-600 text-[10px] uppercase font-bold tracking-tighter block mb-0.5">Total da NF</span>
                          <span className="text-g-400 text-base font-mono font-black block">{brl(g.totalGeral)}</span>
                        </div>

                        {/* Status */}
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-bold px-3 py-1 rounded-full border shadow-sm ${g.hasVencida ? 'bg-red-500/10 text-red-500 border-red-500/30'
                              : g.hasVenceHoje ? 'bg-orange-500/10 text-orange-500 border-orange-500/30'
                                : g.hasProrrogada ? 'bg-purple-500/10 text-purple-500 border-purple-500/30'
                                  : g.allPago ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/30'
                                    : 'bg-blue-500/10 text-blue-500 border-blue-500/30'
                            }`}>
                            {g.hasVencida ? 'Vencida' : g.hasVenceHoje ? 'Vence hoje' : g.hasProrrogada ? 'Prorrogada' : g.allPago ? 'Pago' : 'Pendente'}
                          </span>
                        </div>

                        {/* Chevron */}
                        <div className="flex justify-end">
                          {expanded
                            ? <ChevronUp className="w-4 h-4 text-g-600" />
                            : <ChevronDown className="w-4 h-4 text-g-600" />}
                        </div>
                      </div>
                    </button>

                    {/* Parcelas expandidas (apenas as do mês corrente) */}
                    {expanded && (
                      <div className="border-t border-g-800">
                        <table className="w-full">
                          <thead className="bg-g-850">
                            <tr>
                              <th className="th th-left text-[10px]">Veículo</th>
                              <th className="th th-left text-[10px]">Parcela</th>
                              <th className="th th-left text-[10px]">Vencimento</th>
                              <th className="th text-[10px]">Valor</th>
                              <th className="th text-[10px]">Status</th>
                              <th className="th th-left text-[10px]">Forma</th>
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
                                  <td className="td td-left text-xs font-mono font-bold text-g-500">
                                    {p.placa}
                                  </td>
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
                                  <td className="td td-left text-xs text-g-500 uppercase font-medium">
                                    {p.forma_pgto || '—'}
                                  </td>
                                  <td className="td td-left text-xs tabular-nums">
                                    {previsao ? (
                                      <span className={`flex items-center gap-1 ${prevAtrasada ? 'text-red-500 font-medium' : 'text-g-500'}`}>
                                        {dateBR(previsao)}{prevAtrasada && <AlertTriangle className="w-3 h-3" />}
                                      </span>
                                    ) : '—'}
                                  </td>
                                  <td className="td td-right !pr-1.5" onClick={e => e.stopPropagation()}>
                                    {p._isSintetica ? (
                                      <div className="flex items-center justify-end gap-1">
                                        <span className="text-[10px] text-g-700 italic px-1">via NF</span>
                                      </div>
                                    ) : (
                                      <div className="flex items-center justify-end gap-1">
                                        {p.status_pagamento !== 'Pago' && (
                                          <button
                                            onClick={() => setModalProrrogar(p)}
                                            className="p-1 rounded bg-g-850 border border-g-800 text-g-600 hover:text-purple-400 transition-colors"
                                            title="Prorrogar"
                                          >
                                            <CalendarClock className="w-3 h-3" />
                                          </button>
                                        )}
                                      </div>
                                    )}
                                  </td>
                                </tr>
                              )
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Subtotal do Mês */}
              <div className="flex items-center justify-end p-4 bg-g-900/50 rounded-xl border border-g-800/50 mt-1 mb-8 gap-10">
                <div className="text-right">
                  <span className="text-g-600 text-[10px] block uppercase font-bold mb-0.5">Total {mGroup.monthName}</span>
                  <span className="font-mono font-bold text-g-200 text-xl tabular-nums">
                    {brl(mGroup.subtotal)}
                  </span>
                </div>
              </div>
            </div>
          ))
          }
          {nfGroupsByMonth.length > 0 && (
            <div className="card p-6 flex items-center justify-end gap-10 bg-g-900 border-t-4 border-t-emerald-600">
              <span className="text-g-500 text-sm font-bold uppercase tracking-[0.2em]">
                Total Geral do Ano
              </span>
              <div className="text-right">
                <span className="text-g-600 text-[10px] block uppercase font-bold mb-0.5">Soma de todos os meses</span>
                <span className="font-mono font-bold text-emerald-600 text-3xl tabular-nums">
                  {brl(nfGroupsByMonth.reduce((s, m) => s + m.subtotal, 0))}
                </span>
              </div>
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
              <table className="w-full table-fixed">
                <thead className="bg-g-850 border-b border-g-800">
                  <tr>
                    {[
                      { key: 'placa', label: 'Placa', cls: 'th-left w-[8%] !pl-1.5' },
                      { key: 'id_ord_serv', label: 'Nº OS', cls: 'th-left w-[12%]' },
                      { key: 'empresa_nome', label: 'Empresa', cls: 'th-left w-[8%]' },
                      { key: 'fornecedor', label: 'Fornecedor', cls: 'th-left w-[18%]' },
                      { key: 'nota', label: 'Nota Fiscal', cls: 'th-left w-[8%]' },
                      { key: 'parcela_atual', label: 'Parcela', cls: 'th-left w-[6%]' },
                      { key: 'data_vencimento', label: 'Vencimento', cls: 'th-left w-[8%]' },
                      { key: 'valor_parcela', label: 'Valor', cls: 'th-right w-[9%]' },
                      { key: 'status_pagamento', label: 'Status', cls: 'th-center w-[8%]' },
                      { key: 'data_prevista_pagamento', label: 'Previsão Pgto', cls: 'th-left w-[9%]' }
                    ].map(({ key, label, cls }, i) => (
                      <th key={key} onClick={() => toggleSort(key)} className={`th ${cls} cursor-pointer select-none hover:text-g-300 transition-colors truncate`}>
                        {label}<SortIcon col={key} />
                      </th>
                    ))}
                    <th className="th th-right w-[10%] !pr-1.5">Ações</th>
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
                    const rowBg = p._status === 'vencida' ? 'bg-red-50/20'
                      : p._status === 'vence_hoje' ? 'bg-orange-50/20'
                        : p._status === 'prorrogada' ? 'bg-purple-50/10'
                          : ''
                    return (
                      <tr
                        key={p.id}
                        onClick={() => setModalDetalhe(p)}
                        className={`border-b border-g-800 hover:bg-g-850 transition-colors cursor-pointer ${rowBg}`}
                      >
                        <td className="td td-left !pl-1.5 font-mono font-bold text-g-200">{p.placa}</td>
                        <td className="td td-left text-g-600 font-mono text-[11px] truncate">{p.id_ord_serv || '—'}</td>
                        <td className="td td-left text-xs text-g-500 tabular-nums" title={p.empresa_nome || ''}>{empresaSigla(p.empresa, p.empresa_nome)}</td>
                        <td className="td td-left text-g-500 truncate" title={p.fornecedor_os && p.fornecedor_os !== p.fornecedor ? `OS: ${p.fornecedor_os}` : ''}>
                          <span className="flex items-center gap-1 overflow-hidden">
                            <span className="truncate">{p.fornecedor || '—'}</span>
                            {p.fornecedor_os && p.fornecedor && p.fornecedor_os !== p.fornecedor && (
                              <span className="text-[9px] text-amber-500 bg-amber-500/10 border border-amber-500/30 rounded px-1 flex-shrink-0">≠OS</span>
                            )}
                          </span>
                        </td>
                        <td className="td td-left text-g-500 font-mono text-xs">{p.nota || '—'}</td>
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
                        <td className="td td-right font-mono font-semibold text-g-300 tabular-nums text-sm">
                          {brl(p.valor_atualizado ?? p.valor_parcela)}
                        </td>
                        <td className="td td-center"><FinBadge status={p._status} /></td>
                        <td className="td td-left text-xs tabular-nums">
                          {previsao ? (
                            <span className={`flex items-center gap-1 ${prevAtrasada ? 'text-red-500 font-medium' : 'text-g-500'}`}>
                              {dateBR(previsao)}
                              {prevAtrasada && <AlertTriangle className="w-3 h-3" />}
                            </span>
                          ) : '—'}
                        </td>
                        <td className="td td-right !pr-1.5" onClick={e => e.stopPropagation()}>
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
                  const somaPago = filtered.filter(p => p._status === 'pago').reduce((s, p) => s + (parseFloat(p.valor_atualizado ?? p.valor_parcela) || 0), 0)
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

      {/* Elemento oculto para geração do PDF */}
      <div style={{ position: 'absolute', left: '-9999px', top: '-9999px' }}>
        <div ref={reportRef} className="p-6 bg-white text-black w-[190mm]">
          {/* Header do PDF */}
          <div className="flex items-center justify-between mb-8 border-b-2 border-g-100 pb-4">
            <div className="flex items-center gap-4">
              <img src="/logo.png" alt="TKJ" className="h-16 w-auto object-contain" />
              <div>
                <h1 className="text-2xl font-bold text-g-100 uppercase tracking-tight">Relatório Financeiro</h1>
                <p className="text-sm text-g-600 font-medium">Manutenção · Exercício {year}</p>
                {(filterDataDe || filterDataAte) && (
                  <p className="text-xs text-g-600 font-medium mt-0.5">
                    {filterDataDe && filterDataAte
                      ? `Período: ${filterDataDe.split('-').reverse().join('/')} a ${filterDataAte.split('-').reverse().join('/')}`
                      : filterDataDe
                        ? `A partir de ${filterDataDe.split('-').reverse().join('/')}`
                        : `Até ${filterDataAte.split('-').reverse().join('/')}`}
                  </p>
                )}
              </div>
            </div>
            <div className="text-right">
              <p className="text-[10px] text-g-600 font-black uppercase tracking-widest mb-1">Data e Hora de Geração</p>
              <p className="text-sm font-bold text-g-100 font-mono">
                {new Date().toLocaleDateString('pt-BR')} {new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>
          </div>

          {/* Resumo Financeiro (KPIs) */}
          <div className="grid grid-cols-4 gap-4 mb-8 items-start">
            <div className="col-span-2 border border-g-800 rounded-xl p-4 bg-amber-50/10 min-h-[100px]">
              <p className="text-g-600 text-[10px] uppercase font-black tracking-wider mb-1">Total Pendente Geral</p>
              <p className="text-2xl font-mono font-bold text-g-100">{brl(totalPendente)}</p>
            </div>
            <div className="col-span-2 border border-g-800 rounded-xl p-4 bg-emerald-50/5 min-h-[100px]">
              <p className="text-g-600 text-[10px] uppercase font-black tracking-wider mb-2">Pendente por Empresa</p>
              <div className="space-y-2">
                {pendingByCompany.length > 0 ? pendingByCompany.map(([name, val]) => (
                  <div key={name} className="flex justify-between items-start gap-2 text-[11px]">
                    <span className="text-emerald-900 font-black uppercase leading-tight flex-1">{name}</span>
                    <span className="font-mono font-black text-emerald-900 whitespace-nowrap leading-tight">{brl(val)}</span>
                  </div>
                )) : (
                  <p className="text-xs text-g-600 italic">Nenhuma pendência</p>
                )}
              </div>
            </div>
          </div>

          {/* Listagem por Meses */}
          {nfGroupsByMonth.map(mGroup => (
              <div key={mGroup.month} className="mb-6 break-inside-avoid">
                <div className="flex items-center gap-4 mb-3">
                  <span className="text-g-100 text-lg uppercase font-black tracking-widest">
                    {mGroup.monthName}
                  </span>
                  <div className="h-px flex-1 bg-g-100/20" />
                  <div className="bg-g-950 px-4 py-1.5 rounded-lg border border-g-800">
                    <span className="text-g-200 text-xs font-mono font-bold">Subtotal: {brl(mGroup.subtotal)}</span>
                  </div>
                </div>

                <div className="flex flex-col gap-5">
                  {mGroup.invoices.map(g => (
                    <div key={g.nfKey} className="relative pt-2">
                      {/* Empresa Label (Estilo solicitado: texto acima da borda) */}
                      <div className="absolute -top-1 left-2 bg-white px-2 z-10">
                        <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{g.empresa}</span>
                      </div>

                      <div className="border border-g-800 rounded-xl overflow-hidden bg-white shadow-md">
                        {/* NF Header */}
                        <div className="bg-g-850/40 px-4 py-2 border-b border-g-800">
                          <div className="grid grid-cols-[85px_95px_1fr_85px_95px_80px] gap-2 items-center">
                            <div className="min-h-[40px] flex flex-col justify-center">
                              <span className="text-[10px] text-g-600 uppercase font-black block mb-0.5">Vencimento</span>
                              <span className="text-sm font-mono font-bold text-g-100">{g.nextVencimento ? dateBR(g.nextVencimento) : '—'}</span>
                            </div>
                            <div className="min-h-[40px] flex flex-col justify-center">
                              <span className="text-[10px] text-g-600 uppercase font-black block mb-1">Placas</span>
                              <div className="flex flex-wrap gap-1">
                                {g.placasList.map(p => (
                                  <span key={p} className="text-[11px] font-mono font-black text-g-100 bg-g-100/5 px-1.5 py-0.5 inline-flex items-center justify-center rounded border border-g-100/10 leading-none">{p}</span>
                                ))}
                              </div>
                            </div>
                            <div className="min-h-[40px] flex flex-col justify-center overflow-hidden">
                              <span className="text-[10px] text-g-600 uppercase font-black block mb-0.5">Fornecedor</span>
                              <p className="text-[11px] font-black text-g-100 uppercase tracking-tight truncate pb-0.5">
                                {shortenProviderName(g.fornecedor, 14)}
                              </p>
                            </div>
                            <div className="min-h-[40px] flex flex-col justify-center">
                              <span className="text-[10px] text-g-600 uppercase font-black block mb-0.5">NF / Parcelas</span>
                              <span className="text-xs font-bold block text-g-100">NF {g.numero_nf || '—'}</span>
                              <span className="text-[9px] text-g-600 font-mono font-bold">{g.countPago}/{g.countTotal} pagas</span>
                            </div>
                            <div className="min-h-[40px] flex flex-col justify-center">
                              <span className="text-[10px] text-g-600 uppercase font-black block mb-0.5">Total NF</span>
                              <span className="text-sm font-mono font-black text-g-100">{brl(g.totalGeral)}</span>
                            </div>
                            <div className="min-h-[40px] flex items-center justify-end">
                              <div className={`text-[9px] font-black px-2 py-1 rounded border inline-flex items-center justify-center uppercase tracking-wider leading-none ${g.hasVencida ? 'bg-red-50 text-red-600 border-red-200'
                                  : g.hasVenceHoje ? 'bg-orange-50 text-orange-600 border-orange-200'
                                    : g.hasProrrogada ? 'bg-purple-50 text-purple-600 border-purple-200'
                                      : g.allPago ? 'bg-emerald-50 text-emerald-600 border-emerald-200'
                                        : 'bg-blue-50 text-blue-600 border-blue-200'
                                }`}>
                                {g.hasVencida ? 'Vencida' : g.hasVenceHoje ? 'Vence hoje' : g.hasProrrogada ? 'Prorrogada' : g.allPago ? 'Pago' : 'Pendente'}
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Parcelas Table */}
                        {showInstallmentsInReport && (
                          <table className="w-full text-[11px]">
                            <thead className="bg-g-950/10">
                              <tr>
                                <th className="px-4 py-1.5 text-left text-g-600 font-black uppercase tracking-tighter border-b border-g-800">Veículo</th>
                                <th className="px-4 py-1.5 text-left text-g-600 font-black uppercase tracking-tighter border-b border-g-800">Sistema</th>
                                <th className="px-4 py-1.5 text-left text-g-600 font-black uppercase tracking-tighter border-b border-g-800">Parcela</th>
                                <th className="px-4 py-1.5 text-left text-g-600 font-black uppercase tracking-tighter border-b border-g-800">Vencimento</th>
                                <th className="px-4 py-1.5 text-right text-g-600 font-black uppercase tracking-tighter border-b border-g-800">Valor</th>
                                <th className="px-4 py-1.5 text-left text-g-600 font-black uppercase tracking-tighter border-b border-g-800">Forma</th>
                                <th className="px-4 py-1.5 text-center text-g-600 font-black uppercase tracking-tighter border-b border-g-800">Status</th>
                              </tr>
                            </thead>
                            <tbody>
                              {g.parcelas.map(p => (
                                <tr key={p.id} className="border-b border-g-100/5 last:border-0">
                                  <td className="px-4 py-1.5 font-mono font-black text-g-100">{p.placa}</td>
                                  <td className="px-4 py-1.5 text-g-600 font-bold uppercase text-[9px]">{p.sistema || '—'}</td>
                                  <td className="px-4 py-1.5 text-g-200 font-medium">
                                    {p.parcela_atual && p.parcela_total ? `${p.parcela_atual}/${p.parcela_total}` : '—'}
                                  </td>
                                  <td className="px-4 py-1.5 text-g-200 font-medium">
                                    {p.prorrogada && <span className="block text-[8px] text-purple-600 font-bold leading-none mb-0.5">Venc. Orig: {dateBR(p.data_vencimento_original)}</span>}
                                    {dateBR(p.data_vencimento)}
                                  </td>
                                  <td className="px-4 py-1.5 text-right font-mono font-black text-sm text-g-100">
                                    {p.prorrogada && <span className="block text-[9px] text-purple-600 font-bold leading-none mb-0.5">Orig: {brl(p.valor_parcela)}</span>}
                                    {brl(p.valor_atualizado ?? p.valor_parcela)}
                                  </td>
                                  <td className="px-4 py-1.5 text-g-200 font-medium">{p.forma_pgto || '—'}</td>
                                  <td className="px-4 py-1.5">
                                    <div className="flex justify-center items-center h-full">
                                      <span className={`w-20 h-5 rounded text-[9px] font-black tracking-tighter flex items-center justify-center border leading-none ${p._status === 'pago' ? 'text-emerald-700 bg-emerald-50 border-emerald-100'
                                          : p._status === 'vencida' ? 'text-red-700 bg-red-50 border-red-100'
                                            : p._status === 'prorrogada' ? 'text-purple-700 bg-purple-50 border-purple-100'
                                              : 'text-blue-700 bg-blue-50 border-blue-100'
                                        }`}>
                                        {p._status.toUpperCase()}
                                      </span>
                                    </div>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {/* Footer do Relatório (Final) */}
            <div className="mt-8 pt-4 border-t-2 border-g-100 flex justify-between items-end">
              <div className="text-left" />
              <div className="text-right">
                <p className="text-xs text-g-600 font-black uppercase tracking-widest mb-1">Total Geral do Exercício</p>
                <p className="text-3xl font-mono font-black text-emerald-600 tracking-tighter">
                  {brl(nfGroupsByMonth.reduce((s, m) => s + m.subtotal, 0))}
                </p>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-g-800 text-center">
              <p className="text-[9px] text-g-600 font-bold uppercase tracking-[0.3em]">Relatório Consultivo | TKJ Gerenciamento 2026</p>
            </div>
        </div>
      </div>
    </div>
  )
}

// ════════════════════════════════════════════════════════════════════
// ANÁLISE DE INTERVALOS DE SERVIÇO
// ════════════════════════════════════════════════════════════════════
const SISTEMAS_INTERVALO = [
  { key: 'Pneu',    label: 'Pneu',    sub: 'Troca de pneus' },
  { key: 'Freio',   label: 'Freio',   sub: 'Pastilha · disco · pinça' },
  { key: 'Revisão', label: 'Revisão', sub: 'Óleo · filtros' },
]

const POSICOES_PNEU = ['DIANTEIRO', 'TRASEIRO', 'DIANTEIRO + TRASEIRO']

function RodizioModal({ placa, specs, conjuntos = [], onClose, onSaved }) {
  const first = conjuntos[0]
  const [form, setForm] = useState({
    placa,
    data: '',
    km: '',
    posicao_anterior: first?.posicao_atual || 'TRASEIRO',
    posicao_nova: 'DIANTEIRO',
    espec_pneu: first?.espec || specs[0] || '',
    marca_pneu: first?.marca || '',
    qtd: first?.qtd || 2,
    os_ref: first?.os_ref || '',
    observacao: '',
  })
  const [saving, setSaving] = useState(false)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleConjuntoSelect = os_ref => {
    const c = conjuntos.find(c => c.os_ref === os_ref)
    if (c) setForm(f => ({ ...f, os_ref, posicao_anterior: c.posicao_atual || f.posicao_anterior, espec_pneu: c.espec || f.espec_pneu, marca_pneu: c.marca || f.marca_pneu, qtd: c.qtd || f.qtd }))
    else set('os_ref', os_ref)
  }

  const handleSubmit = async e => {
    e.preventDefault()
    setSaving(true)
    try {
      await createPneuRodizio({
        ...form,
        km:  form.km  ? Number(form.km)  : null,
        qtd: form.qtd ? Number(form.qtd) : 2,
      })
      onSaved()
      onClose()
    } catch (err) {
      console.error('Erro ao criar rodízio:', err)
    } finally {
      setSaving(false)
    }
  }

  return createPortal(
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="bg-g-900 px-6 py-4 rounded-t-2xl flex items-center justify-between">
          <div className="flex items-center gap-2">
            <RotateCcw className="w-4 h-4 text-violet-400" />
            <span className="text-g-100 font-semibold text-sm">Registrar Rodízio / Movimentação</span>
          </div>
          <span className="font-mono font-bold text-violet-400 text-sm">{placa}</span>
        </div>
        <form onSubmit={handleSubmit} className="p-5 flex flex-col gap-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-g-600 text-[10px] font-bold uppercase tracking-wider block mb-1">Data *</label>
              <input type="date" required value={form.data} onChange={e => set('data', e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300" />
            </div>
            <div>
              <label className="text-g-600 text-[10px] font-bold uppercase tracking-wider block mb-1">KM no momento</label>
              <input type="number" value={form.km} onChange={e => set('km', e.target.value)} placeholder="ex: 47489"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300" />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <label className="text-g-600 text-[10px] font-bold uppercase tracking-wider block mb-1">Posição anterior *</label>
              <select value={form.posicao_anterior} onChange={e => set('posicao_anterior', e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300">
                {POSICOES_PNEU.map(p => <option key={p}>{p}</option>)}
              </select>
            </div>
            <ArrowRight className="w-5 h-5 text-violet-400 mt-5 shrink-0" />
            <div className="flex-1">
              <label className="text-g-600 text-[10px] font-bold uppercase tracking-wider block mb-1">Nova posição *</label>
              <select value={form.posicao_nova} onChange={e => set('posicao_nova', e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300">
                {POSICOES_PNEU.map(p => <option key={p}>{p}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <label className="text-g-600 text-[10px] font-bold uppercase tracking-wider block mb-1">Especificação</label>
              {specs.length > 0
                ? <select value={form.espec_pneu} onChange={e => set('espec_pneu', e.target.value)}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300">
                    {specs.map(s => <option key={s}>{s}</option>)}
                    <option value="">Outra</option>
                  </select>
                : <input value={form.espec_pneu} onChange={e => set('espec_pneu', e.target.value)} placeholder="ex: 225/75R16C"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300" />
              }
            </div>
            <div>
              <label className="text-g-600 text-[10px] font-bold uppercase tracking-wider block mb-1">Qtd</label>
              <input type="number" min="1" value={form.qtd} onChange={e => set('qtd', e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-g-600 text-[10px] font-bold uppercase tracking-wider block mb-1">Marca</label>
              <input value={form.marca_pneu} onChange={e => set('marca_pneu', e.target.value)} placeholder="ex: APOLLO"
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300" />
            </div>
            <div>
              <label className="text-g-600 text-[10px] font-bold uppercase tracking-wider block mb-1">Conjunto (OS origem) *</label>
              {conjuntos.length > 0
                ? <select required value={form.os_ref} onChange={e => handleConjuntoSelect(e.target.value)}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300">
                    <option value="">— Selecionar —</option>
                    {conjuntos.map(c => (
                      <option key={c.os_ref} value={c.os_ref}>
                        {c.os_ref} · {c.posicao_atual} · {c.espec || ''} {c.marca ? `· ${c.marca}` : ''}
                      </option>
                    ))}
                  </select>
                : <input value={form.os_ref} onChange={e => set('os_ref', e.target.value)} placeholder="ex: OS-2025-0008"
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-300" />
              }
            </div>
          </div>
          <div>
            <label className="text-g-600 text-[10px] font-bold uppercase tracking-wider block mb-1">Observação</label>
            <textarea value={form.observacao} onChange={e => set('observacao', e.target.value)} rows={2}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-violet-300" />
          </div>
          <div className="flex justify-end gap-3 pt-1">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-g-500 hover:text-g-300 transition-colors">Cancelar</button>
            <button type="submit" disabled={saving}
              className="px-5 py-2 bg-violet-600 text-white text-sm font-semibold rounded-lg hover:bg-violet-700 disabled:opacity-50 flex items-center gap-2 transition-colors">
              {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RotateCcw className="w-3.5 h-3.5" />}
              Registrar
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  )
}

function IntervalosSection() {
  const [sistema,       setSistema]      = useState('Pneu')
  const [data,          setData]         = useState(null)
  const [loading,       setLoading]      = useState(false)
  const [expanded,      setExpanded]     = useState(new Set())
  const [rodizioModal,  setRodizioModal] = useState(null)  // { placa, specs }

  const load = useCallback(() => {
    setLoading(true)
    getIntervalosAnalysis(sistema)
      .then(setData)
      .finally(() => setLoading(false))
  }, [sistema])

  useEffect(() => { load() }, [load])

  const toggleExpand = placa =>
    setExpanded(s => { const n = new Set(s); n.has(placa) ? n.delete(placa) : n.add(placa); return n })

  const fleet = data?.fleet
  const porPlaca = data?.por_placa || []

  // Agrupamento por medida — agregado de por_medida de cada placa (servidor já calcula intervals por spec)
  const byMedida = useMemo(() => {
    if (sistema !== 'Pneu' || !porPlaca.length) return []
    const map = {}
    porPlaca.forEach(veh => {
      const medidas = veh.por_medida || []
      if (medidas.length) {
        medidas.forEach(m => {
          if (!map[m.espec]) map[m.espec] = { spec: m.espec, veiculos: new Set(), n_eventos: 0, total_pneus: 0, km_diffs: [] }
          map[m.espec].veiculos.add(veh.placa)
          map[m.espec].n_eventos += m.n_eventos
          map[m.espec].total_pneus += m.total_pneus || 0
          ;(m.conjuntos || []).forEach(c => { if (c.delta_km) map[m.espec].km_diffs.push(c.delta_km) })
        })
      }
    })
    return Object.values(map)
      .map(r => ({
        spec:        r.spec,
        n_veiculos:  r.veiculos.size,
        n_eventos:   r.n_eventos,
        total_pneus: r.total_pneus || null,
        avg_km:      r.km_diffs.length ? Math.round(r.km_diffs.reduce((a,b)=>a+b,0)/r.km_diffs.length) : null,
        min_km:      r.km_diffs.length ? Math.min(...r.km_diffs) : null,
        max_km:      r.km_diffs.length ? Math.max(...r.km_diffs) : null,
      }))
      .sort((a, b) => b.n_eventos - a.n_eventos)
  }, [sistema, porPlaca])

  const EventTable = ({ eventos, total, isPneu, avgKm, kms, dias, onDeleteRodizio }) => (
    <table className="w-full text-xs min-w-[640px]">
      <thead>
        <tr className="bg-g-900">
          <th className="text-left text-g-600 font-semibold py-2 px-4">#</th>
          <th className="text-left text-g-600 font-semibold py-2 px-3">Data</th>
          <th className="text-right text-g-600 font-semibold py-2 px-3">KM</th>
          <th className="text-right text-g-600 font-semibold py-2 px-3">∆ KM</th>
          <th className="text-right text-g-600 font-semibold py-2 px-3">∆ Dias</th>
          {isPneu && <th className="text-left text-g-600 font-semibold py-2 px-3">Tipo</th>}
          {isPneu && <th className="text-left text-g-600 font-semibold py-2 px-3">Posição</th>}
          {isPneu && <th className="text-left text-g-600 font-semibold py-2 px-3">Marca</th>}
          {isPneu && <th className="text-center text-g-600 font-semibold py-2 px-3">Qtd</th>}
          {!isPneu && <th className="text-left text-g-600 font-semibold py-2 px-3">Serviço</th>}
          <th className="text-left text-g-600 font-semibold py-2 px-3">OS / Ref</th>
        </tr>
      </thead>
      <tbody>
        {eventos.map((ev, i) => {
          const isRodizio = ev.tipo_evento === 'rodizio'
          const isAlert   = !isRodizio && ev.delta_km != null && avgKm && ev.delta_km < avgKm * 0.8
          const rowBg     = isRodizio ? 'bg-violet-50/70 border-violet-100'
                          : isAlert   ? 'bg-amber-50/60'
                          : i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'
          return (
            <tr key={i} className={`border-b ${rowBg}`}>
              <td className="py-2 px-4 text-g-600 font-mono">
                {isRodizio
                  ? <RotateCcw className="w-3 h-3 text-violet-400 inline" />
                  : `${i + 1}/${total}`}
              </td>
              <td className="py-2 px-3 text-g-400 font-mono whitespace-nowrap">{ev.data ? dateBR(ev.data) : '—'}</td>
              <td className="py-2 px-3 text-right font-mono text-g-300 whitespace-nowrap">{ev.km != null ? num(ev.km) + ' km' : '—'}</td>
              <td className="py-2 px-3 text-right font-mono whitespace-nowrap">
                {ev.delta_km != null
                  ? <span className={`font-bold ${isRodizio ? 'text-violet-500' : isAlert ? 'text-amber-600' : 'text-emerald-600'}`}>+{num(ev.delta_km)}</span>
                  : <span className="text-g-700">—</span>}
              </td>
              <td className="py-2 px-3 text-right font-mono whitespace-nowrap">
                {ev.delta_dias != null
                  ? <span className={`font-bold ${isRodizio ? 'text-violet-400' : 'text-blue-600'}`}>+{ev.delta_dias}d</span>
                  : <span className="text-g-700">—</span>}
              </td>
              {isPneu && (
                <td className="py-2 px-3 text-[11px]">
                  {isRodizio
                    ? <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-violet-100 text-violet-700">Rodízio</span>
                    : <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${ev.categoria === 'Compra' ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-g-500'}`}>{ev.categoria || '—'}</span>
                  }
                </td>
              )}
              {isPneu && (
                <td className="py-2 px-3 text-[11px] whitespace-nowrap">
                  {isRodizio && ev.posicao_anterior
                    ? <span className="flex items-center gap-1 text-violet-600">
                        <span className="opacity-70">{ev.posicao_anterior}</span>
                        <ArrowRight className="w-3 h-3" />
                        <span className="font-semibold">{ev.posicao_pneu}</span>
                      </span>
                    : <span className="text-g-400">{ev.posicao_pneu || '—'}</span>
                  }
                </td>
              )}
              {isPneu && <td className="py-2 px-3 text-g-500 text-[11px]">{ev.marca_pneu || '—'}</td>}
              {isPneu && <td className="py-2 px-3 text-center text-g-500">{ev.qtd_pneu ?? (ev.qtd_itens ?? '—')}</td>}
              {!isPneu && <td className="py-2 px-3 text-g-400 max-w-[180px] truncate" title={ev.servico}>{ev.servico || '—'}</td>}
              <td className="py-2 px-3 font-mono text-g-600 text-[10px]">
                <div className="flex items-center gap-1">
                  <span>{ev.numero_os || '—'}</span>
                  {isRodizio && onDeleteRodizio && (
                    <button onClick={() => onDeleteRodizio(ev.id_rodizio)} title="Remover rodízio"
                      className="ml-1 text-violet-300 hover:text-red-500 transition-colors">
                      <X className="w-3 h-3" />
                    </button>
                  )}
                </div>
              </td>
            </tr>
          )
        })}
      </tbody>
      {kms?.length > 0 && (
        <tfoot>
          <tr className="bg-g-900/50 border-t border-g-800">
            <td colSpan={3} className="py-2 px-4 text-g-600 text-[10px] font-semibold uppercase tracking-wide">Resumo</td>
            <td className="py-2 px-3 text-right">
              <span className="text-[10px] text-g-600 block">min / médio / máx</span>
              <span className="font-mono text-g-300 text-[11px]">
                {num(Math.min(...kms))} / <strong className="text-emerald-500">{num(Math.round(kms.reduce((a,b)=>a+b,0)/kms.length))}</strong> / {num(Math.max(...kms))} km
              </span>
            </td>
            <td className="py-2 px-3 text-right">
              {dias?.length > 0 && (
                <>
                  <span className="text-[10px] text-g-600 block">min / médio / máx</span>
                  <span className="font-mono text-g-300 text-[11px]">
                    {Math.min(...dias)} / <strong className="text-blue-400">{Math.round(dias.reduce((a,b)=>a+b,0)/dias.length)}</strong> / {Math.max(...dias)} d
                  </span>
                </>
              )}
            </td>
            <td colSpan={isPneu ? 5 : 2} />
          </tr>
        </tfoot>
      )}
    </table>
  )

  // Tabela de conjuntos de pneus com fases de vida (Pneu only)
  const ConjuntoTable = ({ conjuntos, avgKm, onDeleteRodizio }) => (
    <table className="w-full text-xs min-w-[860px]">
      <thead>
        <tr className="bg-g-900">
          <th className="text-left text-g-600 font-semibold py-2 px-4 w-32">OS / Ref</th>
          <th className="text-left text-g-600 font-semibold py-2 px-3">Data</th>
          <th className="text-right text-g-600 font-semibold py-2 px-3">KM Entrada</th>
          <th className="text-right text-g-600 font-semibold py-2 px-3">KM Rodado</th>
          <th className="text-left text-g-600 font-semibold py-2 px-3">Pos. Inicial</th>
          <th className="text-left text-g-600 font-semibold py-2 px-3">Pos. Atual</th>
          <th className="text-left text-g-600 font-semibold py-2 px-3">Marca</th>
          <th className="text-left text-g-600 font-semibold py-2 px-3">Modelo</th>
          <th className="text-center text-g-600 font-semibold py-2 px-3">Qtd</th>
          <th className="text-right text-g-600 font-semibold py-2 px-3">∆ KM c/ ant.</th>
        </tr>
      </thead>
      <tbody>
        {conjuntos.map((conj, ci) => {
          const isAlert      = conj.delta_km != null && avgKm && conj.delta_km < avgKm * 0.8
          const isDescartado = !!conj.descartado
          const posInicial   = conj.fases[0]?.posicao || '—'
          const rotated      = posInicial !== conj.posicao_atual
          const totalDias    = conj.fases.reduce((s, f) => s + (f.dias || 0), 0)
          return (
            <Fragment key={ci}>
              {/* ── Linha principal: resumo do conjunto ── */}
              <tr className={`border-b border-gray-200 font-medium ${isDescartado ? 'opacity-50' : ''} ${ci % 2 === 0 ? 'bg-white' : 'bg-gray-50/40'}`}>
                <td className="py-2.5 px-4">
                  <span className="font-mono text-g-200 text-[11px] font-bold">{conj.os_ref || '—'}</span>
                  {conj.compra_composta && (
                    <span className="ml-1.5 text-[9px] font-bold px-1 py-0.5 rounded bg-blue-100 text-blue-600 uppercase tracking-wide">kit</span>
                  )}
                </td>
                <td className="py-2.5 px-3 text-g-400 font-mono whitespace-nowrap">{conj.data_compra ? dateBR(conj.data_compra) : '—'}</td>
                <td className="py-2.5 px-3 text-right font-mono text-g-500 whitespace-nowrap">{conj.km_compra != null ? num(conj.km_compra) + ' km' : '—'}</td>
                <td className="py-2.5 px-3 text-right font-mono whitespace-nowrap">
                  <span className={`font-bold ${isDescartado ? 'text-g-600' : 'text-emerald-600'}`}>{conj.km_total != null ? num(conj.km_total) + ' km' : '—'}</span>
                  {totalDias > 0 && <span className="text-blue-400 ml-1.5 font-normal text-[10px]">{totalDias}d</span>}
                </td>
                <td className="py-2.5 px-3">
                  <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded bg-gray-100 text-g-500 uppercase tracking-wide">{posInicial}</span>
                </td>
                <td className="py-2.5 px-3">
                  {isDescartado ? (
                    <div className="flex items-center gap-1">
                      <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded bg-red-100 text-red-600 uppercase tracking-wide">{conj.posicao_atual || '—'}</span>
                      <span className="text-[9px] font-bold text-red-500 ml-0.5">substituído</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1">
                      {rotated && <ArrowRight className="w-3 h-3 text-violet-400 shrink-0" />}
                      <span className={`text-[11px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide ${rotated ? 'bg-violet-100 text-violet-700' : 'bg-sky-100 text-sky-700'}`}>
                        {conj.posicao_atual || '—'}
                      </span>
                      {conj.fases.length === 1 && <span className="text-[9px] text-sky-400 ml-0.5">em uso</span>}
                    </div>
                  )}
                </td>
                <td className="py-2.5 px-3 text-[11px]">
                  <span className="text-g-400 font-medium">{conj.marca || '—'}</span>
                  {conj.recapado && (
                    <span className="ml-1.5 text-[9px] font-bold px-1 py-0.5 rounded bg-orange-100 text-orange-700 uppercase tracking-wide">recapado</span>
                  )}
                  {!conj.recapado && conj.condicao?.toLowerCase() === 'usado' && (
                    <span className="ml-1.5 text-[9px] font-bold px-1 py-0.5 rounded bg-amber-100 text-amber-700 uppercase tracking-wide">usado</span>
                  )}
                </td>
                <td className="py-2.5 px-3 text-g-500 text-[11px]">{conj.modelo || '—'}</td>
                <td className="py-2.5 px-3 text-center text-g-500">{conj.qtd ?? '—'}</td>
                <td className="py-2.5 px-3 text-right font-mono whitespace-nowrap">
                  {conj.delta_km != null
                    ? <span className={`font-bold ${isAlert ? 'text-amber-600' : 'text-g-500'}`}>+{num(conj.delta_km)} km</span>
                    : <span className="text-g-700 text-[10px]">1ª compra</span>}
                </td>
              </tr>
              {/* ── Sub-linhas: só renderiza quando há rodízio ── */}
              {conj.fases.length > 1 && conj.fases.map((fase, fi) => {
                const isLast    = fi === conj.fases.length - 1
                const isRodizio = fi > 0
                const prevPos   = isRodizio ? conj.fases[fi - 1].posicao : null
                const faseDescartada = !!fase.descartado
                return (
                  <tr key={`f${fi}`} className={`border-b border-gray-100 ${isDescartado ? 'opacity-50' : ''} ${isRodizio ? 'bg-violet-50/30' : 'bg-gray-50/20'}`}>
                    {/* col 1: conector + badge */}
                    <td className="py-1.5 px-4">
                      <div className="flex items-center gap-1.5 ml-3">
                        <span className="font-mono text-g-700 text-[10px] select-none">{isLast ? '└─' : '├─'}</span>
                        {isRodizio && (
                          <span className="text-[9px] font-bold px-1 py-0.5 rounded bg-violet-100 text-violet-600 uppercase tracking-wide">Rodízio</span>
                        )}
                      </div>
                    </td>
                    {/* col 2: data */}
                    <td className="py-1.5 px-3 font-mono text-g-600 text-[10px]">{fase.data_inicio ? dateBR(fase.data_inicio) : '—'}</td>
                    {/* col 3: range de KM */}
                    <td className="py-1.5 px-3 text-right font-mono text-[10px] text-g-600 whitespace-nowrap">
                      {num(fase.km_inicio)}{fase.km_fim != null
                        ? <> → {num(fase.km_fim)}</>
                        : <> → <span className="text-sky-500 italic">atual</span></>} km
                    </td>
                    {/* col 4: km rodado + dias */}
                    <td className="py-1.5 px-3 text-right font-mono text-[10px] whitespace-nowrap">
                      {fase.km_rodado != null
                        ? <span className={isRodizio ? 'text-violet-600' : 'text-g-500'}>+{num(fase.km_rodado)} km</span>
                        : '—'}
                      {fase.dias != null && <span className="text-g-600 ml-1.5">{fase.dias}d</span>}
                    </td>
                    {/* col 5: de onde veio (só fases de rodízio) */}
                    <td className="py-1.5 px-3">
                      {isRodizio && prevPos && (
                        <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded bg-gray-100 text-g-500 uppercase tracking-wide">{prevPos}</span>
                      )}
                    </td>
                    {/* col 6: para onde foi (só fases de rodízio) */}
                    <td className="py-1.5 px-3">
                      {isRodizio && (
                        <div className="flex items-center gap-1">
                          <ArrowRight className="w-3 h-3 text-violet-400 shrink-0" />
                          {faseDescartada ? (
                            <>
                              <span className="text-[11px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-red-100 text-red-600">{fase.posicao}</span>
                              <span className="text-[9px] font-bold text-red-500 ml-0.5">substituído</span>
                            </>
                          ) : (
                            <>
                              <span className={`text-[11px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded ${fase.em_uso ? 'bg-sky-100 text-sky-700' : 'bg-violet-100 text-violet-700'}`}>
                                {fase.posicao}
                              </span>
                              {fase.em_uso && <span className="text-[9px] text-sky-400 ml-0.5">em uso</span>}
                            </>
                          )}
                        </div>
                      )}
                    </td>
                    {/* col 7, 8, 9: vazios */}
                    <td /><td /><td />
                    {/* col 9: excluir rodízio */}
                    <td className="py-1.5 px-3 text-right">
                      {!fase.em_uso && !faseDescartada && fase.id_rodizio != null && onDeleteRodizio && (
                        <button onClick={() => onDeleteRodizio(fase.id_rodizio)} title="Remover rodízio"
                          className="text-g-700 hover:text-red-500 transition-colors">
                          <X className="w-3 h-3 inline" />
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </Fragment>
          )
        })}
      </tbody>
    </table>
  )

  const StatKpi = ({ label, value, unit, accent }) => (
    <div className={`rounded-xl p-4 flex flex-col gap-1 ${accent ? 'bg-g-850 border border-g-100/20' : 'bg-white border border-gray-100'}`}>
      <span className={`text-[10px] font-bold uppercase tracking-widest ${accent ? 'text-g-500' : 'text-g-600'}`}>{label}</span>
      <span className={`font-mono font-bold text-xl tabular-nums ${accent ? 'text-white' : 'text-g-100'}`}>
        {value != null ? num(value) : '—'}
        {value != null && <span className={`text-sm font-normal ml-1 ${accent ? 'text-g-400' : 'text-g-500'}`}>{unit}</span>}
      </span>
    </div>
  )

  return (
    <>
    <Section title="Intervalos de Serviço por Veículo" icon={Activity}>
      {/* Controles */}
      <div className="flex items-center gap-3 flex-wrap mb-1">
        {/* Sistema selector */}
        <div className="flex gap-1 bg-g-850 border border-g-800 rounded-xl p-1">
          {SISTEMAS_INTERVALO.map(s => (
            <button
              key={s.key}
              onClick={() => setSistema(s.key)}
              title={s.sub}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${sistema === s.key
                ? 'bg-white shadow-sm text-g-200 border border-g-800'
                : 'text-g-600 hover:text-g-400'
              }`}
            >{s.label}</button>
          ))}
        </div>

        {loading && <Loader2 className="w-4 h-4 animate-spin text-g-600 ml-auto" />}
        {!loading && fleet && (
          <span className="ml-auto text-g-700 text-xs">{fleet.total_veiculos} veículo{fleet.total_veiculos !== 1 ? 's' : ''} · {fleet.total_eventos} evento{fleet.total_eventos !== 1 ? 's' : ''}</span>
        )}
      </div>

      {/* KPIs da frota */}
      {!loading && fleet?.km?.n > 0 && (
        <div className="grid grid-cols-3 lg:grid-cols-6 gap-2 mt-1">
          <StatKpi label="KM mínimo"  value={fleet.km.min}  unit="km" />
          <StatKpi label="KM médio"   value={fleet.km.avg}  unit="km" accent />
          <StatKpi label="KM máximo"  value={fleet.km.max}  unit="km" />
          <StatKpi label="Dias mín."  value={fleet.dias.min}  unit="d" />
          <StatKpi label="Dias médio" value={fleet.dias.avg}  unit="d" accent />
          <StatKpi label="Dias máx."  value={fleet.dias.max}  unit="d" />
        </div>
      )}

      {/* Por Medida — apenas Pneu */}
      {!loading && sistema === 'Pneu' && byMedida.length > 0 && (
        <div className="mt-3 border border-g-800 rounded-xl overflow-hidden">
          <div className="bg-g-900 px-4 py-2 flex items-center gap-2">
            <span className="text-g-400 text-[11px] font-bold uppercase tracking-widest">Por Medida</span>
            <span className="text-g-700 text-[10px] ml-auto">{byMedida.length} especificação{byMedida.length !== 1 ? 'ões' : ''}</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs min-w-[520px]">
              <thead>
                <tr className="bg-g-950/40">
                  <th className="text-left text-g-600 font-semibold py-2 px-4">Especificação</th>
                  <th className="text-center text-g-600 font-semibold py-2 px-3">Veículos</th>
                  <th className="text-center text-g-600 font-semibold py-2 px-3">Eventos</th>
                  <th className="text-center text-g-600 font-semibold py-2 px-3">Pneus adquiridos</th>
                  <th className="text-right text-g-600 font-semibold py-2 px-4">ΔKM mín.</th>
                  <th className="text-right text-g-600 font-semibold py-2 px-4">ΔKM médio</th>
                  <th className="text-right text-g-600 font-semibold py-2 px-4">ΔKM máx.</th>
                </tr>
              </thead>
              <tbody>
                {byMedida.map((row, i) => (
                  <tr key={row.spec} className={`border-t border-g-900 ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'}`}>
                    <td className="py-2 px-4 font-mono font-semibold text-g-200">{row.spec}</td>
                    <td className="py-2 px-3 text-center text-g-500">{row.n_veiculos}</td>
                    <td className="py-2 px-3 text-center text-g-500">{row.n_eventos}</td>
                    <td className="py-2 px-3 text-center text-g-400 font-mono">{row.total_pneus || '—'}</td>
                    <td className="py-2 px-4 text-right font-mono text-g-500">{row.min_km != null ? num(row.min_km) + ' km' : '—'}</td>
                    <td className="py-2 px-4 text-right font-mono font-bold text-emerald-600">{row.avg_km != null ? num(row.avg_km) + ' km' : '—'}</td>
                    <td className="py-2 px-4 text-right font-mono text-g-500">{row.max_km != null ? num(row.max_km) + ' km' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Por veículo */}
      {!loading && porPlaca.length === 0 && (
        <p className="text-g-700 text-sm text-center py-8">Nenhum evento de <strong>{sistema}</strong> encontrado no histórico.</p>
      )}

      {!loading && porPlaca.length > 0 && (
        <div className="flex flex-col gap-2 mt-1">
          {porPlaca.map(veh => {
            const isOpen   = expanded.has(veh.placa)
            const allConjs = (veh.por_medida || []).flatMap(m => m.conjuntos || [])
            const isPneuSistema = sistema === 'Pneu'
            const allKms   = isPneuSistema
              ? allConjs.map(c => c.delta_km).filter(Boolean)
              : (veh.eventos || []).map(e => e.delta_km).filter(Boolean)
            const avgKm    = allKms.length  ? Math.round(allKms.reduce((a,b)=>a+b,0)/allKms.length)  : null
            const allDias  = isPneuSistema
              ? allConjs.map(c => c.delta_dias).filter(Boolean)
              : (veh.eventos || []).map(e => e.delta_dias).filter(Boolean)
            const avgDias  = allDias.length ? Math.round(allDias.reduce((a,b)=>a+b,0)/allDias.length) : null
            const hasPorMedida = sistema === 'Pneu' && veh.por_medida?.length > 0
            const specs    = sistema === 'Pneu'
              ? [...new Set((veh.por_medida || []).map(m => m.espec).filter(e => e && e !== '—'))]
              : []

            // Coloured alert on km_rodado_atual
            const kmRodado = veh.km_rodado_atual
            const avgFleet = fleet?.km?.avg
            const rodadoColor = kmRodado == null ? null
              : avgFleet && kmRodado > avgFleet * 0.85 ? 'text-amber-500'
              : 'text-sky-500'

            return (
              <div key={veh.placa} className="border border-g-800 rounded-xl overflow-hidden bg-white">
                {/* Header */}
                <button
                  onClick={() => toggleExpand(veh.placa)}
                  className="w-full flex items-center gap-4 px-5 py-3.5 hover:bg-g-950/5 transition-colors text-left"
                >
                  <span className="font-mono font-extrabold text-g-100 text-base w-24 shrink-0">{veh.placa}</span>
                  <div className="flex-1 min-w-0 flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="text-g-500 text-[11px] font-semibold uppercase tracking-wider">{veh.modelo || '—'}</span>
                    {veh.implemento && <span className="text-g-700 text-[10px]">· {veh.implemento}</span>}
                    {specs.map(s => (
                      <span key={s} className="bg-g-900 border border-g-800 text-g-400 font-mono text-[10px] px-1.5 py-0.5 rounded">{s}</span>
                    ))}
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    <div className="text-right">
                      <span className="text-g-600 text-[10px] block uppercase tracking-wide">Eventos</span>
                      <span className="font-mono font-bold text-g-200 text-sm">{veh.n_eventos}</span>
                    </div>
                    {avgKm && (
                      <div className="text-right">
                        <span className="text-g-600 text-[10px] block uppercase tracking-wide">Média ΔKM</span>
                        <span className="font-mono font-bold text-emerald-600 text-sm">{num(avgKm)} km</span>
                      </div>
                    )}
                    {avgDias && (
                      <div className="text-right">
                        <span className="text-g-600 text-[10px] block uppercase tracking-wide">Média dias</span>
                        <span className="font-mono font-bold text-blue-600 text-sm">{avgDias}d</span>
                      </div>
                    )}
                    {veh.km_por_posicao?.length > 0 && (
                      <div className="flex items-center gap-2 border-l border-g-800 pl-4 shrink-0">
                        {veh.km_por_posicao.map(p => {
                          const pColor = avgFleet && p.km_rodado > avgFleet * 0.85 ? 'text-amber-500' : 'text-sky-500'
                          return (
                            <div key={p.posicao} className="text-right">
                              <span className="text-g-600 text-[10px] block uppercase tracking-wide">{p.posicao}</span>
                              <span className={`font-mono font-bold text-sm ${pColor}`}>{num(p.km_rodado)} km</span>
                              {p.dias_rodando != null && <span className="text-g-600 text-[10px] block">{p.dias_rodando}d</span>}
                            </div>
                          )
                        })}
                      </div>
                    )}
                    {isOpen
                      ? <ChevronUp className="w-4 h-4 text-g-500 ml-2" />
                      : <ChevronDown className="w-4 h-4 text-g-500 ml-2" />}
                  </div>
                </button>

                {/* Conteúdo expandido */}
                {isOpen && (
                  <div className="border-t border-g-800">
                    {/* Barra de ações (Pneu) */}
                    {sistema === 'Pneu' && (
                      <div className="px-5 py-2 bg-g-950/20 border-b border-g-900 flex items-center justify-end">
                        <button
                          onClick={() => setRodizioModal({ placa: veh.placa, specs, conjuntos: allConjs })}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-600/10 border border-violet-500/30 text-violet-700 rounded-lg text-[11px] font-semibold hover:bg-violet-600/20 transition-colors"
                        >
                          <RotateCcw className="w-3 h-3" />
                          Registrar Rodízio
                        </button>
                      </div>
                    )}
                    {/* KM atual info bar (Pneu) */}
                    {veh.km_atual && (
                      <div className="px-5 py-2.5 bg-sky-50/60 border-b border-sky-100 text-xs">
                        <div className="flex items-center gap-4 flex-wrap">
                          <span className="text-sky-700 font-semibold">KM atual do veículo:</span>
                          <span className="font-mono font-bold text-sky-800">{num(veh.km_atual)} km</span>
                          {veh.km_atual_data && <span className="text-sky-500">em {dateBR(veh.km_atual_data)}</span>}
                        </div>
                        {veh.km_por_posicao?.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-3">
                            {veh.km_por_posicao.map(p => {
                              const pct  = avgFleet ? Math.round(p.km_rodado / avgFleet * 100) : null
                              const pCol = avgFleet && p.km_rodado > avgFleet * 0.85 ? 'border-amber-300 bg-amber-50/80 text-amber-700'
                                         : 'border-sky-200 bg-white text-sky-700'
                              return (
                                <div key={p.posicao} className={`flex items-center gap-2 border rounded-lg px-3 py-1.5 ${pCol}`}>
                                  <span className="font-semibold text-[11px] uppercase tracking-wide opacity-70">{p.posicao}</span>
                                  <span className="font-mono font-bold">{num(p.km_rodado)} km</span>
                                  {p.dias_rodando != null && <span className="opacity-60">{p.dias_rodando}d</span>}
                                  {pct != null && <span className="opacity-60 text-[10px]">({pct}% da média)</span>}
                                  {(p.marca || p.espec) && (
                                    <span className="opacity-50 text-[10px] border-l pl-2">
                                      {p.marca}{p.marca && p.espec ? ' · ' : ''}{p.espec}
                                    </span>
                                  )}
                                  {p.numero_os && <span className="opacity-40 text-[10px] font-mono">{p.numero_os}</span>}
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Por especificação (Pneu) */}
                    {hasPorMedida
                      ? veh.por_medida.map(med => (
                          <div key={med.espec} className="border-b border-g-900 last:border-b-0">
                            <div className="bg-g-950/30 px-5 py-1.5 flex items-center gap-3">
                              <span className="font-mono font-bold text-g-300 text-xs">{med.espec}</span>
                              <span className="text-g-600 text-[10px]">{med.n_eventos} conjunto{med.n_eventos !== 1 ? 's' : ''}</span>
                              {med.total_pneus > 0 && <span className="text-g-600 text-[10px]">· {med.total_pneus} pneus</span>}
                              {med.avg_km && <span className="text-emerald-600 font-mono text-[10px] ml-auto">ΔKM médio c/ ant.: <strong>{num(med.avg_km)}</strong> km</span>}
                            </div>
                            <div className="overflow-x-auto">
                              <ConjuntoTable conjuntos={med.conjuntos || []} avgKm={fleet?.km?.avg}
                                onDeleteRodizio={async id => { await deletePneuRodizio(id); load() }} />
                            </div>
                          </div>
                        ))
                      : (
                        <div className="overflow-x-auto">
                          <EventTable eventos={veh.eventos || []} total={veh.n_eventos} isPneu={false} avgKm={fleet?.km?.avg} kms={allKms} dias={allDias} />
                        </div>
                      )
                    }
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </Section>
    {rodizioModal && (
      <RodizioModal
        placa={rodizioModal.placa}
        specs={rodizioModal.specs || []}
        conjuntos={rodizioModal.conjuntos || []}
        onClose={() => setRodizioModal(null)}
        onSaved={() => load()}
      />
    )}
  </>
  )
}

      // ════════════════════════════════════════════════════════════════════
      // ABA ANÁLISE — gráficos e KPIs (conteúdo original)
      // ════════════════════════════════════════════════════════════════════
      function AnaliseTab({year}) {
  const [implData,    setImplData]    = useState([])
  const [implLoading, setImplLoading] = useState(true)
  const [implSel,     setImplSel]     = useState(null)
  const [implPlaca,   setImplPlaca]   = useState('')

  useEffect(() => {
    setImplLoading(true)
    getImplementoAnalysis(year)
      .then(d => { setImplData(d); setImplSel(null); setImplPlaca('') })
      .finally(() => setImplLoading(false))
  }, [year])

      return (
      <div className="flex flex-col gap-8">

            <IntervalosSection />

            {/* ── ANÁLISE POR IMPLEMENTO VEICULAR ─────────────────────── */}
            <Section title="Análise por Implemento Veicular" icon={Truck}>
              {implLoading ? (
                <div className="flex items-center justify-center h-32 gap-2 text-g-600 text-sm">
                  <Loader2 className="w-4 h-4 animate-spin" /> Carregando análise de implementos…
                </div>
              ) : implData.length === 0 ? (
                <div className="flex items-center justify-center h-24 text-g-700 text-sm">Nenhum implemento registrado no período.</div>
              ) : (
                <div className="flex flex-col gap-5">

                  {/* Cards resumo por implemento */}
                  <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                    {implData.map(imp => {
                      const topSis = imp.por_sistema[0]
                      const isSelected = implSel?.implemento === imp.implemento
                      return (
                        <button
                          key={imp.implemento}
                          onClick={() => { setImplSel(isSelected ? null : imp); setImplPlaca('') }}
                          className={`text-left p-4 rounded-xl border transition-all ${isSelected
                            ? 'bg-g-850 border-g-100/40 shadow-lg ring-1 ring-g-100/20'
                            : 'bg-white border-gray-100 hover:border-gray-300 hover:shadow-md'
                          }`}
                        >
                          <div className="flex items-start justify-between mb-2">
                            <span className={`text-[11px] font-bold uppercase tracking-wider ${isSelected ? 'text-g-100' : 'text-g-200'}`}>{imp.implemento}</span>
                            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${isSelected ? 'bg-g-800 text-g-400' : 'bg-g-900 text-g-500'}`}>{imp.n_placas}v</span>
                          </div>
                          <p className={`font-bold font-mono text-base ${isSelected ? 'text-white' : 'text-g-100'}`}>{brl(imp.total_custo)}</p>
                          <p className={`text-xs mt-0.5 ${isSelected ? 'text-g-400' : 'text-g-600'}`}>{imp.total_os} OS{topSis ? ` · ${topSis.sistema}` : ''}</p>
                        </button>
                      )
                    })}
                  </div>

                  {/* Drilldown do implemento selecionado */}
                  {implSel && (
                    <div className="card border border-g-800 rounded-xl overflow-hidden animate-fade-in">
                      {/* Header drilldown */}
                      <div className="flex items-center justify-between px-5 py-3.5 bg-g-850 border-b border-g-800">
                        <div>
                          <span className="text-g-100 font-bold text-sm">{implSel.implemento}</span>
                          <span className="text-g-600 text-xs ml-3">{implSel.total_os} OS · {implSel.n_placas} veículo{implSel.n_placas !== 1 ? 's' : ''} · {brl(implSel.total_custo)}</span>
                        </div>
                        <button onClick={() => { setImplSel(null); setImplPlaca('') }} className="p-1.5 text-g-600 hover:text-g-300 rounded-lg hover:bg-g-800">
                          <X className="w-4 h-4" />
                        </button>
                      </div>

                      <div className="p-5 flex flex-col gap-6">
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                          {/* Sistemas por custo */}
                          <div>
                            <p className="text-g-600 text-[10px] font-bold uppercase tracking-widest mb-3">Sistemas — Custo e Frequência</p>
                            <div className="flex flex-col gap-1.5">
                              {implSel.por_sistema.slice(0, 10).map((s, i) => {
                                const maxCusto = implSel.por_sistema[0]?.custo || 1
                                const pct = Math.round((s.custo / maxCusto) * 100)
                                return (
                                  <div key={i} className="flex items-center gap-3">
                                    <div className="w-28 text-g-300 text-xs font-semibold truncate shrink-0">{s.sistema}</div>
                                    <div className="flex-1 h-5 bg-g-900 rounded overflow-hidden relative">
                                      <div
                                        className="h-full rounded transition-all"
                                        style={{ width: `${pct}%`, background: i === 0 ? '#22c55e' : i === 1 ? '#34d399' : '#6b7280' }}
                                      />
                                      <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-bold text-g-300">{brlShort(s.custo)}</span>
                                    </div>
                                    <span className="text-g-600 text-[10px] w-12 text-right shrink-0">{s.count} OS</span>
                                  </div>
                                )
                              })}
                            </div>
                          </div>

                          {/* Intervalos de KM */}
                          <div>
                            <p className="text-g-600 text-[10px] font-bold uppercase tracking-widest mb-3">Intervalo Médio entre Manutenções (KM)</p>
                            {implSel.intervalos_km.length === 0 ? (
                              <p className="text-g-700 text-xs italic">KM não registrado para calcular intervalos.</p>
                            ) : (
                              <div className="overflow-x-auto">
                                <table className="w-full text-xs">
                                  <thead>
                                    <tr className="border-b border-g-800">
                                      <th className="text-left text-g-600 font-semibold py-1.5 pr-3">Sistema</th>
                                      <th className="text-right text-g-600 font-semibold py-1.5 px-2">Médio</th>
                                      <th className="text-right text-g-600 font-semibold py-1.5 px-2">Mín</th>
                                      <th className="text-right text-g-600 font-semibold py-1.5 px-2">Máx</th>
                                      <th className="text-right text-g-600 font-semibold py-1.5 pl-2">Amostras</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {implSel.intervalos_km.map((iv, i) => (
                                      <tr key={i} className="border-b border-g-900 hover:bg-g-850">
                                        <td className="py-1.5 pr-3 text-g-200 font-semibold">{iv.sistema}</td>
                                        <td className="py-1.5 px-2 text-right font-mono text-emerald-400 font-bold">{num(iv.intervalo_medio)} km</td>
                                        <td className="py-1.5 px-2 text-right font-mono text-g-500">{num(iv.intervalo_min)}</td>
                                        <td className="py-1.5 px-2 text-right font-mono text-g-500">{num(iv.intervalo_max)}</td>
                                        <td className="py-1.5 pl-2 text-right text-g-600">{iv.amostras}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Drilldown por placa */}
                        <div>
                          <div className="flex items-center justify-between mb-3">
                            <p className="text-g-600 text-[10px] font-bold uppercase tracking-widest">Análise por Placa</p>
                            <div className="flex gap-1 flex-wrap">
                              <button
                                onClick={() => setImplPlaca('')}
                                className={`px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wide transition-all ${!implPlaca ? 'bg-g-100 text-white' : 'bg-g-900 border border-g-800 text-g-500 hover:text-g-300'}`}
                              >Geral</button>
                              {implSel.placas.map(p => (
                                <button
                                  key={p}
                                  onClick={() => setImplPlaca(p)}
                                  className={`px-2.5 py-1 rounded-lg text-[10px] font-mono font-bold transition-all ${implPlaca === p ? 'bg-g-100 text-white' : 'bg-g-900 border border-g-800 text-g-500 hover:text-g-300'}`}
                                >{p}</button>
                              ))}
                            </div>
                          </div>

                          {/* Tabela: sistemas × placa ou geral */}
                          {!implPlaca ? (
                            <div className="overflow-x-auto">
                              <table className="w-full text-xs">
                                <thead>
                                  <tr className="border-b border-g-800">
                                    <th className="text-left text-g-600 font-semibold py-1.5 pr-4">Sistema</th>
                                    <th className="text-right text-g-600 font-semibold py-1.5 px-2">OS</th>
                                    <th className="text-right text-g-600 font-semibold py-1.5 px-2">Custo Total</th>
                                    <th className="text-right text-g-600 font-semibold py-1.5 px-2">Custo Médio/OS</th>
                                    <th className="text-right text-g-600 font-semibold py-1.5 pl-2">Interv. KM médio</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {implSel.por_sistema.map((s, i) => {
                                    const iv = implSel.intervalos_km.find(x => x.sistema === s.sistema)
                                    return (
                                      <tr key={i} className="border-b border-g-900 hover:bg-g-850">
                                        <td className="py-1.5 pr-4 text-g-200 font-semibold">{s.sistema}</td>
                                        <td className="py-1.5 px-2 text-right text-g-400 font-mono">{s.count}</td>
                                        <td className="py-1.5 px-2 text-right font-mono text-g-200 font-bold">{brl(s.custo)}</td>
                                        <td className="py-1.5 px-2 text-right font-mono text-g-400">{s.count > 0 ? brlShort(s.custo / s.count) : '—'}</td>
                                        <td className="py-1.5 pl-2 text-right font-mono text-emerald-400">{iv ? `${num(iv.intervalo_medio)} km` : '—'}</td>
                                      </tr>
                                    )
                                  })}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <div className="flex flex-col gap-2">
                              <p className="text-g-500 text-xs">Intervalos de KM por sistema — Placa <span className="font-mono font-bold text-g-200">{implPlaca}</span></p>
                              {implSel.intervalos_km.filter(iv => iv.por_placa?.[implPlaca]).length === 0 ? (
                                <p className="text-g-700 text-xs italic">Sem dados de KM suficientes para esta placa.</p>
                              ) : (
                                <div className="overflow-x-auto">
                                  <table className="w-full text-xs">
                                    <thead>
                                      <tr className="border-b border-g-800">
                                        <th className="text-left text-g-600 font-semibold py-1.5 pr-4">Sistema</th>
                                        <th className="text-right text-g-600 font-semibold py-1.5 pl-2">Intervalo médio (km)</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {implSel.intervalos_km
                                        .filter(iv => iv.por_placa?.[implPlaca])
                                        .map((iv, i) => (
                                          <tr key={i} className="border-b border-g-900 hover:bg-g-850">
                                            <td className="py-1.5 pr-4 text-g-200 font-semibold">{iv.sistema}</td>
                                            <td className="py-1.5 pl-2 text-right font-mono text-emerald-400 font-bold">{num(iv.por_placa[implPlaca])} km</td>
                                          </tr>
                                        ))}
                                    </tbody>
                                  </table>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </Section>
      </div>
      )
}

      // ════════════════════════════════════════════════════════════════════
      // PÁGINA PRINCIPAL
      // ════════════════════════════════════════════════════════════════════
      export default function MaintenancePage({
        year,
        vehicles = [],
        finAlertDismissed,
        setFinAlertDismissed
      }) {
  const [tab, setTab] = useState('gestao')

      return (
      <div className="flex flex-col gap-6">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex gap-1 bg-g-850 border border-g-800 rounded-xl p-1">
            {[
              { key: 'gestao', label: 'Gestão de OS', icon: Wrench },
              { key: 'financeiro', label: 'Financeiro', icon: DollarSign },
              { key: 'analise', label: 'Análise', icon: BarChart2 },
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${tab === key
                    ? 'bg-white shadow-sm text-g-200 border border-g-800'
                    : 'text-g-600 hover:text-g-400'
                  }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {label}
              </button>
            ))}
          </div>
        </div>

        {tab === 'gestao' && <GestaoTab year={year} />}
        {tab === 'financeiro' && <FinanceiroTab year={year} alertDismissed={finAlertDismissed} onAlertDismiss={() => setFinAlertDismissed(true)} />}
        {tab === 'analise' && <AnaliseTab year={year} />}
      </div>
      )
}
