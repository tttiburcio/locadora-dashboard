import re

with open(r'c:\Users\vinic\Documents\clone\frontend\src\components\FinalizarOsModal.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add mapBackendNfToState after NF_VAZIA
map_fn = """
function mapBackendNfToState(nfBackend, osItens) {
  return {
    id:               nfBackend.id,
    is_saved:         true,
    tipo_nf:          nfBackend.tipo_nf || 'Servico',
    numero_nf:        nfBackend.numero_nf || '',
    empresa_faturada: nfBackend.empresa_faturada || '',
    fornecedor:       nfBackend.fornecedor || '',
    valor_total_nf:   nfBackend.valor_total_nf ? String(nfBackend.valor_total_nf) : '',
    data_emissao:     nfBackend.data_emissao ? String(nfBackend.data_emissao).slice(0, 10) : '',
    observacoes:      nfBackend.observacoes || '',
    qtd_parcelas:     String(nfBackend.parcelas?.length || 1),
    itens: osItens.map(it => {
      const nfItem = (nfBackend.itens || []).find(ni => ni.os_item_id === it.id)
      return {
        os_item_id:       it.id,
        _categoria:       it.categoria ?? '',
        _sistema:         it.sistema   ?? '',
        _servico:         it.servico   ?? '',
        quantidade:       nfItem ? String(nfItem.quantidade) : '1',
        valor_unitario:   nfItem && nfItem.valor_unitario ? String(nfItem.valor_unitario) : '',
        valor_total_item: nfItem && nfItem.valor_total_item ? String(nfItem.valor_total_item) : '',
        incluir:          !!nfItem,
      }
    }),
    parcelas: (nfBackend.parcelas || []).map(p => ({
      data_vencimento:  p.data_vencimento ? String(p.data_vencimento).slice(0, 10) : '',
      valor_parcela:    p.valor_parcela ? String(p.valor_parcela) : '',
      forma_pgto:       p.forma_pgto || 'Faturado',
      status_pagamento: p.status_pagamento || 'Pendente',
    }))
  }
}
"""
content = content.replace('})\n\nfunction validarLocal', '})\n' + map_fn + '\nfunction validarLocal')

# 2. Add is_saved: false to NF_VAZIA
content = content.replace('tipo_nf:          \'Servico\',', 'is_saved:         false,\n  tipo_nf:          \'Servico\',')

# 3. Initialize nfs with os.notas_fiscais
init_old = 'const [nfs, setNfs] = useState([NF_VAZIA(os.itens || [])])'
init_new = 'const [nfs, setNfs] = useState(os.notas_fiscais?.length > 0 ? os.notas_fiscais.map(nf => mapBackendNfToState(nf, os.itens || [])) : [NF_VAZIA(os.itens || [])])'
content = content.replace(init_old, init_new)

# 4. Add salvarNfEspecifica function
salvar_spec = """
  const salvarNfEspecifica = async (ni) => {
    const nf = nfs[ni]
    if (!nf.empresa_faturada || !nf.valor_total_nf || nf.parcelas.length === 0) {
       setError(`Preencha a Empresa e o Valor Total da ${nfLabel(nf, ni)} antes de salvar.`)
       return
    }
    setSaving(true); setError(null)
    try {
      const payloadNfs = nfs.filter(n => n.tipo_nf).map(buildNfPayload)
      if (payloadNfs.length > 0) {
        await dbSyncNfs(os.id, payloadNfs)
      }
      setNf(ni, 'is_saved', true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao salvar NF')
    } finally {
      setSaving(false)
    }
  }
"""
content = content.replace('const salvarNfsParcial = async () => {', salvar_spec + '\n  const salvarNfsParcial = async () => {')

# 5. Remove Salvar NFs from footer
footer_old = """<button onClick={salvarNfsParcial} disabled={saving}
                  className="px-4 py-2 rounded-lg border border-g-800 text-g-400 text-sm hover:bg-g-850 disabled:opacity-50 transition-colors flex items-center gap-2">
                  {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Salvar NF
                </button>"""
content = content.replace(footer_old, "")

# 6. Render expanded/collapsed NFs
render_old = '<div key={ni} className="border border-g-800 rounded-xl overflow-hidden shrink-0">'
render_new = """{nf.is_saved ? (
                  <div key={ni} className="border border-g-800 rounded-xl bg-g-850 px-4 py-3 flex items-center justify-between shrink-0">
                    <div className="flex items-center gap-3">
                      <span className="text-emerald-500 bg-emerald-500/10 p-1.5 rounded-lg"><CheckCircle className="w-4 h-4"/></span>
                      <div>
                        <span className="text-g-200 font-medium text-sm block">{nfLabel(nf, ni)} {nf.numero_nf ? `· ${nf.numero_nf}` : ''}</span>
                        <span className="text-g-500 text-xs">{nf.fornecedor || 'Sem fornecedor'} · {brl(nf.valor_total_nf)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button type="button" onClick={() => setNf(ni, 'is_saved', false)} className="text-g-400 hover:text-g-200 text-xs font-medium px-3 py-1.5 bg-g-800 rounded-lg transition-colors">Editar</button>
                    </div>
                  </div>
                ) : (
                  <div key={ni} className="border border-g-800 rounded-xl overflow-hidden shrink-0">"""
content = content.replace(render_old, render_new)

# 7. Add Save button inside the expanded NF
card_end = '{/* Parcela section was here, end of p-5 div */}'
# Find where the p-5 div ends. It ends at the very end of the map callback block.
# We will inject the button just before the closing </div> of the p-5 div, which is before `</div>` that closes the map block.
# A simpler way is to replace the closing `</div>` of the p-5 container.
# Looking at FinalizarOsModal, there is `</div>` closing `p-5` right before `</div>` closing the `border-g-800` div.
# We will just inject it by replacing:
injection_target = """                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}"""

button_html = """                          </div>
                        </div>
                        <div className="mt-4 pt-4 border-t border-g-800 flex justify-end">
                          <button type="button" onClick={() => salvarNfEspecifica(ni)} disabled={saving} className="px-4 py-2 rounded-lg bg-emerald-600/20 text-emerald-500 text-sm hover:bg-emerald-600/30 font-medium transition-colors flex items-center gap-2">
                            {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                            Salvar NF
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                )
              })}"""
content = content.replace(injection_target, button_html)

with open(r'c:\Users\vinic\Documents\clone\frontend\src\components\FinalizarOsModal.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated FinalizarOsModal.jsx")
