import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { X, Loader2, CheckCircle, Plus, Trash2 } from 'lucide-react'
import { dbFinalizarManutencao, dbAbrirManutencao, dbListFrota } from '../utils/api'
import { brl } from '../utils/format'

const CATEGORIAS  = ['Serviço', 'Compra', 'Ambos']
const FORMAS_PGTO = ['Faturado', 'Boleto', 'PIX', 'Cartão', 'Dinheiro']
const STATUS_PARC = ['Pago', 'Pendente']
const TIPO_OPTS   = ['Preventiva', 'Corretiva']
const SISTEMAS    = [
  'Motor', 'Freio', 'Suspensão', 'Elétrico', 'Transmissão',
  'Carroceria', 'Implemento', 'Pneu', 'Hidráulico', 'Arrefecimento', 'Outro',
]

const FIELD = 'w-full px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm placeholder-g-700 focus:outline-none focus:border-g-100 transition-colors'
const LABEL = 'text-g-600 text-xs font-medium mb-1 block'

const PARCELA_VAZIA = {
  nf_ordem: '', nota: '', data_vencimento: '',
  parcela_atual: '', parcela_total: '',
  valor_parcela: '', forma_pgto: 'Faturado', status_pagamento: 'Pago',
}

export default function FinalizarManutencaoModal({ manutencao = null, onClose, onSaved }) {
  const isFromScratch = manutencao === null

  const [saving, setSaving] = useState(false)
  const [error,  setError]  = useState(null)
  const [frota,  setFrota]  = useState([])
  const [loadingFrota, setLoadingFrota] = useState(false)

  const [form, setForm] = useState({
    id_ord_serv:   '',
    total_os:      '',
    data_execucao: new Date().toISOString().slice(0, 10),
    categoria:     'Serviço',
    qtd_itens:     '',
    prox_km:       '',
    prox_data:     '',
    posicao_pneu:  '', qtd_pneu: '', espec_pneu: '',
    marca_pneu:    '', manejo_pneu: '',
    // from-scratch fields
    placa:           '',
    id_veiculo:      '',
    modelo:          '',
    fornecedor:      '',
    tipo_manutencao: 'Corretiva',
    sistema:         '',
    servico:         '',
    data_entrada:    new Date().toISOString().slice(0, 10),
  })

  const [parcelas, setParcelas] = useState([{ ...PARCELA_VAZIA }])
  const [showPneu, setShowPneu] = useState(false)

  useEffect(() => {
    if (!isFromScratch) return
    setLoadingFrota(true)
    dbListFrota().then(setFrota).finally(() => setLoadingFrota(false))
  }, [isFromScratch])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handlePlaca = (e) => {
    const placa = e.target.value.toUpperCase()
    const v = frota.find(f => f.placa === placa)
    setForm(f => ({
      ...f,
      placa,
      id_veiculo: v?.id     || '',
      modelo:     v?.modelo || f.modelo,
    }))
  }

  const setParc = (i, k, v) =>
    setParcelas(ps => ps.map((p, idx) => idx === i ? { ...p, [k]: v } : p))

  const addParcela = () => {
    const last = parcelas[parcelas.length - 1]
    const total = parseInt(last.parcela_total) || parcelas.length + 1
    setParcelas(ps => [
      ...ps,
      { ...PARCELA_VAZIA, parcela_total: total, parcela_atual: ps.length + 1 },
    ])
  }

  const removeParcela = (i) =>
    setParcelas(ps => ps.filter((_, idx) => idx !== i))

  const totalParcelas = parcelas.reduce((s, p) => s + (parseFloat(p.valor_parcela) || 0), 0)

  const buildFinPayload = () => ({
    ...form,
    total_os:  parseFloat(form.total_os),
    qtd_itens: form.qtd_itens ? parseInt(form.qtd_itens) : null,
    prox_km:   form.prox_km   ? parseFloat(form.prox_km) : null,
    prox_data: form.prox_data || null,
    qtd_pneu:  form.qtd_pneu  ? parseInt(form.qtd_pneu) : null,
    parcelas: parcelas
      .filter(p => p.valor_parcela)
      .map((p, i) => ({
        nf_ordem:        p.nf_ordem   ? parseInt(p.nf_ordem)     : null,
        nota:            p.nota       || null,
        data_vencimento: p.data_vencimento || null,
        parcela_atual:   p.parcela_atual   ? parseInt(p.parcela_atual) : i + 1,
        parcela_total:   p.parcela_total   ? parseInt(p.parcela_total) : parcelas.filter(x => x.valor_parcela).length,
        valor_parcela:   parseFloat(p.valor_parcela),
        forma_pgto:      p.forma_pgto,
        status_pagamento: p.status_pagamento,
      })),
  })

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.id_ord_serv) { setError('Informe o número da OS'); return }
    if (!form.total_os)    { setError('Informe o valor total da OS'); return }
    if (isFromScratch) {
      if (!form.placa)      { setError('Selecione a placa do veículo'); return }
      if (!form.id_veiculo) { setError('Placa não encontrada na frota'); return }
    }

    setSaving(true)
    setError(null)
    try {
      if (isFromScratch) {
        const newManut = await dbAbrirManutencao({
          id_veiculo:        parseInt(form.id_veiculo),
          placa:             form.placa,
          modelo:            form.modelo,
          fornecedor:        form.fornecedor,
          tipo_manutencao:   form.tipo_manutencao,
          sistema:           form.sistema,
          servico:           form.servico,
          km:                null,
          responsavel_tec:   '',
          indisponivel:      false,
          data_entrada:      form.data_entrada,
          status_manutencao: 'em_andamento',
          descricao:         '',
          observacoes:       '',
        })
        try {
          await dbFinalizarManutencao(newManut.id, buildFinPayload())
        } catch (finErr) {
          setError('OS criada mas não finalizada — tente novamente')
          return
        }
      } else {
        await dbFinalizarManutencao(manutencao.id, buildFinPayload())
      }
      onSaved()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao finalizar')
    } finally {
      setSaving(false)
    }
  }

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in">
      <div className="bg-g-900 border border-g-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col animate-fade-up">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-g-800">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 bg-emerald-50 border border-emerald-200 rounded-lg">
              <CheckCircle className="w-4 h-4 text-g-100" />
            </div>
            <div>
              <h2 className="text-g-200 font-semibold text-sm">
                {isFromScratch ? 'Inserir OS Finalizada' : 'Finalizar OS'}
              </h2>
              <p className="text-g-600 text-xs font-mono">
                {isFromScratch
                  ? 'Inserção direta de OS finalizada'
                  : `${manutencao.placa} — ${manutencao.servico || manutencao.sistema || '—'}`}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-g-600 hover:text-g-300 hover:bg-g-850 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="overflow-y-auto px-5 py-4 flex flex-col gap-4">

          {/* From-scratch: vehicle + service fields */}
          {isFromScratch && (
            <div className="pb-3 border-b border-g-800">
              <p className="text-g-600 text-xs font-semibold uppercase tracking-wider mb-3">Identificação do Veículo e Serviço</p>
              <div className="grid grid-cols-3 gap-3 mb-3">
                <div>
                  <label className={LABEL}>Placa *</label>
                  <select value={form.placa} onChange={handlePlaca} className={`${FIELD} font-mono`} disabled={loadingFrota} required>
                    <option value="">{loadingFrota ? 'Carregando…' : 'Selecione…'}</option>
                    {frota.map(v => <option key={v.id} value={v.placa}>{v.placa}</option>)}
                  </select>
                </div>
                <div>
                  <label className={LABEL}>Modelo</label>
                  <input value={form.modelo} disabled className={`${FIELD} bg-g-850 text-g-500 cursor-default opacity-70`} />
                </div>
                <div>
                  <label className={LABEL}>Data de Entrada</label>
                  <input type="date" value={form.data_entrada} onChange={e => set('data_entrada', e.target.value)} className={FIELD} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <label className={LABEL}>Fornecedor / Oficina</label>
                  <input
                    value={form.fornecedor}
                    onChange={e => set('fornecedor', e.target.value.toUpperCase().replace(/[^A-Z\s]/g, ''))}
                    placeholder="Nome da oficina…"
                    className={FIELD}
                  />
                </div>
                <div>
                  <label className={LABEL}>Tipo de Manutenção</label>
                  <select value={form.tipo_manutencao} onChange={e => set('tipo_manutencao', e.target.value)} className={FIELD}>
                    {TIPO_OPTS.map(t => <option key={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={LABEL}>Sistema</label>
                  <select value={form.sistema} onChange={e => set('sistema', e.target.value)} className={FIELD}>
                    <option value="">Selecione…</option>
                    {SISTEMAS.map(s => <option key={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className={LABEL}>Serviço</label>
                  <input
                    value={form.servico}
                    onChange={e => set('servico', e.target.value)}
                    placeholder="Ex: Troca de óleo…"
                    className={FIELD}
                  />
                </div>
              </div>
            </div>
          )}

          {/* OS + Data + Total */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className={LABEL}>Nº da OS *</label>
              <input
                placeholder="OS-2025-0001"
                value={form.id_ord_serv}
                onChange={e => set('id_ord_serv', e.target.value)}
                className={FIELD} required
              />
            </div>
            <div>
              <label className={LABEL}>Data de Execução *</label>
              <input
                type="date" value={form.data_execucao}
                onChange={e => set('data_execucao', e.target.value)}
                className={FIELD} required
              />
            </div>
            <div>
              <label className={LABEL}>Valor Total OS (R$) *</label>
              <input
                type="number" step="0.01" placeholder="0,00"
                value={form.total_os}
                onChange={e => set('total_os', e.target.value)}
                className={FIELD} required
              />
            </div>
          </div>

          {/* Categoria + Qtd Itens */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={LABEL}>Categoria</label>
              <select value={form.categoria} onChange={e => set('categoria', e.target.value)} className={FIELD}>
                {CATEGORIAS.map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className={LABEL}>Qtd. de Itens</label>
              <input
                type="number" placeholder="1"
                value={form.qtd_itens}
                onChange={e => set('qtd_itens', e.target.value)}
                className={FIELD}
              />
            </div>
          </div>

          {/* Próxima manutenção */}
          <div>
            <p className="text-g-600 text-xs font-semibold uppercase tracking-wider mb-2">Próxima Manutenção Programada</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={LABEL}>Próx. KM</label>
                <input
                  type="number" placeholder="Ex: 140000"
                  value={form.prox_km}
                  onChange={e => set('prox_km', e.target.value)}
                  className={FIELD}
                />
              </div>
              <div>
                <label className={LABEL}>Próx. Data</label>
                <input
                  type="date" value={form.prox_data}
                  onChange={e => set('prox_data', e.target.value)}
                  className={FIELD}
                />
              </div>
            </div>
          </div>

          {/* Pneu (expansível) */}
          <button
            type="button"
            onClick={() => setShowPneu(v => !v)}
            className="text-g-600 text-xs font-semibold uppercase tracking-wider flex items-center gap-1 hover:text-g-400 transition-colors w-fit"
          >
            {showPneu ? '▾' : '▸'} Dados de Pneu (opcional)
          </button>
          {showPneu && (
            <div className="grid grid-cols-3 gap-3 pl-3 border-l-2 border-g-800">
              <div>
                <label className={LABEL}>Posição</label>
                <input value={form.posicao_pneu} onChange={e => set('posicao_pneu', e.target.value)} placeholder="Ex: Dianteiro E" className={FIELD} />
              </div>
              <div>
                <label className={LABEL}>Qtd.</label>
                <input type="number" value={form.qtd_pneu} onChange={e => set('qtd_pneu', e.target.value)} className={FIELD} />
              </div>
              <div>
                <label className={LABEL}>Marca</label>
                <input value={form.marca_pneu} onChange={e => set('marca_pneu', e.target.value)} className={FIELD} />
              </div>
              <div className="col-span-2">
                <label className={LABEL}>Especificação</label>
                <input value={form.espec_pneu} onChange={e => set('espec_pneu', e.target.value)} placeholder="Ex: 275/80 R22.5" className={FIELD} />
              </div>
              <div>
                <label className={LABEL}>Manejo</label>
                <input value={form.manejo_pneu} onChange={e => set('manejo_pneu', e.target.value)} className={FIELD} />
              </div>
            </div>
          )}

          {/* Parcelas */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-g-600 text-xs font-semibold uppercase tracking-wider">Parcelas de Pagamento</p>
              <button
                type="button" onClick={addParcela}
                className="flex items-center gap-1 text-xs text-g-100 hover:text-g-50 font-medium transition-colors"
              >
                <Plus className="w-3.5 h-3.5" /> Adicionar parcela
              </button>
            </div>

            <div className="flex flex-col gap-2">
              {parcelas.map((p, i) => (
                <div key={i} className="bg-g-850 border border-g-800 rounded-xl p-3 grid grid-cols-12 gap-2 items-end">
                  <div className="col-span-1">
                    <label className={LABEL}>NF</label>
                    <input type="number" value={p.nf_ordem} onChange={e => setParc(i, 'nf_ordem', e.target.value)} className={`${FIELD} bg-g-900`} placeholder="—" />
                  </div>
                  <div className="col-span-2">
                    <label className={LABEL}>Nota</label>
                    <input value={p.nota} onChange={e => setParc(i, 'nota', e.target.value)} className={`${FIELD} bg-g-900`} placeholder="—" />
                  </div>
                  <div className="col-span-2">
                    <label className={LABEL}>Vencimento</label>
                    <input type="date" value={p.data_vencimento} onChange={e => setParc(i, 'data_vencimento', e.target.value)} className={`${FIELD} bg-g-900`} />
                  </div>
                  <div className="col-span-1">
                    <label className={LABEL}>X/Y</label>
                    <div className="flex items-center gap-1">
                      <input type="number" value={p.parcela_atual} onChange={e => setParc(i, 'parcela_atual', e.target.value)} className={`${FIELD} bg-g-900 w-10 px-1 text-center`} placeholder={i+1} />
                      <span className="text-g-600 text-xs">/</span>
                      <input type="number" value={p.parcela_total} onChange={e => setParc(i, 'parcela_total', e.target.value)} className={`${FIELD} bg-g-900 w-10 px-1 text-center`} placeholder={parcelas.length} />
                    </div>
                  </div>
                  <div className="col-span-2">
                    <label className={LABEL}>Valor (R$)</label>
                    <input type="number" step="0.01" value={p.valor_parcela} onChange={e => setParc(i, 'valor_parcela', e.target.value)} className={`${FIELD} bg-g-900`} placeholder="0,00" />
                  </div>
                  <div className="col-span-2">
                    <label className={LABEL}>Forma Pgto</label>
                    <select value={p.forma_pgto} onChange={e => setParc(i, 'forma_pgto', e.target.value)} className={`${FIELD} bg-g-900`}>
                      {FORMAS_PGTO.map(f => <option key={f}>{f}</option>)}
                    </select>
                  </div>
                  <div className="col-span-1">
                    <label className={LABEL}>Status</label>
                    <select value={p.status_pagamento} onChange={e => setParc(i, 'status_pagamento', e.target.value)} className={`${FIELD} bg-g-900 text-xs`}>
                      {STATUS_PARC.map(s => <option key={s}>{s}</option>)}
                    </select>
                  </div>
                  <div className="col-span-1 flex justify-end pb-0.5">
                    {parcelas.length > 1 && (
                      <button type="button" onClick={() => removeParcela(i)} className="p-1.5 text-g-600 hover:text-red-500 transition-colors">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Total parcelas vs total OS */}
            {totalParcelas > 0 && (
              <div className="flex justify-end gap-4 mt-2 text-xs">
                <span className="text-g-600">Total parcelas: <span className="font-mono font-semibold text-g-400">{brl(totalParcelas)}</span></span>
                {form.total_os && Math.abs(totalParcelas - parseFloat(form.total_os)) > 0.01 && (
                  <span className="text-amber-600 font-medium">
                    Difere do total OS em {brl(Math.abs(totalParcelas - parseFloat(form.total_os)))}
                  </span>
                )}
              </div>
            )}
          </div>

          {error && (
            <p className="text-red-600 text-xs bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
          )}
        </form>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-g-800 flex justify-end gap-2">
          <button
            type="button" onClick={onClose}
            className="px-4 py-2 rounded-lg border border-g-800 text-g-500 text-sm hover:bg-g-850 transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="px-5 py-2 rounded-lg bg-g-100 text-white text-sm font-medium hover:bg-g-50 disabled:opacity-50 transition-colors flex items-center gap-2"
          >
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {isFromScratch ? 'Inserir OS' : 'Finalizar OS'}
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}
