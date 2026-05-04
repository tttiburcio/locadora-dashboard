import { createPortal } from 'react-dom'
import { X, Wrench, FileText, CreditCard, Package, AlertTriangle, CheckCircle, Clock, ChevronDown, ChevronUp } from 'lucide-react'
import { useState } from 'react'
import { brl, dateBR, num } from '../utils/format'

// ── helpers ──────────────────────────────────────────────────────────────
const EMPRESA_NOME_MAP = {
  'TKJ': 'TKJ', 'FINITA': 'FINITA', 'LANDKRAFT': 'LANDKRAFT',
  '1': 'TKJ', '2': 'FINITA', '3': 'LANDKRAFT',
}
function resolveEmpresa(cod) {
  if (!cod) return '—'
  const k = String(cod).toUpperCase().trim()
  return EMPRESA_NOME_MAP[k] || EMPRESA_NOME_MAP[String(parseInt(cod))] || k
}

function diasParados(d1, d2 = null) {
  const a = new Date(d1)
  if (isNaN(a)) return null
  const b = d2 ? new Date(d2) : new Date()
  if (isNaN(b)) return null
  return Math.max(0, Math.round((b - a) / 86400000))
}

// ── sub-components ───────────────────────────────────────────────────────
const Field = ({ label, value, mono = false, isSmall = false }) => (
  <div className="flex flex-col gap-0.5">
    <p className="text-g-600 text-[10px] uppercase tracking-widest font-bold mb-0.5">{label}</p>
    <p className={`${isSmall ? 'text-xs' : 'text-sm'} font-medium ${mono ? 'font-mono' : ''} ${value ? 'text-g-200' : 'text-g-600'} leading-relaxed break-words`}>
      {value || '—'}
    </p>
  </div>
)

function SectionTitle({ icon: Icon, label, count }) {
  return (
    <div className="flex items-center gap-2.5 mb-4">
      <div className="p-1.5 bg-g-850 border border-g-800 rounded-md">
        <Icon className="w-4 h-4 text-g-500" />
      </div>
      <span className="text-g-500 text-sm font-semibold uppercase tracking-widest">{label}</span>
      {count !== undefined && (
        <span className="ml-1 text-g-700 text-sm font-mono">({count})</span>
      )}
      <div className="flex-1 h-px bg-g-850" />
    </div>
  )
}

function ParcelaBadge({ status }) {
  const isPago = status === 'Pago'
  return (
    <span
      className="text-xs font-bold px-2.5 py-1 rounded-full border"
      style={isPago
        ? { color: '#10b981', background: 'rgba(16,185,129,0.12)', borderColor: 'rgba(16,185,129,0.2)' }
        : { color: '#8b5cf6', background: 'rgba(139,92,246,0.12)', borderColor: 'rgba(139,92,246,0.2)' }}
    >
      {status}
    </span>
  )
}

function NfCard({ nf, index, itemLookup }) {
  const [open, setOpen] = useState(true)
  const empresa = resolveEmpresa(nf.empresa_faturada)
  const totalParcelas = nf.parcelas?.length ?? 0
  const pagas = nf.parcelas?.filter(p => p.status_pagamento === 'Pago').length ?? 0
  const progresso = totalParcelas > 0 ? Math.round((pagas / totalParcelas) * 100) : 0
  const barColor = pagas === totalParcelas && totalParcelas > 0 ? '#10b981' : pagas > 0 ? '#8b5cf6' : '#6b7280'

  return (
    <div className="border border-g-800 rounded-xl overflow-hidden">
      {/* NF header */}
      <button
        className="w-full flex items-center justify-between px-4 py-3 bg-g-850 hover:bg-g-800 transition-colors text-left"
        onClick={() => setOpen(v => !v)}
      >
        <div className="flex items-center gap-3">
          <span className="text-g-600 text-sm font-mono">NF {index + 1}</span>
          <span className="text-g-100 text-base font-bold font-mono">{nf.numero_nf || 'Sem número'}</span>
          <span className="text-g-500 text-xs px-2.5 py-1 bg-g-900 rounded border border-g-800">{nf.tipo_nf}</span>
          {nf.tipo_nf_needs_review && (
            <span className="flex items-center gap-1.5 text-amber-400 text-xs font-bold">
              <AlertTriangle className="w-3.5 h-3.5" /> Revisar
            </span>
          )}
        </div>
        <div className="flex items-center gap-5">
          <div className="text-right">
            <div className="text-g-100 font-mono font-bold text-base">{brl(nf.valor_total_nf)}</div>
            <div className="text-g-600 text-xs font-medium">{dateBR(nf.data_emissao) || '—'}</div>
          </div>
          {open ? <ChevronUp className="w-4 h-4 text-g-600" /> : <ChevronDown className="w-4 h-4 text-g-600" />}
        </div>
      </button>

      {open && (
        <div className="px-4 py-4 flex flex-col gap-4">
          {/* NF info row */}
          <div className="grid grid-cols-3 gap-4">
            <Field label="Fornecedor" value={nf.fornecedor} />
            <Field label="Empresa Faturada" value={empresa} />
            <Field label="Emissão" value={dateBR(nf.data_emissao)} />
          </div>
          {nf.observacoes && <Field label="Observações" value={nf.observacoes} isSmall />}

          {/* Itens da NF */}
          {nf.itens?.length > 0 && (
            <div>
              <p className="text-g-600 text-xs uppercase tracking-widest font-bold mb-2.5">
                Itens da Nota ({nf.itens.length})
              </p>
              <div className="flex flex-col gap-1.5">
                {nf.itens.map((it, i) => (
                  <div key={i} className="flex items-center justify-between bg-g-900 border border-g-850 rounded-lg px-4 py-2.5 text-sm">
                    <span className="text-g-400 flex-1 font-medium">
                      {it.descricao_override || (() => {
                        const osItem = itemLookup[it.os_item_id]
                        if (!osItem) return `Item ${i + 1}`
                        const parts = [osItem.sistema, osItem.servico].filter(Boolean)
                        return parts.length > 0 ? parts.join(' — ') : (osItem.descricao || `Item ${i + 1}`)
                      })()}
                    </span>
                    <div className="flex items-center gap-4 text-g-500 shrink-0">
                      {it.quantidade && <span>Qtd: {it.quantidade}</span>}
                      {it.valor_unitario && <span className="font-mono">{brl(it.valor_unitario)}/un</span>}
                      {it.valor_total_item && <span className="font-mono font-bold text-g-200">{brl(it.valor_total_item)}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Parcelas */}
          {nf.parcelas?.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2.5">
                <p className="text-g-600 text-xs uppercase tracking-widest font-bold">
                  Parcelas ({pagas}/{totalParcelas} pagas)
                </p>
                <div className="flex items-center gap-2 w-32">
                  <div className="flex-1 h-1.5 bg-g-850 rounded-full overflow-hidden border border-g-800">
                    <div style={{ width: `${progresso}%`, height: '100%', background: barColor, transition: 'width 0.4s' }} />
                  </div>
                  <span className="text-g-600 text-[10px] font-mono w-8 text-right">{progresso}%</span>
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                {nf.parcelas.map((p, i) => (
                  <div key={i} className="bg-g-900 border border-g-800 rounded-lg px-4 py-3 flex items-center justify-between text-sm">
                    <div className="flex items-center gap-4">
                      <span className="text-g-600 font-mono w-14 font-bold">
                        {p.parcela_atual != null ? `${p.parcela_atual}/${p.parcela_total}` : `#${i + 1}`}
                      </span>
                      {p.data_vencimento && (
                        <span className="text-g-400 font-medium">Venc. {dateBR(p.data_vencimento)}</span>
                      )}
                      {p.forma_pgto && <span className="text-g-600">{p.forma_pgto}</span>}
                      {p.prorrogada && (
                        <span className="text-amber-500 text-xs font-bold">PRORROGADA</span>
                      )}
                    </div>
                    <div className="flex items-center gap-4">
                      {p.valor_atualizado && p.valor_atualizado !== p.valor_parcela && (
                        <span className="font-mono text-amber-500 font-bold text-xs">(Atual: {brl(p.valor_atualizado)})</span>
                      )}
                      <span className="font-mono font-bold text-g-100 text-base">{brl(p.valor_parcela)}</span>
                      <ParcelaBadge status={p.status_pagamento} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── modal principal ───────────────────────────────────────────────────────
export default function DetalhesOsModal({ manutencao: os, onClose, onDeleted }) {
  const isFin = os.status_os === 'finalizada'
  // Só contar dias se veículo estava indisponível
  const dias = (os.indisponivel && os.data_entrada)
    ? diasParados(os.data_entrada, isFin && os.data_execucao ? os.data_execucao : null)
    : null

  // Monta lookup: os_item_id → {sistema, servico, descricao}
  const itemLookup = {}
  ;(os.itens || []).forEach(it => { itemLookup[it.id] = it })

  // Fornecedores únicos das NFs
  const fornecedoresNf = [...new Set(
    (os.notas_fiscais || []).map(nf => nf.fornecedor).filter(Boolean)
  )]

  const allParcelas = (os.notas_fiscais || []).flatMap(nf => nf.parcelas || [])
  
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
  const totalNfs = (os.notas_fiscais || []).reduce((s, nf) => s + (nf.valor_total_nf || 0), 0)

  const STATUS_COLOR = {
    finalizada: '#10b981',
    em_andamento: '#f59e0b',
    aguardando_peca: '#f97316',
    executado_aguardando_nf: '#8b5cf6',
  }
  const barTopColor = STATUS_COLOR[os.status_os] || '#6b7280'

  const STATUS_LABEL = {
    finalizada: 'Finalizada',
    em_andamento: 'Em andamento',
    aguardando_peca: 'Aguardando peça',
    executado_aguardando_nf: 'Aguardando NF',
    aberta: 'Aberta',
    pendente: 'Pendente',
  }

  return createPortal(
    <div
      className="fixed inset-0 z-[9999] flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-g-900 border border-g-800 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[92vh] flex flex-col animate-fade-up overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Barra de cor no topo */}
        <div style={{ height: '4px', background: barTopColor, flexShrink: 0 }} />

        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 border-b border-g-800">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <span className="font-mono font-bold text-g-100 text-xl tracking-tight">{os.placa}</span>
              <span className="text-g-500 font-mono text-sm">{os.numero_os || ''}</span>
              <span
                className="text-[10px] font-bold px-2.5 py-0.5 rounded-full"
                style={{
                  color: barTopColor,
                  background: barTopColor + '18',
                  border: `1px solid ${barTopColor}30`
                }}
              >
                {STATUS_LABEL[os.status_os] || os.status_os}
              </span>
            </div>
            <p className="text-g-500 text-xs">
              {os.modelo || '—'}
              {os.implemento ? ` · ${os.implemento}` : ''}
            </p>
            {fornecedoresNf.length > 0 && (
              <p className="text-g-600 text-xs mt-0.5">
                {fornecedoresNf.join(' · ')}
              </p>
            )}
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-g-600 hover:text-g-300 hover:bg-g-850 transition-colors mt-0.5">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body scrollable */}
        <div className="overflow-y-auto flex-1 px-6 py-5 flex flex-col gap-6">

          {/* ── 1. Identificação da OS ── */}
          <div>
            <SectionTitle icon={Wrench} label="Ordem de Serviço" />
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-4">
              <Field label="Data de Entrada"     value={dateBR(os.data_entrada)} />
              <Field label="Data de Execução"    value={dateBR(os.data_execucao)} />
              {dias !== null && (
                <div className="flex flex-col gap-0.5">
                  <p className="text-g-500 text-[10px] uppercase tracking-widest font-semibold">Dias na Oficina</p>
                  <p className={`text-[15px] font-medium ${dias > 30 ? 'text-red-500' : dias > 7 ? 'text-amber-500' : 'text-g-200'}`}>
                    {dias} {dias === 1 ? 'dia' : 'dias'}
                  </p>
                </div>
              )}
              <Field label="KM"                  value={os.km    ? `${num(os.km)} km`    : null} mono />
              <Field label="Próxima Revisão KM"  value={os.prox_km  ? `${num(os.prox_km)} km`  : null} mono />
              <Field label="Próxima Revisão Data" value={dateBR(os.prox_data)} />
              <Field label="Tipo de Manutenção"  value={os.tipo_manutencao} />
              <Field label="Categoria"           value={os.categoria} />
              <Field label="Responsável Técnico" value={os.responsavel_tec} />
              <div className="flex flex-col gap-0.5">
                <p className="text-g-500 text-[10px] uppercase tracking-widest font-semibold">Veículo Indisponível</p>
                <p className={`text-[15px] font-medium ${os.indisponivel ? 'text-orange-500' : 'text-g-500'}`}>
                  {os.indisponivel ? 'Sim' : 'Não'}
                </p>
              </div>
              <Field label="Contrato" value={os.id_contrato} mono />
              {/* Empresa: consolidada das NFs */}
              {os.notas_fiscais && os.notas_fiscais.length > 0 && (
                <div className="flex flex-col gap-0.5">
                  <p className="text-g-500 text-[10px] uppercase tracking-widest font-semibold">Empresas Faturadas</p>
                  <p className="text-g-200 text-[15px] font-medium">
                    {[...new Set(os.notas_fiscais.map(nf => resolveEmpresa(nf.empresa_faturada)).filter(e => e && e !== '—'))].join(' · ') || '—'}
                  </p>
                </div>
              )}
            </div>
            {os.observacoes && (
              <div className="mt-5 bg-g-850 border border-g-800 rounded-lg px-5 py-4 shadow-inner">
                <p className="text-g-600 text-[10px] uppercase tracking-widest font-bold mb-1.5">Observações</p>
                <p className="text-g-300 text-xs leading-relaxed font-medium">{os.observacoes}</p>
              </div>
            )}
            {os.descricao_pendente && (
              <div className="mt-3 bg-amber-950/30 border border-amber-800/40 rounded-lg px-5 py-4 shadow-inner">
                <p className="text-amber-500 text-[10px] uppercase tracking-widest font-bold mb-1.5">Descrição Pendente</p>
                <p className="text-amber-200 text-xs leading-relaxed font-medium">{os.descricao_pendente}</p>
              </div>
            )}
          </div>

          {/* ── 2. Itens de Serviço ── */}
          {os.itens?.length > 0 && (
            <div>
              <SectionTitle icon={Package} label="Itens de Serviço" count={os.itens.length} />
              <div className="flex flex-col gap-2">
                {os.itens.map((item, i) => (
                  <div key={i} className="bg-g-850 border border-g-800 rounded-xl px-5 py-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap mb-2">
                          {item.categoria && (
                            <span className="text-xs font-bold uppercase text-g-600">{item.categoria}</span>
                          )}
                          {item.categoria && (item.sistema || item.servico) && <span className="text-g-700">·</span>}
                          {item.sistema && (
                            <span className="text-g-200 text-sm font-semibold">{item.sistema}</span>
                          )}
                          {item.servico && (
                            <span className="text-g-500 text-sm font-medium">· {item.servico}</span>
                          )}
                        </div>
                        {item.descricao && <p className="text-g-500 text-sm mt-2 leading-relaxed italic">{item.descricao}</p>}
                      </div>
                      {item.qtd_itens && (
                        <span className="text-g-600 text-sm font-mono shrink-0 font-bold">Qtd: {item.qtd_itens}</span>
                      )}
                    </div>
                    {/* Pneu */}
                    {(item.posicao_pneu || item.espec_pneu || item.marca_pneu) && (
                      <div className="flex items-center gap-4 mt-2 pt-2 border-t border-g-800 flex-wrap">
                        {item.posicao_pneu && <span className="text-g-600 text-[10px]">Pos: <span className="text-g-400">{item.posicao_pneu}</span></span>}
                        {item.qtd_pneu    && <span className="text-g-600 text-[10px]">Qtd: <span className="text-g-400">{item.qtd_pneu}</span></span>}
                        {item.espec_pneu  && <span className="text-g-600 text-[10px]">Espec: <span className="text-g-400">{item.espec_pneu}</span></span>}
                        {item.marca_pneu  && <span className="text-g-600 text-[10px]">Marca: <span className="text-g-400">{item.marca_pneu}</span></span>}
                        {item.manejo_pneu && <span className="text-g-600 text-[10px]">Manejo: <span className="text-g-400">{item.manejo_pneu}</span></span>}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── 3. Notas Fiscais ── */}
          {os.notas_fiscais?.length > 0 && (
            <div>
              <SectionTitle icon={FileText} label="Notas Fiscais" count={os.notas_fiscais.length} />
              {/* Resumo financeiro */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5">
                <div className="bg-g-850 border border-g-800 rounded-xl p-4 text-center">
                  <p className="text-g-600 text-xs uppercase font-bold tracking-wider mb-1.5">Total NFs</p>
                  <p className="text-g-50 text-mono font-extrabold text-lg">{brl(totalNfs)}</p>
                </div>
                <div className="bg-g-850 border border-g-800 rounded-xl p-4 text-center">
                  <p className="text-g-600 text-xs uppercase font-bold tracking-wider mb-1.5">Parcelas</p>
                  <p className="text-g-50 text-mono font-extrabold text-lg">{pagas} / {totalParcelas}</p>
                </div>
                <div
                  className="border rounded-xl p-4 text-center"
                  style={{
                    background: pagas === totalParcelas && totalParcelas > 0 ? 'rgba(16,185,129,0.12)' : 'rgba(139,92,246,0.12)',
                    borderColor: pagas === totalParcelas && totalParcelas > 0 ? 'rgba(16,185,129,0.3)' : 'rgba(139,92,246,0.3)',
                  }}
                >
                  <p className="text-g-600 text-xs uppercase font-bold tracking-wider mb-1.5">Status</p>
                  <p className="font-extrabold text-base" style={{ color: pagas === totalParcelas && totalParcelas > 0 ? '#10b981' : '#8b5cf6' }}>
                    {pagas === totalParcelas && totalParcelas > 0 ? 'Quitado' : pagas > 0 ? `${Math.round((pagas/totalParcelas)*100)}%` : 'Pendente'}
                  </p>
                </div>
              </div>
              <div className="flex flex-col gap-3">
                {os.notas_fiscais.map((nf, i) => (
                  <NfCard key={nf.id} nf={nf} index={i} itemLookup={itemLookup} />
                ))}
              </div>
            </div>
          )}

          {/* Sem NFs ainda */}
          {(!os.notas_fiscais || os.notas_fiscais.length === 0) && (
            <div className="flex flex-col items-center justify-center py-6 text-g-700 gap-2">
              <FileText className="w-8 h-8 opacity-20" />
              <p className="text-sm">Nenhuma Nota Fiscal registrada</p>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-g-800 flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-lg border border-g-800 text-g-400 text-sm font-medium hover:bg-g-850 hover:text-g-200 transition-colors"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}
