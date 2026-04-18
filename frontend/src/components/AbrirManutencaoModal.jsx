import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { X, Loader2, Wrench } from 'lucide-react'
import { dbListFrota, dbAbrirManutencao, dbAtualizarManutencao } from '../utils/api'

const STATUS_OPTS = [
  { value: 'em_andamento',    label: 'Em andamento' },
  { value: 'aguardando_peca', label: 'Aguardando peça' },
  { value: 'pendente',        label: 'Pendente' },
]

const TIPO_OPTS = ['Preventiva', 'Corretiva']

const SISTEMAS = [
  'Motor', 'Freio', 'Suspensão', 'Elétrico', 'Câmbio', 'Diferencial',
  'Direção', 'Implemento', 'Guincho', 'Pneu', 'Hidráulico', 'Arrefecimento', 'Outro',
]

const FIELD = 'w-full px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm placeholder-g-700 focus:outline-none focus:border-g-100 transition-colors'
const LABEL = 'text-g-600 text-xs font-medium mb-1 block'

export default function AbrirManutencaoModal({ onClose, onSaved, manutencao = null }) {
  const isEditMode = manutencao !== null

  const [frota,        setFrota]        = useState([])
  const [loadingFrota, setLoadingFrota] = useState(true)
  const [saving,       setSaving]       = useState(false)
  const [error,        setError]        = useState(null)

  const [form, setForm] = useState(() => {
    if (manutencao) {
      return {
        id_veiculo:        manutencao.id_veiculo ?? '',
        placa:             manutencao.placa ?? '',
        modelo:            manutencao.modelo ?? '',
        fornecedor:        manutencao.fornecedor ?? '',
        tipo_manutencao:   manutencao.tipo_manutencao ?? 'Corretiva',
        sistema:           manutencao.sistema ?? '',
        servico:           manutencao.servico ?? '',
        descricao:         manutencao.descricao ?? '',
        km:                manutencao.km ?? '',
        responsavel_tec:   manutencao.responsavel_tec ?? '',
        indisponivel:      manutencao.indisponivel ?? true,
        data_entrada:      manutencao.data_entrada ?? new Date().toISOString().slice(0, 10),
        status_manutencao: manutencao.status_manutencao ?? '',
        observacoes:       manutencao.observacoes ?? '',
      }
    }
    return {
      id_veiculo:      '',
      placa:           '',
      modelo:          '',
      fornecedor:      '',
      tipo_manutencao: 'Corretiva',
      sistema:         '',
      servico:         '',
      descricao:       '',
      km:              '',
      responsavel_tec: '',
      indisponivel:    true,
      data_entrada:    new Date().toISOString().slice(0, 10),
      status_manutencao: '',
      observacoes:     '',
    }
  })

  useEffect(() => {
    setLoadingFrota(true)
    dbListFrota()
      .then(setFrota)
      .catch(() => setError('Não foi possível carregar a lista de veículos. Verifique se o backend está rodando.'))
      .finally(() => setLoadingFrota(false))
  }, [])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handlePlaca = (e) => {
    const placa = e.target.value.toUpperCase()
    const v = frota.find(f => f.placa === placa)
    setForm(f => ({
      ...f,
      placa,
      id_veiculo: v?.id   || '',
      modelo:     v?.modelo || f.modelo,
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.placa)             { setError('Selecione a placa do veículo'); return }
    if (!form.id_veiculo)        { setError('Placa não encontrada na frota'); return }
    if (!form.status_manutencao) { setError('Selecione o status inicial'); return }
    setSaving(true)
    setError(null)
    try {
      const payload = {
        ...form,
        id_veiculo: parseInt(form.id_veiculo),
        km: form.km ? parseFloat(form.km) : null,
      }
      if (isEditMode) {
        await dbAtualizarManutencao(manutencao.id, payload)
      } else {
        await dbAbrirManutencao(payload)
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
      <div className="bg-g-900 border border-g-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col animate-fade-up">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-g-800">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 bg-g-850 border border-g-800 rounded-lg">
              <Wrench className="w-4 h-4 text-g-100" />
            </div>
            <div>
              <h2 className="text-g-200 font-semibold text-sm">
                {isEditMode ? 'Editar Manutenção' : 'Registrar Manutenção'}
              </h2>
              <p className="text-g-600 text-xs">
                {isEditMode ? `Editando OS · ${manutencao.placa}` : 'Veículo entrando em manutenção'}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-g-600 hover:text-g-300 hover:bg-g-850 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="overflow-y-auto px-5 py-4 flex flex-col gap-4">

          {/* Veículo */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className={LABEL}>Placa *</label>
              <select value={form.placa} onChange={handlePlaca} className={`${FIELD} font-mono`} required disabled={loadingFrota || isEditMode}>
                <option value="">{loadingFrota ? 'Carregando…' : frota.length === 0 ? 'Nenhum veículo encontrado' : 'Selecione…'}</option>
                {frota.map(v => (
                  <option key={v.id} value={v.placa}>{v.placa}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={LABEL}>Modelo</label>
              <input
                value={form.modelo}
                disabled
                placeholder="Preenchido ao selecionar placa"
                className={`${FIELD} bg-g-850 text-g-500 cursor-default opacity-70`}
              />
            </div>
            <div>
              <label className={LABEL}>Data de Entrada *</label>
              <input
                type="date" value={form.data_entrada}
                onChange={e => set('data_entrada', e.target.value)}
                className={FIELD} required
              />
            </div>
          </div>

          {/* Fornecedor + Tipo */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={LABEL}>Fornecedor / Oficina</label>
              <input
                placeholder="Nome da oficina…"
                value={form.fornecedor}
                onChange={e => set('fornecedor', e.target.value.toUpperCase().replace(/[^A-Z\s]/g, ''))}
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

          {/* Sistema + Serviço */}
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
                placeholder="Ex: Troca de óleo, Alinhamento…"
                value={form.servico}
                onChange={e => set('servico', e.target.value)}
                className={FIELD}
              />
            </div>
          </div>

          {/* Descrição */}
          <div>
            <label className={LABEL}>Descrição do Problema / Serviço</label>
            <textarea
              rows={2}
              placeholder="Descreva o problema ou serviço a ser executado…"
              value={form.descricao}
              onChange={e => set('descricao', e.target.value)}
              className={`${FIELD} resize-none`}
            />
          </div>

          {/* KM + Responsável + Status */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className={LABEL}>KM Atual</label>
              <input
                type="number" placeholder="Ex: 125000"
                value={form.km}
                onChange={e => set('km', e.target.value)}
                className={FIELD}
              />
            </div>
            <div>
              <label className={LABEL}>Responsável Técnico</label>
              <input
                placeholder="Nome…"
                value={form.responsavel_tec}
                onChange={e => set('responsavel_tec', e.target.value)}
                className={FIELD}
              />
            </div>
            <div>
              <label className={LABEL}>Status Inicial</label>
              <select value={form.status_manutencao} onChange={e => set('status_manutencao', e.target.value)} className={FIELD} required>
                <option value="">Selecione…</option>
                {STATUS_OPTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </div>

          {/* Indisponível + Observações */}
          <div className="flex items-start gap-4">
            <label className="flex items-center gap-2 cursor-pointer mt-0.5">
              <input
                type="checkbox"
                checked={form.indisponivel}
                onChange={e => set('indisponivel', e.target.checked)}
                className="w-4 h-4 accent-g-100 rounded"
              />
              <span className="text-g-500 text-sm">Veículo indisponível (parado)</span>
            </label>
          </div>

          <div>
            <label className={LABEL}>Observações</label>
            <textarea
              rows={2}
              placeholder="Observações adicionais…"
              value={form.observacoes}
              onChange={e => set('observacoes', e.target.value)}
              className={`${FIELD} resize-none`}
            />
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
            {isEditMode ? 'Salvar Alterações' : 'Registrar OS'}
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}
