import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

export default function KPICard({ icon: Icon, label, value, sub, trend, trendLabel, accent = false, danger = false }) {
  const trendIcon =
    trend > 0 ? <TrendingUp className="w-3 h-3 text-g-400" /> :
    trend < 0 ? <TrendingDown className="w-3 h-3 text-red-400" /> :
    <Minus className="w-3 h-3 text-g-600" />

  const trendColor = trend > 0 ? 'text-g-400' : trend < 0 ? 'text-red-400' : 'text-g-600'

  return (
    <div className={`card p-4 flex flex-col gap-3 relative overflow-hidden
      ${accent ? 'border-g-700 bg-g-800' : ''}
      ${danger ? 'border-red-900 bg-red-950/30' : ''}
    `}>
      {/* Top row */}
      <div className="flex items-center justify-between">
        <div className={`p-1.5 rounded-md ${danger ? 'bg-red-900/50' : 'bg-g-800'}`}>
          {Icon && <Icon className={`w-4 h-4 ${danger ? 'text-red-400' : 'text-g-500'}`} />}
        </div>
        {trend !== undefined && (
          <div className={`flex items-center gap-1 text-xs font-medium ${trendColor}`}>
            {trendIcon}
            {trendLabel}
          </div>
        )}
      </div>

      {/* Value */}
      <div>
        <p className="text-g-500 text-xs font-medium uppercase tracking-wider mb-1">{label}</p>
        <p className={`font-bold text-xl leading-tight ${danger ? 'text-red-300' : 'text-g-50'}`}>{value}</p>
        {sub && <p className="text-g-500 text-xs mt-1">{sub}</p>}
      </div>

      {/* Accent bar */}
      <div className={`absolute bottom-0 left-0 right-0 h-0.5 ${danger ? 'bg-red-700/60' : 'bg-g-700/60'}`} />
    </div>
  )
}
