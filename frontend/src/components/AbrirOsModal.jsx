import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { X, Loader2, Wrench, Plus, Trash2 } from 'lucide-react'
import { dbListFrota, dbAbrirOs, dbAtualizarOs } from '../utils/api'

const TIPOS      = ['Preventiva', 'Corretiva']
const CATEGORIAS_ITEM = ['Serviço', 'Compra']
const STATUS_OPTS = [
  { value: 'em_andamento',    label: 'Em andamento' },
  { value: 'aguardando_peca', label: 'Aguardando peça' },
]
const SISTEMAS = [
  'Motor', 'Freio', 'Suspensão', 'Elétrico', 'Câmbio', 'Diferencial',
  'Direção', 'Implemento', 'Guincho', 'Pneu', 'Hidráulico', 'Arrefecimento', 'Outro',
]

const FIELD = 'w-full px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm placeholder-g-700 focus:outline-none focus:border-g-100 transition-colors'
const LABEL = 'text-g-600 text-[10px] uppercase tracking-widest font-bold mb-1.5 block'

const ITEM_VAZIO = { categoria: 'Serviço', sistema: '', servico: '', descricao: '', qtd_itens: '' }

export default function AbrirOsModal({ onClose, onSaved, os = null }) {
  const isEdit = os !== null

  const [frota,        setFrota]        = useState([])
  const [loadingFrota, setLoadingFrota] = useState(true)
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
    (os?.itens?.length ? os.itens.map(it => ({
      id:        it.id,
      categoria: it.categoria ?? 'Serviço',
      sistema:   it.sistema   ?? '',
      servico:   it.servico   ?? '',
      descricao: it.descricao ?? '',
      qtd_itens: it.qtd_itens ?? '',
    })) : [{ ...ITEM_VAZIO }])
  )

  useEffect(() => {
    dbListFrota()
      .then(setFrota)
      .catch(() => setError('Não foi possível carregar a frota'))
      .finally(() => setLoadingFrota(false))
  }, [])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handlePlaca = e => {
    const placa = e.target.value.toUpperCase()
    const v = frota.find(f => f.placa === placa)
    setForm(f => ({ ...f, placa, id_veiculo: v?.id ?? '', modelo: v?.modelo ?? f.modelo }))
  }

  const setItem = (i, k, v) => setItens(its => its.map((it, idx) => idx === i ? { ...it, [k]: v } : it))
  const addItem    = () => setItens(its => [...its, { ...ITEM_VAZIO }])
  const removeItem = i  => setItens(its => its.filter((_, idx) => idx !== i))

  const handleSubmit = async e => {
    e.preventDefault()
    if (!form.placa)      { setError('Selecione a placa'); return }
    if (!form.id_veiculo) { setError('Placa não encontrada na frota'); return }
    const itensValidos = itens.filter(it => it.sistema || it.servico)
    setSaving(true); setError(null)
    try {
      const payload = {
        ...form,
        id_veiculo: parseInt(form.id_veiculo),
        km: form.km ? parseFloat(form.km) : null,
        itens: itensValidos.map(it => ({
          id:        it.id || null,
          categoria: it.categoria || null,
          sistema:   it.sistema   || null,
          servico:   it.servico   || null,
          descricao: it.descricao || null,
          qtd_itens: it.qtd_itens ? parseInt(it.qtd_itens) : null,
        })),
      }
      if (isEdit) {
        await dbAtualizarOs(os.id, payload)
      } else {
        await dbAbrirOs(payload)
      }
      onSaved()
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm animate-fade-in">
      <div className="bg-g-900 border border-g-800 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[92vh] flex flex-col animate-fade-up">

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
                {isEdit ? `Editando · ${os.placa} · ${os.numero_os || 'sem nº'}` : 'Veículo entrando em manutenção'}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-g-600 hover:text-g-300 hover:bg-g-850 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="overflow-y-auto px-5 py-4 flex flex-col gap-4">

          {/* Veículo */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            <div>
              <label className={LABEL}>Placa *</label>
              <select value={form.placa} onChange={handlePlaca} className={`${FIELD} font-mono`}
                disabled={loadingFrota || isEdit} required>
                <option value="">{loadingFrota ? 'Carregando…' : 'Selecione…'}</option>
                {frota.map(v => <option key={v.id} value={v.placa}>{v.placa}</option>)}
              </select>
            </div>
            <div>
              <label className={LABEL}>Modelo</label>
              <input value={form.modelo} disabled className={`${FIELD} opacity-60 cursor-default`} />
            </div>
            <div>
              <label className={LABEL}>Data de Entrada</label>
              <input type="date" value={form.data_entrada} onChange={e => set('data_entrada', e.target.value)} className={FIELD} />
            </div>
          </div>

          {/* Tipo + KM + Status + Responsável */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className={LABEL}>Tipo de Manutenção</label>
              <select value={form.tipo_manutencao} onChange={e => set('tipo_manutencao', e.target.value)} className={FIELD}>
                {TIPOS.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className={LABEL}>KM Atual</label>
              <input type="number" value={form.km} onChange={e => set('km', e.target.value)} placeholder="Ex: 125000" className={FIELD} />
            </div>
            <div>
              <label className={LABEL}>Status</label>
              <select value={form.status_os} onChange={e => set('status_os', e.target.value)} className={FIELD}>
                {STATUS_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div>
              <label className={LABEL}>Responsável Técnico</label>
              <input value={form.responsavel_tec} onChange={e => set('responsavel_tec', e.target.value)} placeholder="Nome…" className={FIELD} />
            </div>
          </div>

          {/* Indisponível */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={form.indisponivel} onChange={e => set('indisponivel', e.target.checked)} className="w-4 h-4 accent-g-100 rounded" />
            <span className="text-g-500 text-sm">Veículo indisponível (parado para manutenção)</span>
          </label>

          {/* Itens */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-g-600 text-xs font-semibold uppercase tracking-wider">Itens / Serviços</p>
              <button type="button" onClick={addItem}
                className="flex items-center gap-1 text-xs text-g-100 hover:text-g-50 font-medium transition-colors">
                <Plus className="w-3.5 h-3.5" /> Adicionar item
              </button>
            </div>
            <div className="flex flex-col gap-2">
              {itens.map((it, i) => (
                <div key={i} className="bg-g-850 border border-g-800 rounded-xl p-3 flex flex-col sm:flex-row items-stretch sm:items-end gap-3 sm:gap-2">
                  <div className="w-full sm:w-[88px] shrink-0">
                    <label className={LABEL}>Categoria</label>
                    <select value={it.categoria} onChange={e => setItem(i, 'categoria', e.target.value)} className={`${FIELD} bg-g-900`}>
                      {CATEGORIAS_ITEM.map(c => <option key={c}>{c}</option>)}
                    </select>
                  </div>
                  <div className="w-full sm:w-[120px] shrink-0">
                    <label className={LABEL}>Sistema</label>
                    <select value={it.sistema} onChange={e => setItem(i, 'sistema', e.target.value)} className={`${FIELD} bg-g-900`}>
                      <option value="">Selecione…</option>
                      {SISTEMAS.map(s => <option key={s}>{s}</option>)}
                    </select>
                  </div>
                  <div className="w-full sm:flex-[2] sm:w-auto min-w-0">
                    <label className={LABEL}>Item</label>
                    <input value={it.servico} onChange={e => setItem(i, 'servico', e.target.value)}
                      placeholder="Ex: Troca de óleo…" className={`${FIELD} bg-g-900`} />
                  </div>
                  <div className="w-full sm:flex-[2] sm:w-auto min-w-0">
                    <label className={LABEL}>Descrição</label>
                    <input value={it.descricao} onChange={e => setItem(i, 'descricao', e.target.value)}
                      placeholder="Detalhes…" className={`${FIELD} bg-g-900`} />
                  </div>
                  <div className="w-full sm:w-[56px] shrink-0">
                    <label className={LABEL}>Qtd</label>
                    <input type="number" value={it.qtd_itens} onChange={e => setItem(i, 'qtd_itens', e.target.value)}
                      placeholder="1" className={`${FIELD} bg-g-900`} />
                  </div>
                  <div className="w-full sm:w-7 flex sm:justify-center sm:pb-0.5 mt-1 sm:mt-0 items-end justify-end">
                    {itens.length > 1 && (
                      <button type="button" onClick={() => removeItem(i)}
                        className="p-1.5 text-g-600 hover:text-red-500 transition-colors">
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Observações */}
          <div>
            <label className={LABEL}>Observações</label>
            <textarea rows={2} value={form.observacoes} onChange={e => set('observacoes', e.target.value)}
              placeholder="Observações adicionais…" className={`${FIELD} resize-none`} />
          </div>

          {error && <p className="text-red-500 text-xs bg-red-50/10 border border-red-500/20 rounded-lg px-3 py-2">{error}</p>}
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
