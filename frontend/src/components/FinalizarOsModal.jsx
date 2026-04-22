import { useState } from 'react'
import { createPortal } from 'react-dom'
import { X, Loader2, CheckCircle, Trash2, AlertTriangle, ShieldCheck } from 'lucide-react'
import { dbExecutarOs, dbCriarNf, dbFinalizarOs } from '../utils/api'
import { brl } from '../utils/format'

const EMPRESAS   = ['TKJ', 'FINITA', 'LANDKRAFT']
const TIPOS_NF   = ['Produto', 'Servico']
const FORMAS     = ['Faturado', 'Boleto', 'PIX', 'Cartão', 'Dinheiro']
const STATUS_PAG = ['Pendente', 'Pago']
const STATUS_EXEC = ['Resolvido', 'Parcialmente resolvido', 'Pendente']

const H = 'h-[38px]'
const FIELD = `w-full px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm placeholder-g-700 focus:outline-none focus:border-g-100 transition-colors ${H}`
const LABEL = 'text-g-600 text-xs font-medium mb-1 block'

function MoneyInput({ value, onChange, disabled, className }) {
  return (
    <div className="relative">
      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-g-600 text-xs pointer-events-none select-none">R$</span>
      <input
        type="number" step="0.01" min="0"
        value={value}
        onChange={e => onChange(e.target.value)}
        disabled={disabled}
        placeholder="0,00"
        className={`${className} pl-8`}
      />
    </div>
  )
}

function gerarParcelas(qtd, valorTotal, dataEmissao) {
  const n = Math.max(1, parseInt(qtd) || 1)
  const total = parseFloat(valorTotal) || 0
  const base = dataEmissao ? new Date(dataEmissao + 'T12:00:00') : new Date()
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(base)
    d.setDate(d.getDate() + 30 * (i + 1))
    return {
      data_vencimento:  d.toISOString().slice(0, 10),
      valor_parcela:    total > 0 ? (total / n).toFixed(2) : '',
      forma_pgto:       'Faturado',
      status_pagamento: 'Pendente',
    }
  })
}

function itemMatchesTipo(it, tipo_nf) {
  if (tipo_nf === 'Produto') return it._categoria === 'Compra'
  if (tipo_nf === 'Servico') return it._categoria === 'Serviço' || it._categoria === 'Servico' || !it._categoria
  return true
}

const NF_VAZIA = (osItens) => ({
  tipo_nf:          'Servico',
  numero_nf:        '',
  empresa_faturada: '',
  fornecedor:       '',
  valor_total_nf:   '',
  data_emissao:     new Date().toISOString().slice(0, 10),
  observacoes:      '',
  qtd_parcelas:     '1',
  itens: osItens.map(it => ({
    os_item_id:       it.id,
    _categoria:       it.categoria ?? '',
    _sistema:         it.sistema   ?? '',
    _servico:         it.servico   ?? '',
    quantidade:       '1',
    valor_unitario:   '',
    valor_total_item: '',
    incluir:          true,
  })),
  parcelas: gerarParcelas(1, '', new Date().toISOString().slice(0, 10)),
})

// ── Validação local completa ──────────────────────────────────────────
function validarLocal(nfs, osItens) {
  const erros = []

  // Todos os itens da OS devem estar vinculados a pelo menos uma NF
  const osItemIdsVinculados = new Set(
    nfs.flatMap(nf =>
      nf.itens.filter(it => it.incluir && itemMatchesTipo(it, nf.tipo_nf)).map(it => it.os_item_id)
    )
  )
  osItens.forEach(it => {
    if (!osItemIdsVinculados.has(it.id)) {
      const label = it.servico || it.sistema || `Item ${it.id}`
      const cat   = it.categoria ? ` [${it.categoria}]` : ''
      erros.push(`Item "${label}"${cat} não está vinculado a nenhuma NF`)
    }
  })

  nfs.forEach((nf, ni) => {
    const label = `NF ${ni + 1}${nf.numero_nf ? ` (${nf.numero_nf})` : ''}`

    if (!nf.empresa_faturada)
      erros.push(`${label}: empresa faturada é obrigatória`)

    const valorNf = parseFloat(nf.valor_total_nf) || 0
    if (valorNf <= 0)
      erros.push(`${label}: valor total é obrigatório`)

    const itensVinculados = nf.itens.filter(it => it.incluir && itemMatchesTipo(it, nf.tipo_nf))
    if (itensVinculados.length > 0) {
      const somaItens = itensVinculados.reduce((s, it) => s + (parseFloat(it.valor_total_item) || 0), 0)
      if (valorNf > 0 && Math.abs(somaItens - valorNf) > 0.01)
        erros.push(`${label}: soma dos itens (${brl(somaItens)}) ≠ valor total NF (${brl(valorNf)})`)
    }

    if (nf.parcelas.length === 0)
      erros.push(`${label}: adicione ao menos uma parcela`)

    const somaParcelas = nf.parcelas.reduce((s, p) => s + (parseFloat(p.valor_parcela) || 0), 0)
    if (valorNf > 0 && Math.abs(somaParcelas - valorNf) > 0.01)
      erros.push(`${label}: soma das parcelas (${brl(somaParcelas)}) ≠ valor total NF (${brl(valorNf)})`)
  })

  return erros
}

// ─────────────────────────────────────────────────────────────────────
export default function FinalizarOsModal({ os, onClose, onSaved }) {
  const [step,   setStep]   = useState('executar')
  const [saving, setSaving] = useState(false)
  const [error,  setError]  = useState(null)
  const [errosValidacao, setErrosValidacao] = useState(null)

  const [execForm, setExecForm] = useState({
    data_execucao:      new Date().toISOString().slice(0, 10),
    km:                 os.km       ?? '',
    prox_km:            os.prox_km  ?? '',
    prox_data:          os.prox_data ?? '',
    status_execucao:    'Resolvido',
    descricao_pendente: '',
  })

  const [nfs, setNfs] = useState([NF_VAZIA(os.itens || [])])

  // ── Execução ──────────────────────────────────────────────────────
  const handleExecutar = async () => {
    if (!execForm.data_execucao) { setError('Informe a data de execução'); return }
    const needsPendente = execForm.status_execucao === 'Parcialmente resolvido' || execForm.status_execucao === 'Pendente'
    if (needsPendente && !execForm.descricao_pendente.trim()) {
      setError('Descreva o que ficou pendente'); return
    }
    setSaving(true); setError(null)
    try {
      await dbExecutarOs(os.id, {
        data_execucao:      execForm.data_execucao,
        km:                 execForm.km      ? parseFloat(execForm.km)      : null,
        prox_km:            execForm.prox_km ? parseFloat(execForm.prox_km) : null,
        prox_data:          execForm.prox_data || null,
        status_execucao:    execForm.status_execucao || null,
        descricao_pendente: needsPendente ? execForm.descricao_pendente : null,
      })
      setStep('nfs')
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao executar OS')
    } finally {
      setSaving(false)
    }
  }

  // ── NFs helpers ───────────────────────────────────────────────────
  const setNf = (i, k, v) => setNfs(ns => ns.map((n, idx) => idx !== i ? n : { ...n, [k]: v }))

  const setNfAndRegen = (i, k, v) => setNfs(ns => ns.map((n, idx) => {
    if (idx !== i) return n
    const updated = { ...n, [k]: v }
    if (k === 'valor_total_nf' || k === 'qtd_parcelas') {
      updated.parcelas = gerarParcelas(
        k === 'qtd_parcelas' ? v : n.qtd_parcelas,
        k === 'valor_total_nf' ? v : n.valor_total_nf,
        n.data_emissao,
      )
    }
    return updated
  }))

  const addNf    = () => setNfs(ns => [...ns, NF_VAZIA(os.itens || [])])
  const removeNf = i => setNfs(ns => ns.filter((_, idx) => idx !== i))

  const setNfItem = (ni, realIdx, k, v) => setNfs(ns => ns.map((n, nidx) => nidx !== ni ? n : {
    ...n, itens: n.itens.map((it, iidx) => {
      if (iidx !== realIdx) return it
      const updated = { ...it, [k]: v }
      if (k === 'quantidade' || k === 'valor_unitario') {
        const qtd  = parseFloat(k === 'quantidade'     ? v : it.quantidade)     || 0
        const unit = parseFloat(k === 'valor_unitario' ? v : it.valor_unitario) || 0
        updated.valor_total_item = qtd && unit ? (qtd * unit).toFixed(2) : ''
      }
      return updated
    }),
  }))

  const setParc = (ni, pi, k, v) => setNfs(ns => ns.map((n, nidx) => nidx !== ni ? n : {
    ...n, parcelas: n.parcelas.map((p, pidx) => pidx !== pi ? p : { ...p, [k]: v }),
  }))

  const salvarNfs = async () => {
    const erros = validarLocal(nfs, os.itens || [])
    if (erros.length > 0) { setErrosValidacao(erros); setStep('finalizar'); return }

    setSaving(true); setError(null)
    try {
      for (const nf of nfs) {
        if (!nf.tipo_nf) continue
        const itensVinculados = nf.itens.filter(it =>
          it.incluir && itemMatchesTipo(it, nf.tipo_nf) && (it.valor_total_item || it.valor_unitario)
        )
        await dbCriarNf(os.id, {
          numero_nf:        nf.numero_nf        || null,
          tipo_nf:          nf.tipo_nf,
          empresa_faturada: nf.empresa_faturada || null,
          fornecedor:       nf.fornecedor       || null,
          valor_total_nf:   nf.valor_total_nf   ? parseFloat(nf.valor_total_nf) : null,
          data_emissao:     nf.data_emissao     || null,
          observacoes:      nf.observacoes      || null,
          itens: itensVinculados.map(it => ({
            os_item_id:       it.os_item_id,
            quantidade:       parseFloat(it.quantidade)       || 1,
            valor_unitario:   parseFloat(it.valor_unitario)   || null,
            valor_total_item: parseFloat(it.valor_total_item) || null,
          })),
          parcelas: nf.parcelas.filter(p => p.valor_parcela).map(p => ({
            data_vencimento:  p.data_vencimento || null,
            valor_parcela:    parseFloat(p.valor_parcela),
            forma_pgto:       p.forma_pgto,
            status_pagamento: p.status_pagamento,
          })),
        })
      }
      setErrosValidacao([])
      setStep('finalizar')
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar NFs')
    } finally {
      setSaving(false)
    }
  }

  const handleFinalizar = async () => {
    setSaving(true); setError(null)
    try {
      await dbFinalizarOs(os.id)
      onSaved()
    } catch (err) {
      const detail = err.response?.data?.detail
      const errosBackend = detail?.erros ?? (Array.isArray(detail) ? detail : null)
      if (errosBackend) setErrosValidacao(errosBackend)
      else setError(typeof detail === 'string' ? detail : 'Erro ao finalizar OS')
    } finally {
      setSaving(false)
    }
  }

  const steps = [
    { key: 'executar',  label: '1. Execução' },
    { key: 'nfs',       label: '2. Notas Fiscais' },
    { key: 'finalizar', label: '3. Finalizar' },
  ]

  const needsPendente = execForm.status_execucao === 'Parcialmente resolvido' || execForm.status_execucao === 'Pendente'

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in">
      <div className="bg-g-900 border border-g-800 rounded-2xl shadow-2xl w-full max-w-5xl max-h-[96vh] flex flex-col animate-fade-up">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-g-800 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 bg-emerald-50/20 border border-emerald-500/30 rounded-lg">
              <CheckCircle className="w-4 h-4 text-emerald-500" />
            </div>
            <div>
              <h2 className="text-g-200 font-semibold text-sm">Finalizar OS · {os.placa}</h2>
              <p className="text-g-600 text-xs font-mono">{os.numero_os || 'sem nº'} · {os.fornecedor || '—'}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-g-600 hover:text-g-300 hover:bg-g-850 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Steps */}
        <div className="flex items-center gap-0 px-6 pt-4 shrink-0">
          {steps.map((s, i) => (
            <div key={s.key} className="flex items-center">
              <span className={`text-xs font-medium px-3 py-1 rounded-full transition-colors ${
                step === s.key ? 'bg-g-100 text-white' :
                steps.findIndex(x => x.key === step) > i ? 'text-emerald-500' : 'text-g-700'
              }`}>{s.label}</span>
              {i < steps.length - 1 && <div className="w-8 h-px bg-g-800 mx-1" />}
            </div>
          ))}
        </div>

        {/* Itens da OS (contexto) */}
        {os.itens?.length > 0 && (
          <div className="px-6 pt-3 shrink-0">
            <p className="text-g-600 text-xs font-semibold uppercase tracking-wider mb-1.5">Itens da OS</p>
            <div className="flex flex-wrap gap-2">
              {os.itens.map(it => (
                <span key={it.id} className="bg-g-850 border border-g-800 rounded-lg px-2.5 py-1 text-xs text-g-400">
                  {it.categoria && <span className="text-g-700 mr-1.5 font-medium">[{it.categoria}]</span>}
                  {it.sistema && <span className="text-g-600">{it.sistema} · </span>}
                  {it.servico || it.descricao || '—'}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="overflow-y-auto px-6 py-5 flex flex-col gap-5 flex-1">

          {/* ── Step 1: Execução ── */}
          {step === 'executar' && (
            <>
              <p className="text-g-500 text-sm">Registre a data de execução e o resultado do serviço.</p>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className={LABEL}>Data de Execução *</label>
                  <input type="date" value={execForm.data_execucao}
                    onChange={e => setExecForm(f => ({ ...f, data_execucao: e.target.value }))}
                    className={FIELD} required />
                </div>
                <div>
                  <label className={LABEL}>Status de Execução *</label>
                  <select value={execForm.status_execucao}
                    onChange={e => setExecForm(f => ({ ...f, status_execucao: e.target.value }))}
                    className={FIELD}>
                    {STATUS_EXEC.map(s => <option key={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className={LABEL}>KM na Execução</label>
                  <input type="number" value={execForm.km}
                    onChange={e => setExecForm(f => ({ ...f, km: e.target.value }))}
                    placeholder="Ex: 125000" className={FIELD} />
                </div>
                <div>
                  <label className={LABEL}>Próx. KM</label>
                  <input type="number" value={execForm.prox_km}
                    onChange={e => setExecForm(f => ({ ...f, prox_km: e.target.value }))}
                    placeholder="Ex: 140000" className={FIELD} />
                </div>
                <div>
                  <label className={LABEL}>Próx. Data</label>
                  <input type="date" value={execForm.prox_data}
                    onChange={e => setExecForm(f => ({ ...f, prox_data: e.target.value }))}
                    className={FIELD} />
                </div>
              </div>
              {needsPendente && (
                <div>
                  <label className={LABEL}>Descrição do Pendente *</label>
                  <textarea rows={3} value={execForm.descricao_pendente}
                    onChange={e => setExecForm(f => ({ ...f, descricao_pendente: e.target.value }))}
                    placeholder="Descreva o que ficou pendente ou parcialmente resolvido…"
                    className="w-full px-3 py-2 bg-g-900 border border-amber-500/50 rounded-lg text-g-300 text-sm placeholder-g-700 focus:outline-none focus:border-amber-400 transition-colors resize-none" />
                </div>
              )}
            </>
          )}

          {/* ── Step 2: NFs ── */}
          {step === 'nfs' && (
            <>
              <div className="flex items-center justify-between">
                <p className="text-g-500 text-sm">Adicione as Notas Fiscais emitidas para esta OS.</p>
                <button type="button" onClick={addNf}
                  className="flex items-center gap-1 text-xs text-g-100 hover:text-g-50 font-medium transition-colors">
                  + Nova NF
                </button>
              </div>

              {nfs.map((nf, ni) => {
                const itensVisiveis  = nf.itens.filter(it => itemMatchesTipo(it, nf.tipo_nf))
                const somaItens      = itensVisiveis.filter(it => it.incluir).reduce((s, it) => s + (parseFloat(it.valor_total_item) || 0), 0)
                const somaParcelas   = nf.parcelas.reduce((s, p) => s + (parseFloat(p.valor_parcela) || 0), 0)
                const valorNf        = parseFloat(nf.valor_total_nf) || 0
                const difereItens    = valorNf > 0 && itensVisiveis.some(it => it.incluir) && Math.abs(somaItens - valorNf) > 0.01
                const difereParcelas = valorNf > 0 && Math.abs(somaParcelas - valorNf) > 0.01
                // Aviso não-bloqueante de fornecedor diferente
                const avisaFornecedor = nf.fornecedor && os.fornecedor && nf.fornecedor !== os.fornecedor

                return (
                  <div key={ni} className="border border-g-800 rounded-xl overflow-hidden">
                    <div className="bg-g-850 px-4 py-2.5 flex items-center justify-between">
                      <span className="text-g-400 text-xs font-semibold uppercase tracking-wider">
                        NF {ni + 1} — {nf.tipo_nf === 'Produto' ? 'Compra' : 'Serviço'}
                      </span>
                      {nfs.length > 1 && (
                        <button type="button" onClick={() => removeNf(ni)} className="text-g-600 hover:text-red-500 transition-colors">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                    <div className="p-5 flex flex-col gap-4">

                      {/* Linha 1: tipo_nf, numero_nf, empresa_faturada */}
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <label className={LABEL}>Tipo NF *</label>
                          <select value={nf.tipo_nf} onChange={e => setNf(ni, 'tipo_nf', e.target.value)} className={FIELD}>
                            {TIPOS_NF.map(t => <option key={t}>{t}</option>)}
                          </select>
                        </div>
                        <div>
                          <label className={LABEL}>Nº Nota Fiscal</label>
                          <input value={nf.numero_nf} onChange={e => setNf(ni, 'numero_nf', e.target.value)}
                            placeholder="Ex: 2036" className={FIELD} />
                        </div>
                        <div>
                          <label className={LABEL}>Empresa Faturada *</label>
                          <select value={nf.empresa_faturada} onChange={e => setNf(ni, 'empresa_faturada', e.target.value)}
                            className={`${FIELD} ${!nf.empresa_faturada ? 'border-amber-500/60' : ''}`}>
                            <option value="">Selecione…</option>
                            {EMPRESAS.map(e => <option key={e}>{e}</option>)}
                          </select>
                        </div>
                      </div>

                      {/* Linha 2: fornecedor, data_emissao, valor_total_nf */}
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <label className={LABEL}>Fornecedor</label>
                          <input value={nf.fornecedor}
                            onChange={e => setNf(ni, 'fornecedor', e.target.value.toUpperCase().replace(/[^A-Z0-9\s/]/g, ''))}
                            placeholder="Nome do fornecedor…" className={FIELD} />
                          {avisaFornecedor && (
                            <p className="text-amber-500 text-xs mt-1 flex items-center gap-1">
                              <AlertTriangle className="w-3 h-3" /> Diferente do fornecedor da OS
                            </p>
                          )}
                        </div>
                        <div>
                          <label className={LABEL}>Data de Emissão</label>
                          <input type="date" value={nf.data_emissao}
                            onChange={e => setNf(ni, 'data_emissao', e.target.value)} className={FIELD} />
                        </div>
                        <div>
                          <label className={LABEL}>Valor Total NF *</label>
                          <MoneyInput value={nf.valor_total_nf}
                            onChange={v => setNfAndRegen(ni, 'valor_total_nf', v)}
                            className={FIELD} />
                        </div>
                      </div>

                      {/* Itens vinculados */}
                      {itensVisiveis.length > 0 && (
                        <div>
                          <p className={`${LABEL} mb-2`}>
                            Itens vinculados
                            <span className="text-g-700 ml-1.5">({nf.tipo_nf === 'Produto' ? 'categoria Compra' : 'categoria Serviço'})</span>
                          </p>
                          <div className="flex flex-col gap-1.5">
                            {itensVisiveis.map((it) => {
                              const realIdx = nf.itens.indexOf(it)
                              return (
                                <div key={realIdx} className="grid grid-cols-12 gap-3 items-center bg-g-850 rounded-lg px-4 py-2.5">
                                  <label className="col-span-1 flex items-center justify-center cursor-pointer">
                                    <input type="checkbox" checked={it.incluir}
                                      onChange={e => setNfItem(ni, realIdx, 'incluir', e.target.checked)}
                                      className="w-3.5 h-3.5 accent-g-100" />
                                  </label>
                                  <span className="col-span-4 text-g-400 text-xs truncate">
                                    {it._sistema && <span className="text-g-600 mr-1">{it._sistema} ·</span>}
                                    {it._servico || '—'}
                                  </span>
                                  <div className="col-span-2">
                                    <input type="number" step="0.01" value={it.quantidade}
                                      onChange={e => setNfItem(ni, realIdx, 'quantidade', e.target.value)}
                                      disabled={!it.incluir}
                                      placeholder="Qtd"
                                      className={`${FIELD} bg-g-900 text-xs ${!it.incluir ? 'opacity-40' : ''}`} />
                                  </div>
                                  <div className="col-span-2">
                                    <MoneyInput value={it.valor_unitario}
                                      onChange={v => setNfItem(ni, realIdx, 'valor_unitario', v)}
                                      disabled={!it.incluir}
                                      className={`${FIELD} bg-g-900 text-xs ${!it.incluir ? 'opacity-40' : ''}`} />
                                  </div>
                                  <div className="col-span-3">
                                    <MoneyInput value={it.valor_total_item}
                                      onChange={() => {}}
                                      disabled
                                      className={`${FIELD} bg-g-900 text-xs opacity-60 cursor-default`} />
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                          {itensVisiveis.some(it => it.incluir) && (
                            <div className="flex justify-end mt-2 text-xs gap-4">
                              <span className="text-g-600">Soma itens: <span className="font-mono text-g-400">{brl(somaItens)}</span></span>
                              {difereItens && (
                                <span className="text-amber-500 flex items-center gap-1">
                                  <AlertTriangle className="w-3 h-3" />
                                  Difere {brl(Math.abs(somaItens - valorNf))} do valor NF
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      {itensVisiveis.length === 0 && (
                        <p className="text-g-700 text-xs italic">
                          Nenhum item da OS com categoria compatível com este tipo de NF.
                        </p>
                      )}

                      {/* Parcelas */}
                      <div className="border-t border-g-800 pt-4">
                        <div className="flex items-center gap-4 mb-3">
                          <p className="text-g-500 text-xs font-semibold uppercase tracking-wider">Parcelas</p>
                          <div className="flex items-center gap-2">
                            <label className="text-g-700 text-xs">Quantidade:</label>
                            <input type="number" min="1" max="60" value={nf.qtd_parcelas}
                              onChange={e => setNfAndRegen(ni, 'qtd_parcelas', e.target.value)}
                              className={`w-16 px-2 py-1 bg-g-900 border border-g-800 rounded-lg text-g-300 text-xs focus:outline-none focus:border-g-100 ${H}`} />
                          </div>
                        </div>
                        <div className="flex flex-col gap-2">
                          {nf.parcelas.map((p, pi) => (
                            <div key={pi} className="grid grid-cols-12 gap-3 items-end bg-g-850 rounded-lg px-4 py-2.5">
                              <div className="col-span-1 flex items-end pb-1.5">
                                <span className="text-g-600 text-xs font-mono tabular-nums">{pi + 1}×</span>
                              </div>
                              <div className="col-span-3">
                                <label className={LABEL}>Vencimento</label>
                                <input type="date" value={p.data_vencimento}
                                  onChange={e => setParc(ni, pi, 'data_vencimento', e.target.value)}
                                  className={`${FIELD} bg-g-900`} />
                              </div>
                              <div className="col-span-3">
                                <label className={LABEL}>Valor</label>
                                <MoneyInput value={p.valor_parcela}
                                  onChange={v => setParc(ni, pi, 'valor_parcela', v)}
                                  className={`${FIELD} bg-g-900`} />
                              </div>
                              <div className="col-span-3">
                                <label className={LABEL}>Forma de Pagamento</label>
                                <select value={p.forma_pgto} onChange={e => setParc(ni, pi, 'forma_pgto', e.target.value)}
                                  className={`${FIELD} bg-g-900`}>
                                  {FORMAS.map(f => <option key={f}>{f}</option>)}
                                </select>
                              </div>
                              <div className="col-span-2">
                                <label className={LABEL}>Status</label>
                                <select value={p.status_pagamento} onChange={e => setParc(ni, pi, 'status_pagamento', e.target.value)}
                                  className={`${FIELD} bg-g-900`}>
                                  {STATUS_PAG.map(s => <option key={s}>{s}</option>)}
                                </select>
                              </div>
                            </div>
                          ))}
                        </div>
                        {valorNf > 0 && (
                          <div className="flex justify-end gap-4 mt-2 text-xs">
                            <span className="text-g-600">Total parcelas: <span className="font-mono text-g-400">{brl(somaParcelas)}</span></span>
                            {difereParcelas && (
                              <span className="text-amber-500 flex items-center gap-1">
                                <AlertTriangle className="w-3 h-3" />
                                Difere {brl(Math.abs(somaParcelas - valorNf))} do valor NF
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                    </div>
                  </div>
                )
              })}
            </>
          )}

          {/* ── Step 3: Finalizar ── */}
          {step === 'finalizar' && (
            <>
              {errosValidacao === null ? (
                <div className="bg-g-850 border border-g-800 rounded-xl p-6 flex flex-col items-center gap-3">
                  <ShieldCheck className="w-8 h-8 text-g-600" />
                  <p className="text-g-600 text-sm">Verificando consistência…</p>
                </div>
              ) : errosValidacao.length === 0 ? (
                <div className="bg-emerald-50/10 border border-emerald-500/30 rounded-xl p-5 flex items-center gap-3">
                  <CheckCircle className="w-6 h-6 text-emerald-500 shrink-0" />
                  <div>
                    <p className="text-emerald-400 font-semibold text-sm">OS válida — sem inconsistências</p>
                    <p className="text-g-600 text-xs mt-0.5">Todos os itens vinculados, valores e parcelas consistentes.</p>
                  </div>
                </div>
              ) : (
                <div className="bg-red-50/10 border border-red-500/30 rounded-xl p-4 flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                    <p className="text-red-400 font-semibold text-sm">
                      {errosValidacao.length} inconsistência{errosValidacao.length !== 1 ? 's' : ''} — corrija antes de finalizar
                    </p>
                  </div>
                  <ul className="pl-4 flex flex-col gap-1.5 mt-1">
                    {errosValidacao.map((v, i) => (
                      <li key={i} className="text-red-300 text-xs list-disc">{v}</li>
                    ))}
                  </ul>
                  <button onClick={() => setStep('nfs')}
                    className="mt-2 self-start text-xs text-g-500 underline hover:text-g-300 transition-colors">
                    ← Voltar para NFs e corrigir
                  </button>
                </div>
              )}
            </>
          )}

          {error && (
            <p className="text-red-500 text-xs bg-red-50/10 border border-red-500/20 rounded-lg px-3 py-2">{error}</p>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-g-800 flex items-center justify-between shrink-0">
          <button type="button" onClick={onClose}
            className="px-4 py-2 rounded-lg border border-g-800 text-g-500 text-sm hover:bg-g-850 transition-colors">
            Fechar
          </button>
          <div className="flex items-center gap-2">
            {step === 'nfs' && (
              <button type="button" onClick={() => setStep('executar')}
                className="px-4 py-2 rounded-lg border border-g-800 text-g-500 text-sm hover:bg-g-850 transition-colors">
                Voltar
              </button>
            )}
            {step === 'finalizar' && (
              <button type="button" onClick={() => setStep('nfs')}
                className="px-4 py-2 rounded-lg border border-g-800 text-g-500 text-sm hover:bg-g-850 transition-colors">
                Voltar para NFs
              </button>
            )}
            {step === 'executar' && (
              <button onClick={handleExecutar} disabled={saving}
                className="px-5 py-2 rounded-lg bg-g-100 text-white text-sm font-medium hover:bg-g-50 disabled:opacity-50 transition-colors flex items-center gap-2">
                {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Executar → NFs
              </button>
            )}
            {step === 'nfs' && (
              <button onClick={salvarNfs} disabled={saving}
                className="px-5 py-2 rounded-lg bg-g-100 text-white text-sm font-medium hover:bg-g-50 disabled:opacity-50 transition-colors flex items-center gap-2">
                {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Salvar NFs → Revisar
              </button>
            )}
            {step === 'finalizar' && (
              <button onClick={handleFinalizar}
                disabled={saving || errosValidacao === null || errosValidacao.length > 0}
                className="px-5 py-2 rounded-lg bg-emerald-600 text-white text-sm font-medium hover:bg-emerald-500 disabled:opacity-50 transition-colors flex items-center gap-2">
                {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                Finalizar OS
              </button>
            )}
          </div>
        </div>
      </div>
    </div>,
    document.body
  )
}
