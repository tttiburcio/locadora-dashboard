import { Flame, Trophy, ZapOff } from 'lucide-react'
import { km, num, pct } from '../../utils/format'
import { HIGH_USAGE_THRESHOLD, IDLE_KM_MONTH } from '../../constants/trackerThresholds'

export default function TrackerInsightsCard({ highUsageVehicles, idleVehicles, topKmVehicles, trackerUsage }) {
  if (!trackerUsage || !trackerUsage.length) return null

  const total    = trackerUsage.length
  const highPct  = total > 0 ? highUsageVehicles.length / total * 100 : 0
  const idlePct  = total > 0 ? idleVehicles.length      / total * 100 : 0

  return (
    <div className="grid grid-cols-3 gap-3 mt-3">
      {/* Uso excessivo */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Flame className="w-3.5 h-3.5 text-red-400 shrink-0" />
          <p className="text-g-600 text-xs font-semibold uppercase tracking-widest">Uso Excessivo</p>
          <span className="text-g-800 text-[10px] whitespace-nowrap">&gt;{HIGH_USAGE_THRESHOLD} km/dia</span>
        </div>
        <p className="text-2xl font-bold font-mono text-red-400 tabular-nums">{num(highUsageVehicles.length)}</p>
        <p className="text-g-700 text-xs mt-1 tabular-nums">{pct(highPct)} da frota</p>
        {highUsageVehicles.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {highUsageVehicles.slice(0, 4).map(v => (
              <span key={v.placa} className="text-[10px] font-mono text-red-400/70 bg-red-500/10 px-1.5 py-0.5 rounded border border-red-500/20">
                {v.placa}
              </span>
            ))}
            {highUsageVehicles.length > 4 && (
              <span className="text-[10px] text-g-700">+{highUsageVehicles.length - 4}</span>
            )}
          </div>
        )}
      </div>

      {/* Top KM */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Trophy className="w-3.5 h-3.5 text-amber-400 shrink-0" />
          <p className="text-g-600 text-xs font-semibold uppercase tracking-widest">Top KM</p>
        </div>
        <div className="flex flex-col gap-1.5">
          {topKmVehicles.map((v, i) => (
            <div key={v.placa} className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="text-g-800 text-[10px] w-3 shrink-0">{i + 1}</span>
                <span className="text-g-300 text-xs font-mono truncate">{v.placa}</span>
              </div>
              <span className="text-cyan-400 text-xs font-mono tabular-nums shrink-0">{km(v.km)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Ociosos */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-3">
          <ZapOff className="w-3.5 h-3.5 text-amber-500 shrink-0" />
          <p className="text-g-600 text-xs font-semibold uppercase tracking-widest">Ociosos</p>
          <span className="text-g-800 text-[10px] whitespace-nowrap">&lt;{IDLE_KM_MONTH} km/mês</span>
        </div>
        <p className="text-2xl font-bold font-mono text-amber-400 tabular-nums">{num(idleVehicles.length)}</p>
        <p className="text-g-700 text-xs mt-1 tabular-nums">{pct(idlePct)} da frota</p>
        {idleVehicles.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {idleVehicles.slice(0, 4).map(v => (
              <span key={v.placa} className="text-[10px] font-mono text-amber-400/70 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                {v.placa}
              </span>
            ))}
            {idleVehicles.length > 4 && (
              <span className="text-[10px] text-g-700">+{idleVehicles.length - 4}</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
