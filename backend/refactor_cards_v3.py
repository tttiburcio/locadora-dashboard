with open(r'c:\Users\vinic\Documents\clone\frontend\src\pages\MaintenancePage.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# ── 1. Improve getEmpresasFaturadas to map codes to full names ──────────────
EMPRESA_NAMES = {
    'TKJ': 'TKJ Gerenciamento',
    'FINITA': 'Finita Locações',
    'LANDKRAFT': 'Landkraft',
    '1': 'TKJ Gerenciamento',
    '2': 'Finita Locações',
    '3': 'Landkraft',
}

old_get_emp = """function getEmpresasFaturadas(os) {
  if (!os.notas_fiscais || os.notas_fiscais.length === 0) return '—';
  const emp = new Set(os.notas_fiscais.map(nf => nf.empresa_faturada).filter(Boolean));
  if (emp.size === 0) return '—';
  return Array.from(emp).join(', ');
}"""

new_get_emp = """const EMPRESA_NOME_MAP = {
  'TKJ': 'TKJ Gerenciamento',
  'FINITA': 'Finita Locações',
  'LANDKRAFT': 'Landkraft',
  '1': 'TKJ Gerenciamento', '2': 'Finita Locações', '3': 'Landkraft',
}
function resolveEmpresaNome(cod) {
  if (!cod) return null
  return EMPRESA_NOME_MAP[String(cod).toUpperCase()] || EMPRESA_NOME_MAP[String(parseInt(cod))] || cod
}
function getEmpresasFaturadas(os) {
  if (!os.notas_fiscais || os.notas_fiscais.length === 0) return '—';
  const emp = new Set(os.notas_fiscais.map(nf => resolveEmpresaNome(nf.empresa_faturada)).filter(Boolean));
  if (emp.size === 0) return '—';
  return Array.from(emp).join(' · ');
}"""

content = content.replace(old_get_emp, new_get_emp)

# ── 2. Replace the Finalizadas card with a premium redesign ─────────────────
old_fin_card_start = """              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px', padding: '24px' }}>
                {filteredFin.map(o => {
                  const dias = o.indisponivel && o.data_entrada && o.data_execucao ? diasParados(o.data_entrada, o.data_execucao) : null;
                  const pgtoProgresso = o._totalParcelas > 0 ? Math.round((o._pagas / o._totalParcelas) * 100) : 0;
                  
                  return (
                    <div 
                      key={o.id} 
                      onClick={() => setModalDetalhe(o)}
                      className="border-l-4 border-emerald-500 rounded-xl bg-white shadow-sm hover:shadow-md transition-all cursor-pointer p-5 flex flex-col gap-4 relative group"
                    >"""

new_fin_card_start = """              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px', padding: '24px' }}>
                {filteredFin.map(o => {
                  const dias = o.indisponivel && o.data_entrada && o.data_execucao ? diasParados(o.data_entrada, o.data_execucao) : null;
                  const pgtoProgresso = o._totalParcelas > 0 ? Math.round((o._pagas / o._totalParcelas) * 100) : 0;
                  const pagoTotal = o._totalParcelas > 0 && o._pagas === o._totalParcelas
                  const pagoNenhum = o._pagas === 0
                  const pagoParc = !pagoTotal && !pagoNenhum
                  const borderColor = pagoTotal ? '#10b981' : pagoParc ? '#f59e0b' : '#ef4444'
                  const pgStatusLabel = pagoTotal ? 'Quitado' : pagoParc ? `${o._pagas}/${o._totalParcelas} pagas` : 'Não pago'
                  const pgStatusCls = pagoTotal ? 'text-emerald-600 bg-emerald-50' : pagoParc ? 'text-amber-600 bg-amber-50' : 'text-red-500 bg-red-50'
                  const pgBarColor = pagoTotal ? '#10b981' : pagoParc ? '#f59e0b' : '#ef4444'
                  
                  return (
                    <div
                      key={o.id}
                      onClick={() => setModalDetalhe(o)}
                      style={{ borderLeftColor: borderColor }}
                      className="border-l-[5px] rounded-xl bg-white shadow-md hover:shadow-lg transition-all cursor-pointer flex flex-col overflow-hidden"
                    >"""

content = content.replace(old_fin_card_start, new_fin_card_start)

# Replace card body with new premium version
old_fin_body = """                      {/* Header */}
                      <div className="flex items-start justify-between pb-3 border-b border-g-800">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-mono font-bold text-g-100 text-lg">{o.placa}</span>
                            <span className="text-g-500 text-xs px-2 py-0.5 bg-g-900 rounded-md border border-g-800">{o.numero_os || 'Sem OS'}</span>
                          </div>
                          <span className="text-g-500 text-xs font-medium">{o.modelo || 'Sem modelo'}</span>
                        </div>
                        <div className="flex flex-col items-end gap-1.5">
                          <span className="px-2 py-1 rounded text-[10px] font-bold bg-emerald-50/80 text-emerald-600 border border-emerald-200">FINALIZADA</span>
                          <span className="text-g-500 text-xs font-medium">{dateBR(o.data_execucao)}</span>
                        </div>
                      </div>
                      
                      {/* Body Info */}
                      <div className="flex-1 flex flex-col gap-3">
                        <div className="grid grid-cols-2 gap-3">
                          <div className="bg-g-900/40 p-2.5 rounded-lg border border-g-900">
                            <span className="block text-g-600 text-[10px] uppercase font-bold mb-0.5">Empresas Faturadas</span>
                            <span className="text-g-300 text-xs truncate block" title={getEmpresasFaturadas(o)}>{getEmpresasFaturadas(o)}</span>
                          </div>
                          <div className="bg-emerald-50/30 p-2.5 rounded-lg border border-emerald-100/50">
                            <span className="block text-emerald-800/70 text-[10px] uppercase font-bold mb-0.5">Custo Total OS</span>
                            <span className="text-emerald-600 text-sm font-bold font-mono truncate block">{brl(o._totalNfs)}</span>
                          </div>
                        </div>

                        <div>
                          <span className="block text-g-600 text-[10px] uppercase font-bold mb-1">Fornecedores Origem</span>
                          <span className="text-g-400 text-xs truncate block" title={getFornecedoresUnicos(o)}>{getFornecedoresUnicos(o)}</span>
                        </div>

                        <div>
                          <span className="block text-g-600 text-[10px] uppercase font-bold mb-1">Serviço Realizado</span>
                          <div className="text-g-300 text-xs leading-relaxed line-clamp-2" title={`${o._sistema || ''} - ${o._servico || ''}`}>
                            <span className="font-medium text-g-200">{o._sistema || 'Não informado'}</span>
                            {o._servico && ` — ${o._servico}`}
                          </div>
                        </div>
                        
                        {(o.km || o.prox_km || dias !== null) && (
                          <div className="flex items-center gap-2 pt-2 flex-wrap">
                            {o.km && <span className="text-[10px] font-mono text-g-500 border border-g-800 px-1.5 py-0.5 rounded">KM {o.km}</span>}
                            {o.prox_km && <span className="text-[10px] font-mono text-blue-400 border border-blue-900 px-1.5 py-0.5 rounded bg-blue-950/20">Próx: {o.prox_km}</span>}
                            {dias !== null && <span className="text-[10px] font-mono text-g-500 border border-g-800 px-1.5 py-0.5 rounded">{dias} dias off</span>}
                          </div>
                        )}
                      </div>
                      
                      {/* Footer Actions & Progress */}
                      <div className="border-t border-g-800 pt-3 mt-1 flex items-center justify-between">
                          <div className="flex-1 mr-4">
                            <div className="flex justify-between items-center mb-1.5">
                              <span className="text-[10px] uppercase font-bold text-g-500">Pagamento</span>
                              <span className="text-[10px] font-mono font-medium text-g-400">{o._pagas} / {o._totalParcelas} pagas</span>
                            </div>
                            <div className="h-1.5 w-full bg-g-850 rounded-full overflow-hidden border border-g-800">
                              <div className="h-full bg-emerald-500 transition-all duration-500" style={{ width: `${pgtoProgresso}%` }} />
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-1 shrink-0" onClick={e => e.stopPropagation()}>
                              <button
                                onClick={() => setModalEdit(o)}
                                title="Editar OS"
                                className="p-2 text-g-500 bg-g-900 border border-g-800 hover:text-g-100 hover:bg-g-850 rounded-lg transition-colors"
                              >
                                <Pencil className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => setConfirmDel(o.id)}
                                className="p-2 text-g-500 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                          </div>
                      </div>
                    </div>
                  )
                })}
              </div>"""

new_fin_body = """                      {/* Header com gradiente sutil */}
                      <div className="px-5 pt-5 pb-4" style={{ background: 'linear-gradient(135deg, rgba(16,185,129,0.04) 0%, transparent 60%)' }}>
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <div className="flex items-center gap-2.5 mb-1">
                              <span className="font-mono font-extrabold text-g-100" style={{ fontSize: '1.25rem', letterSpacing: '-0.02em' }}>{o.placa}</span>
                              <span className="text-g-400 font-mono text-sm font-semibold">{o.numero_os || ''}</span>
                            </div>
                            <span className="text-g-500 text-sm">{o.modelo || 'Sem modelo'}</span>
                          </div>
                          <div className="text-right">
                            <div className="font-mono font-extrabold text-g-100" style={{ fontSize: '1.1rem' }}>{brl(o._totalNfs)}</div>
                            <div className="text-g-600 text-xs mt-0.5">{dateBR(o.data_execucao)}</div>
                          </div>
                        </div>

                        {/* Empresa faturada destaque */}
                        <div className="flex items-center gap-2 flex-wrap">
                          {o.notas_fiscais && o.notas_fiscais.length > 0
                            ? [...new Set(o.notas_fiscais.map(nf => resolveEmpresaNome(nf.empresa_faturada)).filter(Boolean))].map(emp => (
                              <span key={emp} className="text-xs font-semibold px-2.5 py-1 rounded-full" style={{ background: 'rgba(99,102,241,0.12)', color: '#818cf8' }}>{emp}</span>
                            ))
                            : <span className="text-g-600 text-xs">Empresa não informada</span>
                          }
                        </div>
                      </div>

                      {/* Divisor */}
                      <div style={{ height: '1px', background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent)' }} />
                      
                      {/* Corpo informações */}
                      <div className="px-5 py-4 flex flex-col gap-3 flex-1">
                        <div>
                          <div className="text-g-600 text-xs font-semibold uppercase tracking-wider mb-1">Fornecedor</div>
                          <div className="text-g-300 text-sm font-medium truncate" title={getFornecedoresUnicos(o)}>{getFornecedoresUnicos(o)}</div>
                        </div>

                        <div>
                          <div className="text-g-600 text-xs font-semibold uppercase tracking-wider mb-1">Serviço</div>
                          <div className="text-g-300 text-sm line-clamp-2 leading-relaxed">
                            {o._sistema && <span className="text-g-200 font-semibold">{o._sistema}</span>}
                            {o._servico && <span className="text-g-500"> · {o._servico}</span>}
                            {!o._sistema && !o._servico && <span className="text-g-700 italic">Não informado</span>}
                          </div>
                        </div>

                        {(o.km || dias !== null) && (
                          <div className="flex items-center gap-2 flex-wrap">
                            {o.km && (
                              <span className="inline-flex items-center gap-1 text-xs font-mono text-g-500 border border-g-800 px-2 py-0.5 rounded-md">
                                {o.km} km
                              </span>
                            )}
                            {dias !== null && (
                              <span className="inline-flex items-center gap-1 text-xs text-g-600 border border-g-800 px-2 py-0.5 rounded-md">
                                {dias}d na oficina
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                      
                      {/* Footer: barra de pagamento */}
                      <div className="px-5 pb-4 pt-3 border-t border-g-800">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-semibold text-g-500 uppercase tracking-wider">Pagamento</span>
                          <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full ${pgStatusCls}`}>{pgStatusLabel}</span>
                        </div>
                        <div style={{ height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '999px', overflow: 'hidden' }}>
                          <div style={{ width: `${pgtoProgresso}%`, height: '100%', background: pgBarColor, borderRadius: '999px', transition: 'width 0.5s ease' }} />
                        </div>
                        <div className="flex items-center justify-end gap-1 mt-3" onClick={e => e.stopPropagation()}>
                          <button onClick={() => setModalEdit(o)} title="Editar" className="p-1.5 text-g-600 hover:text-g-300 rounded-lg hover:bg-g-850 transition-colors">
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
              </div>"""

content = content.replace(old_fin_body, new_fin_body)

with open(r'c:\Users\vinic\Documents\clone\frontend\src\pages\MaintenancePage.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("done v3")
