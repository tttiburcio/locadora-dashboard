import { Route } from 'lucide-react'
import { km } from '../../utils/format'
import { HIGH_USAGE_THRESHOLD, IDLE_KM_MONTH } from '../../constants/trackerThresholds'

/**
 * Cores escuras e contrastantes para leitura fácil em tabela dark-mode:
 * - Excessivo  (kmDia > 150)       → vermelho sólido
 * - Ocioso     (kmTotal < 100/mês) → âmbar sólido
 * - Normal                         → branco suave
 * - Sem dados                      → cinza apagado
 */
function kmColor(kmValue, dailyKm, isIdle) {
  if (kmValue === null || kmValue === undefined) return 'text-zinc-400'
  if (dailyKm !== null && dailyKm !== undefined && dailyKm > HIGH_USAGE_THRESHOLD)
    return 'text-red-600'
  if (isIdle)
    return 'text-amber-600'
  return 'text-zinc-800'
}

export default function VehicleKmBadge({ kmValue, dailyKm, isIdle }) {
  if (kmValue === null || kmValue === undefined) {
    return <span className="text-zinc-400 text-sm font-mono">—</span>
  }
  const color = kmColor(kmValue, dailyKm, isIdle)
  return (
    <span className={`inline-flex items-center gap-1 font-mono text-xs tabular-nums font-semibold whitespace-nowrap ${color}`}>
      <Route className="w-3 h-3 shrink-0 opacity-60" />
      {km(kmValue)}
    </span>
  )
}
