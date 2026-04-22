import { useState, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { X, Loader2, CheckCircle, Plus, Trash2, AlertTriangle, ShieldCheck } from 'lucide-react'
import { dbExecutarOs, dbCriarNf, dbFinalizarOs, dbValidarOs } from '../utils/api'
import { brl, dateBR } from '../utils/format'

const TIPOS_NF   = ['Produto', 'Servico']
const FORMAS     = ['Faturado', 'Boleto', 'PIX', 'Cartão', 'Dinheiro']
const STATUS_PAG = ['Pendente', 'Pago']

const FIELD = 'w-full px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm placeholder-g-700 focus:outline-none focus:border-g-100 transition-colors'
const LABEL = 'text-g-600 text-xs font-medium mb-1 block'

const NF_VAZIA = (osItens) => ({
  numero_nf:      '',
  tipo_nf:        'Servico',
  fornecedor:     '',
  valor_total_nf: '',
  data_emissao:   new Date().toISOString().slice(0, 10),
  observacoes:    '',
  itens: osItens.map(it => ({
    os_item_id:       it.id,
    _sistema:         it.sistema,
    _servico:         it.servico,
    valor_unitario:   '',
    valor_total_item: '',
    quantidade:       '1',
    incluir:          true,
  })),
  parcelas: [{ data_vencimento: '', valor_parcela: '', forma_pgto: 'Faturado', status_pagamento: 'Pendente' }],
})

const PARCELA_VAZIA = { data_vencimento: '', valor_parcela: '', forma_pgto: 'Faturado', status_pagamento: 'Pendente' }

export default function FinalizarOsModal({ os, onClose, onSaved }) {
  const [step,      setStep]      = useState('executar')  // executar | nfs | finalizar
  const [saving,    setSaving]    = useState(false)
  const [error,     setError]     = useState(null)
  const [validacao, setValidacao] = useState(null)   // null | string[]

  const [execForm, setExecForm] = useState({
    data_execucao: new Date().toISOString().slice(0, 10),
    km:      os.km      ?? '',
    prox_km: os.prox_km ?? '',
    prox_data: os.prox_data ?? '',
    categoria: os.categoria ?? 'Serviço',
  })

  const [nfs, setNfs] = useState([NF_VAZIA(os.itens || [])])

  // ── Execução ──────────────────────────────────────────────────────
  const handleExecutar = async () => {
    if (!execForm.data_execucao) { setError('Informe a data de execução'); return }
    setSaving(true); setError(null)
    try {
      await dbExecutarOs(os.id, {
        data_execucao: execForm.data_execucao,
        km:            execForm.km       ? parseFloat(execForm.km)       : null,
        prox_km:       execForm.prox_km  ? parseFloat(execForm.prox_km)  : null,
        prox_data:     execForm.prox_data || null,
        categoria:     execForm.categoria || null,
      })
      setStep('nfs')
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao executar OS')
    } finally {
      setSaving(false)
    }
  }

  // ── NFs ──────────────────────────────────────────────────────────
  const setNf    = (i, k, v) => setNfs(ns => ns.map((n, idx) => idx === i ? { ...n, [k]: v } : n))
  const addNf    = () => setNfs(ns => [...ns, NF_VAZIA(os.itens || [])])
  const removeNf = i => setNfs(ns => ns.filter((_, idx) => idx !== i))

  const setNfItem = (ni, ii, k, v) => setNfs(ns => ns.map((n, nidx) => nidx !== ni ? n : {
    ...n, itens: n.itens.map((it, iidx) => iidx !== ii ? it : { ...it, [k]: v }),
  }))

  const setParc = (ni, pi, k, v) => setNfs(ns => ns.map((n, nidx) => nidx !== ni ? n : {
    ...n, parcelas: n.parcelas.map((p, pidx) => pidx !== pi ? p : { ...p, [k]: v }),
  }))

  const addParc    = ni => setNfs(ns => ns.map((n, nidx) => nidx !== ni ? n : { ...n, parcelas: [...n.parcelas, { ...PARCELA_VAZIA }] }))
  const removeParc = (ni, pi) => setNfs(ns => ns.map((n, nidx) => nidx !== ni ? n : { ...n, parcelas: n.parcelas.filter((_, pidx) => pidx !== pi) }))

  const salvarNfs = async () => {
    setSaving(true); setError(null)
    try {
      for (const nf of nfs) {
        if (!nf.tipo_nf) continue
        const itensValidos = nf.itens.filter(it => it.incluir && (it.valor_total_item || it.valor_unitario))
        const payload = {
          numero_nf:      nf.numero_nf      || null,
          tipo_nf:        nf.tipo_nf,
          fornecedor:     nf.fornecedor     || null,
          valor_total_nf: nf.valor_total_nf ? parseFloat(nf.valor_total_nf) : null,
          data_emissao:   nf.data_emissao   || null,
          observacoes:    nf.observacoes    || null,
          itens: itensValidos.map(it => ({
            os_item_id:       it.os_item_id,
            quantidade:       it.quantidade ? parseFloat(it.quantidade) : 1,
            valor_unitario:   it.valor_unitario   ? parseFloat(it.valor_unitario)   : null,
            valor_total_item: it.valor_total_item ? parseFloat(it.valor_total_item) : null,
          })),
          parcelas: nf.parcelas.filter(p => p.valor_parcela).map(p => ({
            data_vencimento:  p.data_vencimento || null,
            valor_parcela:    parseFloat(p.valor_parcela),
            forma_pgto:       p.forma_pgto,
            status_pagamento: p.status_pagamento,
          })),
        }
        await dbCriarNf(os.id, payload)
      }
      setStep('finalizar')
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar NFs')
    } finally {
      setSaving(false)
    }
  }

  // ── Validação + Finalizar ─────────────────────────────────────────
  const handleValidar = useCallback(async () => {
    setSaving(true); setError(null)
    try {
      const erros = await dbValidarOs(os.id)
      setValidacao(erros)
    } catch (err) {
      setError('Erro ao validar OS')
    } finally {
      setSaving(false)
    }
  }, [os.id])

  const handleFinalizar = async () => {
    setSaving(true); setError(null)
    try {
      await dbFinalizarOs(os.id)
      onSaved()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao finalizar OS — verifique inconsistências')
    } finally {
      setSaving(false)
    }
  }

  const steps = [
    { key: 'executar',  label: '1. Execução' },
    { key: 'nfs',       label: '2. Notas Fiscais' },
    { key: 'finalizar', label: '3. Finalizar' },
  ]

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in">
      <div className="bg-g-900 border border-g-800 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[94vh] flex flex-col animate-fade-up">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-g-800 shrink-0">
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
        <div className="flex items-center gap-0 px-5 pt-4 shrink-0">
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

        {/* Itens da OS (contexto sempre visível) */}
        {os.itens?.length > 0 && (
          <div className="px-5 pt-3 shrink-0">
            <p className="text-g-600 text-xs font-semibold uppercase tracking-wider mb-1.5">Itens da OS</p>
            <div className="flex flex-wrap gap-2">
              {os.itens.map(it => (
                <span key={it.id} className="bg-g-850 border border-g-800 rounded-lg px-2.5 py-1 text-xs text-g-400">
                  {it.sistema && <span className="text-g-600">{it.sistema} · </span>}
                  {it.servico || it.descricao || '—'}
                  {it.qtd_itens > 1 && <span className="text-g-600 ml-1">×{it.qtd_itens}</span>}
                </span>
              ))}
            </div>
          </div>
        )}

        <div className="overflow-y-auto px-5 py-4 flex flex-col gap-4 flex-1">

          {/* ── Step 1: Execução ── */}
          {step === 'executar' && (
            <>
              <p className="text-g-500 text-sm">Registre a data de execução e dados de conclusão do serviço.</p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={LABEL}>Data de Execução *</label>
                  <input type="date" value={execForm.data_execucao}
                    onChange={e => setExecForm(f => ({ ...f, data_execucao: e.target.value }))}
                    className={FIELD} required />
                </div>
                <div>
                  <label className={LABEL}>Categoria</label>
                  <select value={execForm.categoria}
                    onChange={e => setExecForm(f => ({ ...f, categoria: e.target.value }))}
                    className={FIELD}>
                    <option value="">Selecione…</option>
                    {['Serviço', 'Compra', 'Ambos'].map(c => <option key={c}>{c}</option>)}
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
            </>
          )}

          {/* ── Step 2: NFs ── */}
          {step === 'nfs' && (
            <>
              <div className="flex items-center justify-between">
                <p className="text-g-500 text-sm">Adicione as Notas Fiscais emitidas para esta OS.</p>
                <button type="button" onClick={addNf}
                  className="flex items-center gap-1 text-xs text-g-100 hover:text-g-50 font-medium transition-colors">
                  <Plus className="w-3.5 h-3.5" /> Nova NF
                </button>
              </div>

              {nfs.map((nf, ni) => {
                const totalParcelas = nf.parcelas.reduce((s, p) => s + (parseFloat(p.valor_parcela) || 0), 0)
                const totalNf       = parseFloat(nf.valor_total_nf) || 0
                const difere        = nf.valor_total_nf && Math.abs(totalParcelas - totalNf) > 0.01
                return (
                  <div key={ni} className="border border-g-800 rounded-xl overflow-hidden">
                    <div className="bg-g-850 px-4 py-2.5 flex items-center justify-between">
                      <span className="text-g-400 text-xs font-semibold uppercase tracking-wider">NF {ni + 1}</span>
                      {nfs.length > 1 && (
                        <button type="button" onClick={() => removeNf(ni)} className="text-g-600 hover:text-red-500 transition-colors">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                    <div className="p-4 flex flex-col gap-3">
                      {/* NF header fields */}
                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <label className={LABEL}>Nº Nota Fiscal</label>
                          <input value={nf.numero_nf} onChange={e => setNf(ni, 'numero_nf', e.target.value)}
                            placeholder="Ex: 2036/2754" className={FIELD} />
                        </div>
                        <div>
                          <label className={LABEL}>Tipo NF *</label>
                          <select value={nf.tipo_nf} onChange={e => setNf(ni, 'tipo_nf', e.target.value)} className={FIELD}>
                            {TIPOS_NF.map(t => <option key={t}>{t}</option>)}
                          </select>
                        </div>
                        <div>
                          <label className={LABEL}>Data de Emissão</label>
                          <input type="date" value={nf.data_emissao} onChange={e => setNf(ni, 'data_emissao', e.target.value)} className={FIELD} />
                        </div>
                        <div>
                          <label className={LABEL}>Fornecedor</label>
                          <input value={nf.fornecedor}
                            onChange={e => setNf(ni, 'fornecedor', e.target.value.toUpperCase().replace(/[^A-Z0-9\s/]/g, ''))}
                            placeholder="Nome do fornecedor…" className={FIELD} />
                        </div>
                        <div>
                          <label className={LABEL}>Valor Total NF (R$)</label>
                          <input type="number" step="0.01" value={nf.valor_total_nf}
                            onChange={e => setNf(ni, 'valor_total_nf', e.target.value)}
                            placeholder="0,00" className={FIELD} />
                        </div>
                      </div>

                      {/* Itens vinculados */}
                      {nf.itens.length > 0 && (
                        <div>
                          <p className={`${LABEL} mb-2`}>Itens vinculados</p>
                          <div className="flex flex-col gap-1.5">
                            {nf.itens.map((it, ii) => (
                              <div key={ii} className="grid grid-cols-12 gap-2 items-center bg-g-850 rounded-lg px-3 py-2">
                                <label className="col-span-1 flex items-center justify-center">
                                  <input type="checkbox" checked={it.incluir}
                                    onChange={e => setNfItem(ni, ii, 'incluir', e.target.checked)}
                                    className="w-3.5 h-3.5 accent-g-100" />
                                </label>
                                <span className="col-span-4 text-g-400 text-xs truncate">
                                  {it._sistema && <span className="text-g-600">{it._sistema} · </span>}
                                  {it._servico || '—'}
                                </span>
                                <div className="col-span-2">
                                  <input type="number" step="0.01" value={it.quantidade}
                                    onChange={e => setNfItem(ni, ii, 'quantidade', e.target.value)}
                                    disabled={!it.incluir}
                                    placeholder="Qtd" className={`${FIELD} bg-g-900 text-xs ${!it.incluir ? 'opacity-40' : ''}`} />
                                </div>
                                <div className="col-span-2">
                                  <input type="number" step="0.01" value={it.valor_unitario}
                                    onChange={e => setNfItem(ni, ii, 'valor_unitario', e.target.value)}
                                    disabled={!it.incluir}
                                    placeholder="Vl Unit." className={`${FIELD} bg-g-900 text-xs ${!it.incluir ? 'opacity-40' : ''}`} />
                                </div>
                                <div className="col-span-3">
                                  <input type="number" step="0.01" value={it.valor_total_item}
                                    onChange={e => setNfItem(ni, ii, 'valor_total_item', e.target.value)}
                                    disabled={!it.incluir}
                                    placeholder="Vl Total" className={`${FIELD} bg-g-900 text-xs ${!it.incluir ? 'opacity-40' : ''}`} />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Parcelas */}
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <p className={LABEL}>Parcelas de Pagamento</p>
                          <button type="button" onClick={() => addParc(ni)}
                            className="text-xs text-g-100 hover:text-g-50 font-medium flex items-center gap-1">
                            <Plus className="w-3 h-3" /> Parcela
                          </button>
                        </div>
                        <div className="flex flex-col gap-2">
                          {nf.parcelas.map((p, pi) => (
                            <div key={pi} className="grid grid-cols-12 gap-2 items-end bg-g-850 rounded-lg px-3 py-2">
                              <div className="col-span-3">
                                <label className={LABEL}>Vencimento</label>
                                <input type="date" value={p.data_vencimento}
                                  onChange={e => setParc(ni, pi, 'data_vencimento', e.target.value)}
                                  className={`${FIELD} bg-g-900`} />
                              </div>
                              <div className="col-span-3">
                                <label className={LABEL}>Valor (R$)</label>
                                <input type="number" step="0.01" value={p.valor_parcela}
                                  onChange={e => setParc(ni, pi, 'valor_parcela', e.target.value)}
                                  placeholder="0,00" className={`${FIELD} bg-g-900`} />
                              </div>
                              <div className="col-span-3">
                                <label className={LABEL}>Forma Pgto</label>
                                <select value={p.forma_pgto} onChange={e => setParc(ni, pi, 'forma_pgto', e.target.value)}
                                  className={`${FIELD} bg-g-900 text-xs`}>
                                  {FORMAS.map(f => <option key={f}>{f}</option>)}
                                </select>
                              </div>
                              <div className="col-span-2">
                                <label className={LABEL}>Status</label>
                                <select value={p.status_pagamento} onChange={e => setParc(ni, pi, 'status_pagamento', e.target.value)}
                                  className={`${FIELD} bg-g-900 text-xs`}>
                                  {STATUS_PAG.map(s => <option key={s}>{s}</option>)}
                                </select>
                              </div>
                              <div className="col-span-1 flex justify-end pb-0.5">
                                {nf.parcelas.length > 1 && (
                                  <button type="button" onClick={() => removeParc(ni, pi)} className="text-g-600 hover:text-red-500 transition-colors">
                                    <Trash2 className="w-3 h-3" />
                                  </button>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                        {totalParcelas > 0 && (
                          <div className="flex justify-end gap-3 mt-1.5 text-xs">
                            <span className="text-g-600">Total parcelas: <span className="font-mono font-semibold text-g-400">{brl(totalParcelas)}</span></span>
                            {difere && (
                              <span className="text-amber-500 flex items-center gap-1">
                                <AlertTriangle className="w-3 h-3" />
                                Difere do valor NF em {brl(Math.abs(totalParcelas - totalNf))}
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

          {/* ── Step 3: Validação + Finalizar ── */}
          {step === 'finalizar' && (
            <>
              <p className="text-g-500 text-sm">Valide a consistência antes de finalizar a OS.</p>
              {validacao === null ? (
                <div className="bg-g-850 border border-g-800 rounded-xl p-6 flex flex-col items-center gap-3">
                  <ShieldCheck className="w-8 h-8 text-g-600" />
                  <p className="text-g-600 text-sm">Clique em "Validar" para checar consistência financeira antes de finalizar.</p>
                  <button onClick={handleValidar} disabled={saving}
                    className="px-5 py-2 rounded-lg border border-g-800 text-g-400 text-sm hover:bg-g-800 hover:text-g-200 transition-colors flex items-center gap-2">
                    {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                    Validar OS
                  </button>
                </div>
              ) : validacao.length === 0 ? (
                <div className="bg-emerald-50/10 border border-emerald-500/30 rounded-xl p-5 flex items-center gap-3">
                  <CheckCircle className="w-6 h-6 text-emerald-500 shrink-0" />
                  <div>
                    <p className="text-emerald-400 font-semibold text-sm">OS válida — sem inconsistências</p>
                    <p className="text-g-600 text-xs mt-0.5">Valores de NFs e parcelas estão consistentes.</p>
                  </div>
                </div>
              ) : (
                <div className="bg-red-50/10 border border-red-500/30 rounded-xl p-4 flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
                    <p className="text-red-400 font-semibold text-sm">{validacao.length} inconsistência{validacao.length !== 1 ? 's' : ''} encontrada{validacao.length !== 1 ? 's' : ''}</p>
                  </div>
                  <ul className="pl-4 flex flex-col gap-1">
                    {validacao.map((v, i) => (
                      <li key={i} className="text-red-300 text-xs list-disc">{v}</li>
                    ))}
                  </ul>
                  <button onClick={handleValidar} disabled={saving}
                    className="mt-1 self-start text-xs text-g-500 underline hover:text-g-300 transition-colors">
                    Revalidar
                  </button>
                </div>
              )}
            </>
          )}

          {error && <p className="text-red-500 text-xs bg-red-50/10 border border-red-500/20 rounded-lg px-3 py-2">{error}</p>}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-g-800 flex items-center justify-between shrink-0">
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
                Voltar
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
                disabled={saving || validacao === null || validacao?.length > 0}
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
