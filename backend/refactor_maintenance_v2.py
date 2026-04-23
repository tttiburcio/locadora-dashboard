import re

with open(r'c:\Users\vinic\Documents\clone\frontend\src\pages\MaintenancePage.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update initial sort states
content = content.replace(
    "const [sortAberta,   setSortAberta]   = useState({ col: null, dir: 'asc' })",
    "const [sortAberta,   setSortAberta]   = useState({ col: 'data_entrada', dir: 'desc' })"
)
content = content.replace(
    "const [sortFin,      setSortFin]      = useState({ col: null, dir: 'asc' })",
    "const [sortFin,      setSortFin]      = useState({ col: 'data_execucao', dir: 'desc' })"
)

# Function to get unique categories/companies
header_helpers = """
function getEmpresasFaturadas(os) {
  if (!os.notas_fiscais || os.notas_fiscais.length === 0) return '—';
  const emp = new Set(os.notas_fiscais.map(nf => nf.empresa_faturada).filter(Boolean));
  if (emp.size === 0) return '—';
  return Array.from(emp).join(', ');
}

"""
content = content.replace('function getFornecedoresUnicos(os) {', header_helpers + 'function getFornecedoresUnicos(os) {')

# 2. Rich Card Template function to be injected in map body
# We will just replace the inner div of the map

# Abertas:
aberta_start = content.find('<div className="flex flex-col gap-3">', content.find('subTab === \'em_andamento\''))
aberta_end = content.find('</div>', content.find('})}', aberta_start)) + 6

new_abertas = """              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {filteredAbertas.map(o => {
                  const dias = o.indisponivel && o.data_entrada ? diasParados(o.data_entrada) : null;
                  const borderCol = o.status_os === 'aguardando_peca' ? 'border-orange-500' :
                                    o.status_os === 'executado_aguardando_nf' ? 'border-purple-500' :
                                    'border-amber-500';
                  
                  return (
                    <div 
                      key={o.id} 
                      onClick={() => setModalDetalhe(o)}
                      className={`border-l-4 ${borderCol} rounded-xl bg-white shadow-sm hover:shadow-md transition-all cursor-pointer p-5 flex flex-col gap-4 relative group`}
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between pb-3 border-b border-g-800">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-mono font-bold text-g-100 text-lg">{o.placa}</span>
                            <span className="text-g-500 text-xs px-2 py-0.5 bg-g-900 rounded-md border border-g-800">{o.numero_os || 'Sem OS'}</span>
                          </div>
                          <span className="text-g-500 text-xs font-medium">{o.modelo || 'Sem modelo'}</span>
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
                      <div className="flex-1 flex flex-col gap-3">
                        <div className="grid grid-cols-2 gap-3">
                          <div className="bg-g-900/50 p-2.5 rounded-lg border border-g-900">
                            <span className="block text-g-600 text-[10px] uppercase font-bold mb-0.5">Entrada</span>
                            <span className="text-g-300 text-xs">{dateBR(o.data_entrada) || '—'}</span>
                          </div>
                          <div className="bg-g-900/50 p-2.5 rounded-lg border border-g-900">
                            <span className="block text-g-600 text-[10px] uppercase font-bold mb-0.5">Mecânico</span>
                            <span className="text-g-300 text-xs truncate block">{o.responsavel_tec || 'Não definido'}</span>
                          </div>
                        </div>

                        <div>
                          <span className="block text-g-600 text-[10px] uppercase font-bold mb-1">Fornecedores</span>
                          <span className="text-g-300 text-xs truncate block" title={getFornecedoresUnicos(o)}>{getFornecedoresUnicos(o)}</span>
                        </div>

                        <div>
                          <span className="block text-g-600 text-[10px] uppercase font-bold mb-1">Serviço Principal</span>
                          <div className="text-g-300 text-xs leading-relaxed line-clamp-2" title={`${o._sistema || ''} - ${o._servico || ''}`}>
                            <span className="font-medium text-g-200">{o._sistema || 'Não informado'}</span>
                            {o._servico && ` — ${o._servico}`}
                          </div>
                        </div>
                        
                        {(o.km || o.prox_km) && (
                          <div className="flex items-center gap-3 pt-2">
                            {o.km && <span className="text-[10px] font-mono text-g-500 border border-g-800 px-1.5 py-0.5 rounded">KM {o.km}</span>}
                            {o.prox_km && <span className="text-[10px] font-mono text-blue-400 border border-blue-900 px-1.5 py-0.5 rounded bg-blue-950/20">Próx: {o.prox_km}</span>}
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
              </div>"""

content = content[:aberta_start] + new_abertas + content[aberta_end:]


# Finalizadas:
fin_start = content.find('<div className="flex flex-col gap-3">', content.find('subTab === \'finalizadas\''))
fin_end = content.find('</div>', content.find('})}', fin_start)) + 6

new_fin = """              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {filteredFin.map(o => {
                  const dias = o.indisponivel && o.data_entrada && o.data_execucao ? diasParados(o.data_entrada, o.data_execucao) : null;
                  const pgtoProgresso = o._totalParcelas > 0 ? Math.round((o._pagas / o._totalParcelas) * 100) : 0;
                  
                  return (
                    <div 
                      key={o.id} 
                      onClick={() => setModalDetalhe(o)}
                      className="border-l-4 border-emerald-500 rounded-xl bg-white shadow-sm hover:shadow-md transition-all cursor-pointer p-5 flex flex-col gap-4 relative group"
                    >
                      {/* Header */}
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

content = content[:fin_start] + new_fin + content[fin_end:]

with open(r'c:\Users\vinic\Documents\clone\frontend\src\pages\MaintenancePage.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("done v2")
