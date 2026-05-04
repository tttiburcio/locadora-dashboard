import { Wifi, WifiOff, Loader } from 'lucide-react'

/**
 * Badge de status da conexão com o map-trackerAPI.
 * - null  → carregando (spinner)
 * - true  → online
 * - false → offline
 * Nunca bloqueia renderização; é puramente informativo.
 */
export default function TrackerStatusBadge({ online }) {
  if (online === null) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide bg-g-850 text-g-600 border border-g-800">
        <Loader className="w-3 h-3 animate-spin" />
        Rastreador
      </span>
    )
  }

  if (online) {
    return (
      <span className="badge-green inline-flex items-center gap-1">
        <Wifi className="w-3 h-3" />
        Tracker Online
      </span>
    )
  }

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide bg-g-850 text-g-500 border border-g-800">
      <WifiOff className="w-3 h-3" />
      Tracker Offline
    </span>
  )
}
