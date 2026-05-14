import os

file_path = r"c:\Users\ADM\Documents\locadora-dashboard\frontend\src\pages\MaintenancePage.jsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Apply Sort Logic
orig_sort = """    r = [...r].sort((a, b) => {
      const av = a[col] ?? '', bv = b[col] ?? ''
      // Try date comparison first (ISO strings like 2026-04-22)
      const ad = Date.parse(av), bd = Date.parse(bv)
      if (!isNaN(ad) && !isNaN(bd)) return dir === 'asc' ? ad - bd : bd - ad
      // Numeric comparison
      const an = parseFloat(av), bn = parseFloat(bv)
      if (!isNaN(an) && !isNaN(bn)) return dir === 'asc' ? an - bn : bn - an
      // String comparison
      const as = av.toString().toLowerCase(), bs = bv.toString().toLowerCase()
      return dir === 'asc' ? (as < bs ? -1 : as > bs ? 1 : 0) : (as > bs ? -1 : as < bs ? 1 : 0)
    })"""

new_sort = """    r = [...r].sort((a, b) => {
      const av = a[col] ?? '', bv = b[col] ?? ''
      let diff = 0
      // Try date comparison first (ISO strings like 2026-04-22)
      const ad = Date.parse(av), bd = Date.parse(bv)
      if (!isNaN(ad) && !isNaN(bd)) {
        diff = dir === 'asc' ? ad - bd : bd - ad
      } else {
        // Numeric comparison
        const an = parseFloat(av), bn = parseFloat(bv)
        if (!isNaN(an) && !isNaN(bn)) {
          diff = dir === 'asc' ? an - bn : bn - an
        } else {
          // String comparison
          const as = av.toString().toLowerCase(), bs = bv.toString().toLowerCase()
          diff = dir === 'asc' ? (as < bs ? -1 : as > bs ? 1 : 0) : (as > bs ? -1 : as < bs ? 1 : 0)
        }
      }
      // Critério secundário / Desempate: Ordenar pelo número da OS na mesma direção
      if (diff === 0) {
        const aos = a.numero_os ?? '', bos = b.numero_os ?? ''
        diff = dir === 'asc' ? (aos < bos ? -1 : aos > bos ? 1 : 0) : (aos > bos ? -1 : aos < bos ? 1 : 0)
      }
      return diff
    })"""

assert orig_sort in content, "Error: orig_sort block not found!"
content = content.replace(orig_sort, new_sort)

# 2. Apply Abertas filter
orig_abertas = """  const emAndamento = abertas.filter(o => o.status_os === 'em_andamento')
  const aguardando = abertas.filter(o => o.status_os === 'aguardando_peca')
  const agNf = abertas.filter(o => o.status_os === 'executado_aguardando_nf')
  const todasAbertas = abertas"""

new_abertas = """  const abertasDoAno = useMemo(() => {
    if (!year) return abertas
    return abertas.filter(o => {
      const dateStr = o.data_entrada || o.criado_em
      if (!dateStr) return true // Evita que suma
      return new Date(dateStr).getFullYear() === parseInt(year)
    })
  }, [abertas, year])

  const emAndamento = abertasDoAno.filter(o => o.status_os === 'em_andamento')
  const aguardando = abertasDoAno.filter(o => o.status_os === 'aguardando_peca')
  const agNf = abertasDoAno.filter(o => o.status_os === 'executado_aguardando_nf')
  const todasAbertas = abertasDoAno"""

assert orig_abertas in content, "Error: orig_abertas block not found!"
content = content.replace(orig_abertas, new_abertas)

# 3. Apply finalizadasDoAno and filteredFin
orig_fin = """  const filteredFin = useMemo(() => {
    const byYear = year
      ? finalizadas.filter(o => {
        const dateStr = o.data_execucao || o.data_entrada || o.criado_em || (o.notas_fiscais?.[0]?.data_emissao)
        if (!dateStr) return true // Para evitar que a OS suma do sistema
        return new Date(dateStr).getFullYear() === parseInt(year)
      })
      : finalizadas
    return applyTipoFilter(applyFilterSort(withDisplay(byYear), filterFin, sortFin, ['placa', 'fornecedor', 'modelo', '_sistema', '_servico', 'numero_os']))
  }, [finalizadas, filterFin, sortFin, year, filterTipo])"""

new_fin = """  const finalizadasDoAno = useMemo(() => {
    if (!year) return finalizadas
    return finalizadas.filter(o => {
      const dateStr = o.data_execucao || o.data_entrada || o.criado_em || (o.notas_fiscais?.[0]?.data_emissao)
      if (!dateStr) return true // Para evitar que a OS suma do sistema
      return new Date(dateStr).getFullYear() === parseInt(year)
    })
  }, [finalizadas, year])

  const filteredFin = useMemo(() => {
    return applyTipoFilter(applyFilterSort(withDisplay(finalizadasDoAno), filterFin, sortFin, ['placa', 'fornecedor', 'modelo', '_sistema', '_servico', 'numero_os']))
  }, [finalizadasDoAno, filterFin, sortFin, filterTipo])"""

assert orig_fin in content, "Error: orig_fin block not found!"
content = content.replace(orig_fin, new_fin)

# 4. Apply KPI card
orig_kpi = """          <div>
            <p className="text-g-600 text-xs uppercase tracking-wider">Finalizadas (total)</p>
            <p className="text-g-200 font-bold text-xl">{finalizadas.length}</p>
          </div>"""

new_kpi = """          <div>
            <p className="text-g-600 text-xs uppercase tracking-wider">Finalizadas (total)</p>
            <p className="text-g-200 font-bold text-xl">{finalizadasDoAno.length}</p>
          </div>"""

assert orig_kpi in content, "Error: orig_kpi block not found!"
content = content.replace(orig_kpi, new_kpi)

# 5. Apply Tab count
orig_tab = """          {[
            { key: 'em_andamento', label: `Em andamento (${todasAbertas.length})` },
            { key: 'finalizadas', label: `Finalizadas (${finalizadas.length})` },
          ].map(t => ("""

new_tab = """          {[
            { key: 'em_andamento', label: `Em andamento (${todasAbertas.length})` },
            { key: 'finalizadas', label: `Finalizadas (${finalizadasDoAno.length})` },
          ].map(t => ("""

assert orig_tab in content, "Error: orig_tab block not found!"
content = content.replace(orig_tab, new_tab)

# 6. Apply Pneu header with Registrar Rodizio button relocation
orig_pneu = """                    {/* Barra de ações (Pneu) */}
                    {sistema === 'Pneu' && (
                      <div className="px-5 py-2 bg-g-950/20 border-b border-g-900 flex items-center justify-end">
                        <button
                          onClick={() => setRodizioModal({ placa: veh.placa, specs, conjuntos: allConjs })}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-600/10 border border-violet-500/30 text-violet-700 rounded-lg text-[11px] font-semibold hover:bg-violet-600/20 transition-colors"
                        >
                          <RotateCcw className="w-3 h-3" />
                          Registrar Rodízio
                        </button>
                      </div>
                    )}
                    {/* KM atual info bar (Pneu) */}
                    {veh.km_atual && (
                      <div className="px-5 py-2.5 bg-sky-50/60 border-b border-sky-100 text-xs">
                        <div className="flex items-center gap-4 flex-wrap">
                          <span className="text-sky-700 font-semibold">KM atual do veículo:</span>
                          <span className="font-mono font-bold text-sky-800">{num(veh.km_atual)} km</span>
                          {veh.km_atual_data && <span className="text-sky-500">em {dateBR(veh.km_atual_data)}</span>}
                        </div>
                        {veh.km_por_posicao?.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-3">
                            {veh.km_por_posicao.map(p => {
                              const pct  = avgFleet ? Math.round(p.km_rodado / avgFleet * 100) : null
                              const pCol = avgFleet && p.km_rodado > avgFleet * 0.85 ? 'border-amber-300 bg-amber-50/80 text-amber-700'
                                         : 'border-sky-200 bg-white text-sky-700'
                              return (
                                <div key={p.posicao} className={`flex items-center gap-2 border rounded-lg px-3 py-1.5 ${pCol}`}>
                                  <span className="font-semibold text-[11px] uppercase tracking-wide opacity-70">{p.posicao}</span>
                                  <span className="font-mono font-bold">{num(p.km_rodado)} km</span>
                                  {p.dias_rodando != null && <span className="opacity-60">{p.dias_rodando}d</span>}
                                  {pct != null && <span className="opacity-60 text-[10px]">({pct}% da média)</span>}
                                  {(p.marca || p.espec) && (
                                    <span className="opacity-50 text-[10px] border-l pl-2">
                                      {p.marca}{p.marca && p.espec ? ' · ' : ''}{p.espec}
                                    </span>
                                  )}
                                  {p.numero_os && <span className="opacity-40 text-[10px] font-mono">{p.numero_os}</span>}
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </div>
                    )}"""

new_pneu = """                    {/* Cabeçalho Pneu: KM Atual e Registro de Rodízio */}
                    {sistema === 'Pneu' && (
                      <div className="px-5 py-3.5 bg-sky-50/30 border-b border-sky-100 flex flex-col gap-3">
                        <div className="flex items-center justify-between flex-wrap gap-3">
                          <div className="flex items-center gap-3 flex-wrap text-xs">
                            {veh.km_atual ? (
                              <>
                                <span className="text-sky-700 font-semibold">KM atual do veículo:</span>
                                <span className="font-mono font-extrabold text-sky-900 bg-white border border-sky-200/80 px-2.5 py-0.5 rounded-md shadow-sm text-[13px]">{num(veh.km_atual)} km</span>
                                {veh.km_atual_data && <span className="text-sky-500 font-medium text-[11px]">em {dateBR(veh.km_atual_data)}</span>}
                              </>
                            ) : (
                              <span className="text-g-600 italic font-medium">Veículo sem KM registrado</span>
                            )}
                          </div>

                          <button
                            onClick={() => setRodizioModal({ placa: veh.placa, specs, conjuntos: allConjs })}
                            className="flex items-center gap-1.5 px-3.5 py-2 bg-white hover:bg-violet-50 border border-violet-200 hover:border-violet-300 text-violet-700 hover:text-violet-800 rounded-lg text-xs font-extrabold shadow-sm hover:shadow transition-all duration-200 group cursor-pointer active:scale-95"
                          >
                            <RotateCcw className="w-3.5 h-3.5 text-violet-500 group-hover:rotate-[-45deg] transition-transform" />
                            Registrar Rodízio
                          </button>
                        </div>

                        {veh.km_por_posicao?.length > 0 && (
                          <div className="flex flex-wrap gap-2.5">
                            {veh.km_por_posicao.map(p => {
                              const pct  = avgFleet ? Math.round(p.km_rodado / avgFleet * 100) : null
                              const pCol = avgFleet && p.km_rodado > avgFleet * 0.85 ? 'border-amber-300 bg-amber-50/75 text-amber-800'
                                         : 'border-sky-200 bg-white text-sky-800'
                              return (
                                <div key={p.posicao} className={`flex items-center gap-2 border rounded-lg px-3 py-1.5 ${pCol} shadow-sm text-xs`}>
                                  <span className="font-bold text-[10px] uppercase tracking-wider opacity-70">{p.posicao}</span>
                                  <span className="font-mono font-extrabold">{num(p.km_rodado)} km</span>
                                  {p.dias_rodando != null && <span className="opacity-60 font-medium">{p.dias_rodando}d</span>}
                                  {pct != null && <span className="opacity-50 font-medium text-[10px]">({pct}% da média)</span>}
                                  {(p.marca || p.espec) && (
                                    <span className="opacity-40 text-[10px] border-l border-current/20 pl-2 font-medium">
                                      {p.marca}{p.marca && p.espec ? ' · ' : ''}{p.espec}
                                    </span>
                                  )}
                                  {p.numero_os && <span className="opacity-30 text-[10px] font-mono tracking-tighter">{p.numero_os}</span>}
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </div>
                    )}

                    {/* KM atual info bar simplificada para outros sistemas */}
                    {sistema !== 'Pneu' && veh.km_atual && (
                      <div className="px-5 py-2.5 bg-sky-50/60 border-b border-sky-100 text-xs">
                        <div className="flex items-center gap-4 flex-wrap">
                          <span className="text-sky-700 font-semibold">KM atual do veículo:</span>
                          <span className="font-mono font-bold text-sky-800">{num(veh.km_atual)} km</span>
                          {veh.km_atual_data && <span className="text-sky-500 font-medium">em {dateBR(veh.km_atual_data)}</span>}
                        </div>
                      </div>
                    )}"""

assert orig_pneu in content, "Error: orig_pneu block not found!"
content = content.replace(orig_pneu, new_pneu)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("SUCCESS: All 6 modifications successfully and cleanly applied!")
