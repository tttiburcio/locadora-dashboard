import re

with open(r'c:\Users\vinic\Documents\clone\frontend\src\pages\MaintenancePage.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add getFornecedoresUnicos
fn_fornecedores = """
function getFornecedoresUnicos(os) {
  if (!os.notas_fiscais || os.notas_fiscais.length === 0) return os.fornecedor || '—';
  const forns = new Set(os.notas_fiscais.map(nf => nf.fornecedor).filter(Boolean));
  if (forns.size === 0) return os.fornecedor || '—';
  return Array.from(forns).join(' / ');
}

"""
content = content.replace('function StatusBadge({ status }) {', fn_fornecedores + 'function StatusBadge({ status }) {')


# 2. Em andamento filter block
old_filter_aberta = """          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-g-600" />
            <input
              value={filterAberta}
              onChange={e => setFilterAberta(e.target.value)}
              placeholder="Filtrar por placa, fornecedor, status, modelo, sistema, serviço…"
              className="w-full pl-9 pr-9 py-2 bg-g-900 border border-g-800 rounded-lg text-g-400 text-sm placeholder-g-700 focus:outline-none focus:border-g-100 transition-colors"
            />
            {filterAberta && (
              <button onClick={() => setFilterAberta('')} className="absolute right-3 top-1/2 -translate-y-1/2">
                <X className="w-3.5 h-3.5 text-g-600 hover:text-g-400" />
              </button>
            )}
          </div>"""

new_filter_aberta = """          <div className="flex items-center gap-3 relative">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-g-600" />
              <input
                value={filterAberta}
                onChange={e => setFilterAberta(e.target.value)}
                placeholder="Filtrar por placa, fornecedor, status, modelo, sistema, serviço…"
                className="w-full pl-9 pr-9 py-2 bg-g-900 border border-g-800 rounded-lg text-g-400 text-sm placeholder-g-700 focus:outline-none focus:border-g-100 transition-colors"
              />
              {filterAberta && (
                <button onClick={() => setFilterAberta('')} className="absolute right-3 top-1/2 -translate-y-1/2">
                  <X className="w-3.5 h-3.5 text-g-600 hover:text-g-400" />
                </button>
              )}
            </div>
            <select
              value={`${sortAberta.col || 'data_entrada'}-${sortAberta.dir}`}
              onChange={e => {
                const [col, dir] = e.target.value.split('-');
                setSortAberta({ col, dir });
              }}
              className="w-48 px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm focus:outline-none focus:border-g-100 transition-colors cursor-pointer"
            >
              <option value="data_entrada-desc">Mais recentes</option>
              <option value="data_entrada-asc">Mais antigas</option>
              <option value="placa-asc">Placa (A-Z)</option>
              <option value="status_os-asc">Status</option>
            </select>
          </div>"""

content = content.replace(old_filter_aberta, new_filter_aberta)

# 3. Em Andamento table replacement
# Find <div className="overflow-x-auto"> to </div> around line 618
aberta_table_start = content.find('<div className="overflow-x-auto">')
aberta_table_end = content.find('</div>', content.find('</table>', aberta_table_start)) + 6

new_aberta_list = """              <div className="flex flex-col gap-3">
                {filteredAbertas.map(o => {
                  const dias = o.indisponivel && o.data_entrada ? diasParados(o.data_entrada) : null;
                  const borderCol = o.status_os === 'aguardando_peca' ? 'border-orange-500' :
                                    o.status_os === 'executado_aguardando_nf' ? 'border-purple-500' :
                                    'border-amber-500';
                  
                  return (
                    <div 
                      key={o.id} 
                      onClick={() => setModalDetalhe(o)}
                      className={`border-l-4 ${borderCol} rounded-lg bg-white shadow-sm hover:shadow-md transition-shadow cursor-pointer p-4 flex flex-col gap-3`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <span className="font-mono font-bold text-g-200 text-sm">{o.placa}</span>
                          <span className="text-g-500 text-xs">{o.modelo || '—'}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-g-600 text-xs font-mono">{o.numero_os || 'Sem OS'}</span>
                          <StatusBadge status={o.status_os} />
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-3 gap-4">
                        <div>
                          <span className="block text-g-600 text-[10px] uppercase font-semibold mb-1">Fornecedor</span>
                          <span className="text-g-300 text-xs truncate block" title={getFornecedoresUnicos(o)}>{getFornecedoresUnicos(o)}</span>
                        </div>
                        <div>
                          <span className="block text-g-600 text-[10px] uppercase font-semibold mb-1">Serviço / Sistema</span>
                          <span className="text-g-300 text-xs truncate block" title={`${o._sistema || ''} - ${o._servico || ''}`}>{o._sistema || '—'} - {o._servico || '—'}</span>
                        </div>
                        <div className="text-right">
                          <span className="block text-g-600 text-[10px] uppercase font-semibold mb-1">Tempo / Entrada</span>
                          <span className="text-g-300 text-xs">
                            {dias !== null
                                ? <span className={dias > 30 ? 'text-red-500 font-semibold' : dias > 7 ? 'text-amber-500 font-medium' : 'text-g-500'}>{dias} dias</span>
                                : <span className="text-g-700">—</span>}
                            {' • '}{dateBR(o.data_entrada)}
                          </span>
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-end border-t border-g-800 pt-3 mt-1" onClick={e => e.stopPropagation()}>
                          <div className="flex items-center gap-2">
                              {o.status_os === 'em_andamento' && (
                                <button
                                  onClick={() => handleStatusChange(o, 'aguardando_peca')}
                                  title="Marcar como aguardando peça"
                                  className="px-3 py-1.5 text-xs font-medium text-orange-600 bg-orange-50/50 hover:bg-orange-50 rounded-lg transition-colors"
                                >
                                  Ag. peça
                                </button>
                              )}
                              {o.status_os === 'aguardando_peca' && (
                                <button
                                  onClick={() => handleStatusChange(o, 'em_andamento')}
                                  title="Retomar andamento"
                                  className="px-3 py-1.5 text-xs font-medium text-amber-600 bg-amber-50/50 hover:bg-amber-50 rounded-lg transition-colors"
                                >
                                  Retomar
                                </button>
                              )}
                              <button
                                onClick={() => setModalEdit(o)}
                                title="Editar OS"
                                className="px-3 py-1.5 text-xs font-medium text-g-500 bg-g-850 hover:text-g-200 hover:bg-g-800 rounded-lg transition-colors flex items-center gap-1.5"
                              >
                                <Pencil className="w-3.5 h-3.5" /> Editar
                              </button>
                              <button
                                onClick={() => setModalFin(o)}
                                className="px-3 py-1.5 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded-lg transition-colors"
                              >
                                Finalizar
                              </button>
                              <button
                                onClick={() => setConfirmDel(o.id)}
                                className="p-1.5 text-g-600 hover:text-red-500 bg-g-850 hover:bg-red-50 rounded-lg transition-colors ml-1"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                          </div>
                      </div>
                    </div>
                  )
                })}
              </div>"""

content = content[:aberta_table_start] + new_aberta_list + content[aberta_table_end:]


# 4. Finalizadas filter block
old_filter_fin = """          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-g-600" />
            <input
              value={filterFin}
              onChange={e => setFilterFin(e.target.value)}
              placeholder="Filtrar por placa, fornecedor, modelo, sistema, serviço, nº OS…"
              className="w-full pl-9 pr-9 py-2 bg-g-900 border border-g-800 rounded-lg text-g-400 text-sm placeholder-g-700 focus:outline-none focus:border-g-100 transition-colors"
            />
            {filterFin && (
              <button onClick={() => setFilterFin('')} className="absolute right-3 top-1/2 -translate-y-1/2">
                <X className="w-3.5 h-3.5 text-g-600 hover:text-g-400" />
              </button>
            )}
          </div>"""

new_filter_fin = """          <div className="flex items-center gap-3 relative">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-g-600" />
              <input
                value={filterFin}
                onChange={e => setFilterFin(e.target.value)}
                placeholder="Filtrar por placa, fornecedor, modelo, sistema, serviço, nº OS…"
                className="w-full pl-9 pr-9 py-2 bg-g-900 border border-g-800 rounded-lg text-g-400 text-sm placeholder-g-700 focus:outline-none focus:border-g-100 transition-colors"
              />
              {filterFin && (
                <button onClick={() => setFilterFin('')} className="absolute right-3 top-1/2 -translate-y-1/2">
                  <X className="w-3.5 h-3.5 text-g-600 hover:text-g-400" />
                </button>
              )}
            </div>
            <select
              value={`${sortFin.col || 'data_execucao'}-${sortFin.dir}`}
              onChange={e => {
                const [col, dir] = e.target.value.split('-');
                setSortFin({ col, dir });
              }}
              className="w-48 px-3 py-2 bg-g-900 border border-g-800 rounded-lg text-g-300 text-sm focus:outline-none focus:border-g-100 transition-colors cursor-pointer"
            >
              <option value="data_execucao-desc">Mais recentes</option>
              <option value="data_execucao-asc">Mais antigas</option>
              <option value="placa-asc">Placa (A-Z)</option>
              <option value="_totalNfs-desc">Maior valor</option>
              <option value="_totalNfs-asc">Menor valor</option>
            </select>
          </div>"""

content = content.replace(old_filter_fin, new_filter_fin)

# 5. Finalizada table replacement
fin_table_start = content.find('<div className="overflow-x-auto">', content.find('filteredFin.length === 0'))
fin_table_end = content.find('</div>', content.find('</table>', fin_table_start)) + 6

new_fin_list = """              <div className="flex flex-col gap-3">
                {filteredFin.map(o => {
                  const dias = o.indisponivel && o.data_entrada && o.data_execucao ? diasParados(o.data_entrada, o.data_execucao) : null;
                  return (
                    <div 
                      key={o.id} 
                      onClick={() => setModalDetalhe(o)}
                      className={`border-l-4 border-emerald-500 rounded-lg bg-white shadow-sm hover:shadow-md transition-shadow cursor-pointer p-4 flex flex-col gap-3`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <span className="font-mono font-bold text-g-200 text-sm">{o.placa}</span>
                          <span className="text-g-500 text-xs">{o.modelo || '—'}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-g-600 text-xs font-mono">{o.numero_os || 'Sem OS'}</span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50/50 text-emerald-600 border border-emerald-200/50">FINALIZADA</span>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-4 gap-4">
                        <div className="col-span-1">
                          <span className="block text-g-600 text-[10px] uppercase font-semibold mb-1">Fornecedor</span>
                          <span className="text-g-300 text-xs truncate block" title={getFornecedoresUnicos(o)}>{getFornecedoresUnicos(o)}</span>
                        </div>
                        <div className="col-span-1">
                          <span className="block text-g-600 text-[10px] uppercase font-semibold mb-1">Serviço / Sistema</span>
                          <span className="text-g-300 text-xs truncate block" title={`${o._sistema || ''} - ${o._servico || ''}`}>{o._sistema || '—'} - {o._servico || '—'}</span>
                        </div>
                        <div className="col-span-1 text-right">
                          <span className="block text-g-600 text-[10px] uppercase font-semibold mb-1">Total OS</span>
                          <span className="text-g-200 text-sm font-bold font-mono">{brl(o._totalNfs)}</span>
                        </div>
                        <div className="col-span-1 text-right">
                          <span className="block text-g-600 text-[10px] uppercase font-semibold mb-1">Execução</span>
                          <span className="text-g-300 text-xs">
                            {dateBR(o.data_execucao)}
                            {dias !== null && <span className="ml-2 text-g-600">({dias} d)</span>}
                          </span>
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between border-t border-g-800 pt-3 mt-1">
                          <div className="text-xs text-g-500 flex items-center gap-3">
                            <span>Parcelas pagas: <span className="font-medium text-g-300">{o._pagas} / {o._totalParcelas}</span></span>
                          </div>
                          <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
                              <button
                                onClick={() => setModalEdit(o)}
                                title="Editar OS"
                                className="px-3 py-1.5 text-xs font-medium text-g-500 bg-g-850 hover:text-g-200 hover:bg-g-800 rounded-lg transition-colors flex items-center gap-1.5"
                              >
                                <Pencil className="w-3.5 h-3.5" /> Editar
                              </button>
                              <button
                                onClick={() => setConfirmDel(o.id)}
                                className="p-1.5 text-g-600 hover:text-red-500 bg-g-850 hover:bg-red-50 rounded-lg transition-colors ml-1"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                          </div>
                      </div>
                    </div>
                  )
                })}
              </div>"""

content = content[:fin_table_start] + new_fin_list + content[fin_table_end:]

with open(r'c:\Users\vinic\Documents\clone\frontend\src\pages\MaintenancePage.jsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("Replacement Complete")
