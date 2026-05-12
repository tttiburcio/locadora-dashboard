import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { X, Loader2, Wrench, Plus, Trash2 } from 'lucide-react'
import { dbListFrota, dbAbrirOs, dbAtualizarOs, dbPneuSpecs } from '../utils/api'

const TIPOS       = ['Preventiva', 'Corretiva']
const CATEGORIAS  = ['Serviço', 'Compra']
const STATUS_OPTS = [
  { value: 'em_andamento',    label: 'Em andamento'    },
  { value: 'aguardando_peca', label: 'Aguardando peça' },
]
const SISTEMAS = [
  'Motor', 'Freio', 'Suspensão', 'Elétrico', 'Câmbio', 'Diferencial',
  'Direção', 'Implemento', 'Guincho', 'Pneu', 'Hidráulico', 'Arrefecimento', 'Outro',
]
const POSICOES_PNEU = [
  { value: 'DIANTEIRO', label: 'Dianteiro' },
  { value: 'TRASEIRO',  label: 'Traseiro'  },
  { value: 'ESTEPE',    label: 'Estepe'    },
  { value: 'AMBOS',     label: 'Ambos'     },
]
const CONDICOES_PNEU = ['Novo', 'Usado', 'Recapado']

const F  = 'w-full px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm placeholder-g-700 focus:outline-none focus:border-g-100 transition-colors'
const FI = 'w-full px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm placeholder-g-700 focus:outline-none focus:border-g-600 transition-colors'
const L  = 'text-g-600 text-[10px] uppercase tracking-widest font-bold mb-1.5 block'

const ITEM_VAZIO = {
  categoria: 'Serviço', sistema: '', servico: '', descricao: '', qtd_itens: '',
  posicao_pneu: '', qtd_pneu: '', espec_pneu: '',
  marca_pneu: '', modelo_pneu: '', condicao_pneu: '', manejo_pneu: '',
}

const isPneuCompra = it =>
  it.sistema?.toLowerCase() === 'pneu' && it.categoria?.toLowerCase() === 'compra'

export default function AbrirOsModal({ onClose, onSaved, os = null }) {
  const isEdit = os !== null

  const [frota,        setFrota]        = useState([])
  const [loadingFrota, setLoadingFrota] = useState(true)
  const [pneuSpecs,    setPneuSpecs]    = useState({ por_posicao: {}, specs_unicas: [] })
  const [saving,       setSaving]       = useState(false)
  const [error,        setError]        = useState(null)

  const [form, setForm] = useState(() => ({
    id_veiculo:      os?.id_veiculo      ?? '',
    placa:           os?.placa           ?? '',
    modelo:          os?.modelo          ?? '',
    tipo_manutencao: os?.tipo_manutencao ?? 'Corretiva',
    responsavel_tec: os?.responsavel_tec ?? '',
    indisponivel:    os?.indisponivel    ?? true,
    data_entrada:    os?.data_entrada    ?? new Date().toISOString().slice(0, 10),
    km:              os?.km              ?? '',
    status_os:       os?.status_os       ?? 'em_andamento',
    observacoes:     os?.observacoes     ?? '',
  }))

  const [itens, setItens] = useState(() =>
    os?.itens?.length
      ? os.itens.map(it => ({
          id:            it.id,
          categoria:     it.categoria     ?? 'Serviço',
          sistema:       it.sistema       ?? '',
          servico:       it.servico       ?? '',
          descricao:     it.descricao     ?? '',
          qtd_itens:     it.qtd_itens     ?? '',
          posicao_pneu:  it.posicao_pneu  ?? '',
          qtd_pneu:      it.qtd_pneu      ?? '',
          espec_pneu:    it.espec_pneu    ?? '',
          marca_pneu:    it.marca_pneu    ?? '',
          modelo_pneu:   it.modelo_pneu   ?? '',
          condicao_pneu: it.condicao_pneu ?? '',
          manejo_pneu:   it.manejo_pneu   ?? '',
        }))
      : [{ ...ITEM_VAZIO }]
  )

  useEffect(() => {
    dbListFrota()
      .then(setFrota)
      .catch(() => setError('Não foi possível carregar a frota'))
      .finally(() => setLoadingFrota(false))
  }, [])

  // Carregar specs de pneu quando placa mudar
  useEffect(() => {
    if (!form.placa) { setPneuSpecs({ por_posicao: {}, specs_unicas: [] }); return }
    dbPneuSpecs(form.placa)
      .then(setPneuSpecs)
      .catch(() => setPneuSpecs({ por_posicao: {}, specs_unicas: [] }))
  }, [form.placa])

  const setF = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handlePlaca = e => {
    const placa = e.target.value.toUpperCase()
    const v = frota.find(f => f.placa === placa)
    setForm(f => ({ ...f, placa, id_veiculo: v?.id ?? '', modelo: v?.modelo ?? f.modelo }))
  }

  const setItem = (i, k, v) => setItens(its => its.map((it, idx) => {
    if (idx !== i) return it
    const upd = { ...it, [k]: v }

    if (k === 'sistema' && v?.toLowerCase() === 'pneu') {
      upd.categoria   = 'Compra'
      upd.manejo_pneu = 'Compra'
    }
    if (k === 'categoria' && upd.sistema?.toLowerCase() === 'pneu') {
      upd.manejo_pneu = v?.toLowerCase() === 'compra' ? 'Compra' : ''
    }

    // Auto-fill ao selecionar posição
    if (k === 'posicao_pneu' && v) {
      const posUpper = v.toUpperCase()
      const byPos    = pneuSpecs.por_posicao
      const unicas   = pneuSpecs.specs_unicas   // [{espec_pneu, marca_pneu, ...}]

      let spec = byPos[posUpper] ?? null

      // Fallback: 1 medida única conhecida → preenche independente da posição
      if (!spec && posUpper !== 'AMBOS' && unicas.length === 1) {
        spec = unicas[0]
      }
      // AMBOS com medida única → preenche também
      if (!spec && posUpper === 'AMBOS' && unicas.length === 1) {
        spec = unicas[0]
      }

      if (spec) {
        upd.espec_pneu    = spec.espec_pneu    || upd.espec_pneu
        upd.marca_pneu    = spec.marca_pneu    || upd.marca_pneu
        upd.modelo_pneu   = spec.modelo_pneu   || upd.modelo_pneu
        upd.condicao_pneu = spec.condicao_pneu || upd.condicao_pneu
      }
    }

    return upd
  }))

  const addItem    = () => setItens(its => [...its, { ...ITEM_VAZIO }])
  const removeItem = i  => setItens(its => its.filter((_, idx) => idx !== i))

  const handleSubmit = async e => {
    e.preventDefault()
    if (!form.placa)      { setError('Selecione a placa'); return }
    if (!form.id_veiculo) { setError('Placa não encontrada na frota'); return }

    for (const it of itens) {
      if (!isPneuCompra(it)) continue
      if (!it.posicao_pneu) {
        setError('Informe a posição do pneu em todos os itens Pneu · Compra')
        return
      }
      if (it.posicao_pneu === 'AMBOS' && (parseInt(it.qtd_pneu) || 0) <= 2) {
        setError('Posição "Ambos" requer quantidade maior que 2')
        return
      }
    }

    const itensValidos = itens.filter(it => it.sistema || it.servico)
    setSaving(true); setError(null)
    try {
      const payload = {
        ...form,
        id_veiculo: parseInt(form.id_veiculo),
        km: form.km ? parseFloat(form.km) : null,
        itens: itensValidos.map(it => ({
          id:            it.id            || null,
          categoria:     it.categoria     || null,
          sistema:       it.sistema       || null,
          servico:       it.servico       || null,
          descricao:     it.descricao     || null,
          qtd_itens:     it.qtd_itens     ? parseInt(it.qtd_itens)  : null,
          posicao_pneu:  it.posicao_pneu  || null,
          qtd_pneu:      it.qtd_pneu      ? parseInt(it.qtd_pneu)   : null,
          espec_pneu:    it.espec_pneu    || null,
          marca_pneu:    it.marca_pneu    || null,
          modelo_pneu:   it.modelo_pneu   || null,
          condicao_pneu: it.condicao_pneu || null,
          manejo_pneu:   it.manejo_pneu   || null,
        })),
      }
      isEdit ? await dbAtualizarOs(os.id, payload) : await dbAbrirOs(payload)
      onSaved()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  const placaOk = !!form.placa && !!form.id_veiculo

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in">
      <div className="bg-g-900 border border-g-800 rounded-2xl shadow-2xl w-full max-w-5xl max-h-[92vh] flex flex-col animate-fade-up">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-g-800 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 bg-g-850 border border-g-800 rounded-lg">
              <Wrench className="w-4 h-4 text-g-100" />
            </div>
            <div>
              <h2 className="text-g-200 font-semibold text-sm">
                {isEdit ? 'Editar OS' : 'Abrir Nova OS'}
              </h2>
              <p className="text-g-600 text-xs">
                {isEdit
                  ? `Editando · ${os.placa} · ${os.numero_os || 'sem nº'}`
                  : 'Veículo entrando em manutenção'}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-g-600 hover:text-g-300 hover:bg-g-850 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="overflow-y-auto px-5 py-4 flex flex-col gap-4">

          {/* Veículo */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className={L}>Placa *</label>
              <select value={form.placa} onChange={handlePlaca}
                className={`${F} font-mono`} disabled={loadingFrota || isEdit} required>
                <option value="">{loadingFrota ? 'Carregando…' : 'Selecione…'}</option>
                {frota.map(v => <option key={v.id} value={v.placa}>{v.placa}</option>)}
              </select>
            </div>
            <div>
              <label className={L}>Modelo</label>
              <input value={form.modelo} disabled className={`${F} opacity-60 cursor-default`} />
            </div>
            <div>
              <label className={L}>Data de Entrada</label>
              <input type="date" value={form.data_entrada}
                onChange={e => setF('data_entrada', e.target.value)} className={F} />
            </div>
          </div>

          {/* Tipo + KM + Status + Responsável */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div>
              <label className={L}>Tipo de Manutenção</label>
              <select value={form.tipo_manutencao}
                onChange={e => setF('tipo_manutencao', e.target.value)} className={F}>
                {TIPOS.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className={L}>KM Atual</label>
              <input type="number" value={form.km}
                onChange={e => setF('km', e.target.value)} placeholder="Ex: 125000" className={F} />
            </div>
            <div>
              <label className={L}>Status</label>
              <select value={form.status_os}
                onChange={e => setF('status_os', e.target.value)} className={F}>
                {STATUS_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label className={L}>Responsável Técnico</label>
              <input value={form.responsavel_tec}
                onChange={e => setF('responsavel_tec', e.target.value)}
                placeholder="Nome…" className={F} />
            </div>
          </div>

          {/* Indisponível */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.indisponivel}
              onChange={e => setF('indisponivel', e.target.checked)}
              className="w-4 h-4 accent-g-100 rounded" />
            <span className="text-g-500 text-sm">Veículo indisponível (parado para manutenção)</span>
          </label>

          {/* Itens */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-g-600 text-xs font-semibold uppercase tracking-wider">Itens / Serviços</p>
              <button
                type="button"
                onClick={addItem}
                disabled={!placaOk}
                title={!placaOk ? 'Selecione a placa antes de adicionar itens' : undefined}
                className="flex items-center gap-1 text-xs text-g-100 hover:text-g-50 font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Plus className="w-3.5 h-3.5" /> Adicionar item
              </button>
            </div>

            <div className="flex flex-col gap-2">
              {itens.map((it, i) => {
                const isPneu      = isPneuCompra(it)
                const qtdPneu     = parseInt(it.qtd_pneu) || 0
                const ambosWarn   = it.posicao_pneu === 'AMBOS' && qtdPneu <= 2
                // datalist id único por item
                const dlId        = `dl-medida-${i}`

                return (
                  <div key={i} className="bg-g-850 border border-g-800 rounded-xl p-3">
                    <div className="flex items-end gap-2 flex-wrap">

                      {/* Categoria */}
                      <div style={{ width: 106 }} className="shrink-0">
                        <label className={L}>Categoria</label>
                        <select value={it.categoria}
                          onChange={e => setItem(i, 'categoria', e.target.value)} className={FI}>
                          {CATEGORIAS.map(c => <option key={c}>{c}</option>)}
                        </select>
                      </div>

                      {/* Sistema */}
                      <div style={{ width: 130 }} className="shrink-0">
                        <label className={L}>Sistema</label>
                        <select value={it.sistema}
                          onChange={e => setItem(i, 'sistema', e.target.value)} className={FI}>
                          <option value="">Selecione…</option>
                          {SISTEMAS.map(s => <option key={s}>{s}</option>)}
                        </select>
                      </div>

                      {isPneu ? (
                        <>
                          {/* Posição */}
                          <div style={{ width: 150 }} className="shrink-0">
                            <label className={L}>Posição *</label>
                            <select value={it.posicao_pneu}
                              onChange={e => setItem(i, 'posicao_pneu', e.target.value)}
                              className={`${FI} ${!it.posicao_pneu ? 'border-orange-500/60' : ''}`}>
                              <option value="">Selecione…</option>
                              {POSICOES_PNEU.map(p => (
                                <option key={p.value} value={p.value}
                                  disabled={p.value === 'AMBOS' && qtdPneu <= 2}>
                                  {p.label}{p.value === 'AMBOS' && qtdPneu <= 2 ? ' (qtd > 2)' : ''}
                                </option>
                              ))}
                            </select>
                          </div>

                          {/* Qtd Pneus */}
                          <div style={{ width: 72 }} className="shrink-0">
                            <label className={L}>Qtd</label>
                            <input type="number" min="1" value={it.qtd_pneu}
                              onChange={e => setItem(i, 'qtd_pneu', e.target.value)}
                              placeholder="2" className={FI} />
                          </div>

                          {/* Medida — datalist com sugestões do histórico da placa */}
                          <div style={{ width: 130 }} className="shrink-0">
                            <label className={L}>
                              Medida
                              {it.espec_pneu && (
                                <span className="ml-1 text-g-500 normal-case font-normal tracking-normal">
                                  ·auto
                                </span>
                              )}
                            </label>
                            <datalist id={dlId}>
                              {pneuSpecs.specs_unicas.map(s => (
                                <option key={s.espec_pneu} value={s.espec_pneu} />
                              ))}
                            </datalist>
                            <input
                              list={dlId}
                              value={it.espec_pneu}
                              onChange={e => setItem(i, 'espec_pneu', e.target.value)}
                              placeholder={
                                pneuSpecs.specs_unicas.length === 1
                                  ? pneuSpecs.specs_unicas[0].espec_pneu
                                  : '12.5/80-18'
                              }
                              className={FI}
                            />
                          </div>

                          {/* Marca */}
                          <div style={{ width: 130 }} className="shrink-0">
                            <label className={L}>Marca</label>
                            <input value={it.marca_pneu}
                              onChange={e => setItem(i, 'marca_pneu', e.target.value)}
                              placeholder="Bridgestone" className={FI} />
                          </div>

                          {/* Modelo */}
                          <div style={{ width: 120 }} className="shrink-0">
                            <label className={L}>Modelo</label>
                            <input value={it.modelo_pneu}
                              onChange={e => setItem(i, 'modelo_pneu', e.target.value)}
                              placeholder="L2/G2" className={FI} />
                          </div>

                          {/* Condição */}
                          <div style={{ width: 116 }} className="shrink-0">
                            <label className={L}>Condição</label>
                            <select value={it.condicao_pneu}
                              onChange={e => setItem(i, 'condicao_pneu', e.target.value)}
                              className={FI}>
                              <option value="">Selecione…</option>
                              {CONDICOES_PNEU.map(c => <option key={c}>{c}</option>)}
                            </select>
                          </div>
                        </>
                      ) : (
                        <>
                          <div className="flex-[2] min-w-[120px]">
                            <label className={L}>Item</label>
                            <input value={it.servico}
                              onChange={e => setItem(i, 'servico', e.target.value)}
                              placeholder="Ex: Troca de óleo…" className={FI} />
                          </div>
                          <div className="flex-[2] min-w-[120px]">
                            <label className={L}>Descrição</label>
                            <input value={it.descricao}
                              onChange={e => setItem(i, 'descricao', e.target.value)}
                              placeholder="Detalhes…" className={FI} />
                          </div>
                          <div style={{ width: 72 }} className="shrink-0">
                            <label className={L}>Qtd</label>
                            <input type="number" value={it.qtd_itens}
                              onChange={e => setItem(i, 'qtd_itens', e.target.value)}
                              placeholder="1" className={FI} />
                          </div>
                        </>
                      )}

                      {/* Delete */}
                      <div className="w-7 shrink-0 flex items-end pb-0.5">
                        {itens.length > 1 && (
                          <button type="button" onClick={() => removeItem(i)}
                            className="p-1.5 text-g-600 hover:text-red-500 transition-colors">
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>

                    {ambosWarn && (
                      <p className="mt-1.5 text-[11px] text-orange-400">
                        Posição "Ambos" requer quantidade maior que 2.
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Observações */}
          <div>
            <label className={L}>Observações</label>
            <textarea rows={2} value={form.observacoes}
              onChange={e => setF('observacoes', e.target.value)}
              placeholder="Observações adicionais…" className={`${F} resize-none`} />
          </div>

          {error && (
            <p className="text-red-500 text-xs bg-red-50/10 border border-red-500/20 rounded-lg px-3 py-2">
              {error}
            </p>
          )}
        </form>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-g-800 flex justify-end gap-2 shrink-0">
          <button type="button" onClick={onClose}
            className="px-4 py-2 rounded-lg border border-g-800 text-g-500 text-sm hover:bg-g-850 transition-colors">
            Cancelar
          </button>
          <button onClick={handleSubmit} disabled={saving}
            className="px-5 py-2 rounded-lg bg-g-100 text-white text-sm font-medium hover:bg-g-50 disabled:opacity-50 transition-colors flex items-center gap-2">
            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {isEdit ? 'Salvar Alterações' : 'Abrir OS'}
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}
