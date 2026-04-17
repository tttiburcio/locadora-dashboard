import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { useCountUp } from '../hooks/useCountUp'

/**
 * Props:
 *   icon, label, value (string fallback), sub, trend, trendLabel, accent, danger
 *   rawValue  — raw number to animate (optional)
 *   formatter — fn(number) → string, used with rawValue
 *   delay     — CSS animation-delay in ms for stagger entrance (default 0)
 */
export default function KPICard({
  icon: Icon, label, value, sub, trend, trendLabel,
  accent = false, danger = false,
  rawValue, formatter, delay = 0,
}) {
  const animated  = useCountUp(typeof rawValue === 'number' ? rawValue : 0)
  const displayed = typeof rawValue === 'number' && formatter
    ? formatter(animated)
    : value

  const trendIcon =
    trend > 0  ? <TrendingUp  className="w-3 h-3 text-emerald-600" /> :
    trend < 0  ? <TrendingDown className="w-3 h-3 text-red-500" /> :
                 <Minus        className="w-3 h-3 text-g-600" />

  const trendColor = trend > 0 ? 'text-emerald-600' : trend < 0 ? 'text-red-500' : 'text-g-600'

  return (
    <div
      className={`card p-4 flex flex-col gap-3 relative overflow-hidden stagger-child
        ${accent ? 'border-g-100/20' : ''}
        ${danger ? 'border-red-200 bg-red-50/50' : ''}
      `}
      style={{ '--i': 0, animationDelay: `${delay}ms` }}
    >
      {/* Top row */}
      <div className="flex items-center justify-between">
        <div className={`p-1.5 rounded-md
          ${danger  ? 'bg-red-100'              : ''}
          ${accent  ? 'bg-g-100/10'             : ''}
          ${!danger && !accent ? 'bg-g-850' : ''}
        `}>
          {Icon && (
            <Icon className={`w-4 h-4
              ${danger ? 'text-red-600' : accent ? 'text-g-100' : 'text-g-500'}
            `} />
          )}
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
        <p className="text-g-600 text-xs font-semibold uppercase tracking-wider mb-1">{label}</p>
        <p className={`font-bold text-xl leading-tight tabular-nums
          ${danger ? 'text-red-700' : 'text-g-200'}
        `}>
          {displayed}
        </p>
        {sub && <p className="text-g-600 text-xs mt-1">{sub}</p>}
      </div>

      {/* Bottom accent line */}
      <div className={`absolute bottom-0 left-0 right-0 h-px
        ${danger ? 'bg-red-200' : accent ? 'bg-g-100/30' : 'bg-g-800'}
      `} />
    </div>
  )
}
