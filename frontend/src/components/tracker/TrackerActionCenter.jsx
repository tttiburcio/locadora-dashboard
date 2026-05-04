import { AlertTriangle, RefreshCw, Wrench, ZapOff, CheckCircle, Activity, ArrowRight, Play } from 'lucide-react'
import { useTrackerActions } from '../../hooks/useTrackerActions'

const SEVERITY = {
  high:   { bg: 'bg-red-500/10',   border: 'border-red-500/20',   text: 'text-red-400'   },
  medium: { bg: 'bg-amber-500/10', border: 'border-amber-500/20', text: 'text-amber-400' },
  low:    { bg: 'bg-blue-500/10',  border: 'border-blue-500/20',  text: 'text-blue-400'  },
}

const TYPE_ICON = {
  redistribution: RefreshCw,
  maintenance:    Wrench,
  reallocation:   ZapOff,
}

function HealthBar({ score }) {
  const color  = score >= 80 ? 'bg-emerald-500' : score >= 50 ? 'bg-amber-500' : 'bg-red-500'
  const label  = score >= 80 ? 'Saudável' : score >= 50 ? 'Atenção' : 'Crítico'
  const tColor = score >= 80 ? 'text-emerald-400' : score >= 50 ? 'text-amber-400' : 'text-red-400'
  const badge  = score >= 80
    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
    : score >= 50
    ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
    : 'bg-red-500/10 text-red-400 border-red-500/20'

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1.5 bg-g-800 rounded-full overflow-hidden max-w-[120px]">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${score}%` }} />
      </div>
      <span className={`text-sm font-bold font-mono tabular-nums ${tColor}`}>{score}</span>
      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide border ${badge}`}>
        {label}
      </span>
    </div>
  )
}

export default function TrackerActionCenter({
  recommendedActions,
  fleetHealthScore,
  trackerUsage,
  onDrillDown,
}) {
  const { executeAction } = useTrackerActions()

  if (!trackerUsage || !trackerUsage.length) return null

  const allGood = fleetHealthScore >= 80 && recommendedActions.length === 0

  function handleApply(action, e) {
    e.stopPropagation()
    const confirmed = window.confirm(`Confirmar ação?\n\n${action.message}`)
    if (!confirmed) return
    executeAction(action)
    alert('Ação aplicada (simulação)')
  }

  return (
    <div className="card p-4 mt-3">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-g-600" />
          <p className="text-g-600 text-xs font-semibold uppercase tracking-widest">Centro de Ação</p>
        </div>
        {fleetHealthScore !== null && <HealthBar score={fleetHealthScore} />}
      </div>

      {allGood ? (
        <div className="flex items-center gap-2 text-g-600 text-sm">
          <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
          Frota equilibrada — nenhuma ação necessária.
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {recommendedActions.map((action, i) => {
            const sev  = SEVERITY[action.severity] || SEVERITY.medium
            const Icon = TYPE_ICON[action.type] || AlertTriangle
            return (
              <div
                key={i}
                className={`flex items-center gap-3 p-3 rounded-lg border ${sev.bg} ${sev.border} ${onDrillDown ? 'cursor-pointer hover:opacity-80 transition-opacity' : ''}`}
                onClick={() => onDrillDown && onDrillDown(action.filterTarget)}
              >
                <Icon className={`w-4 h-4 ${sev.text} shrink-0`} />
                <p className={`text-sm flex-1 ${sev.text}`}>{action.message}</p>
                <button
                  onClick={e => handleApply(action, e)}
                  className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wide border transition-colors shrink-0 ${sev.border} ${sev.text} hover:bg-white/10`}
                >
                  <Play className="w-2.5 h-2.5" />
                  Aplicar
                </button>
                {onDrillDown && (
                  <span className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide ${sev.text} opacity-60 whitespace-nowrap`}>
                    Ver frota <ArrowRight className="w-3 h-3" />
                  </span>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
