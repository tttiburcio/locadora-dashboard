import { Route, Gauge, Trophy } from 'lucide-react'
import KPICard from '../KPICard'
import { km } from '../../utils/format'

/**
 * Linha de KPIs do map-trackerAPI na OverviewPage.
 * Só renderiza quando trackerKpis !== null (tracker online com dados).
 * Nunca bloqueia ou quebra a renderização da página.
 *
 * Shape esperado de trackerKpis:
 *   { total_veiculos, total_km_frota, media_diaria, veiculo_destaque }
 */
export default function TrackerKpiRow({ trackerKpis }) {
  if (!trackerKpis) return null

  const totalKm   = trackerKpis.total_km_frota ?? 0
  const mediaDia  = trackerKpis.media_diaria   ?? 0
  const destaque  = trackerKpis.veiculo_destaque ?? '—'

  return (
    <div className="grid grid-cols-3 gap-3 mt-3">
      <KPICard
        icon={Route}
        label="KM Total da Frota"
        rawValue={totalKm}
        formatter={km}
        sub="Acumulado no ano"
        delay={0}
      />
      <KPICard
        icon={Gauge}
        label="Média KM / Dia"
        rawValue={mediaDia}
        formatter={v => km(Math.round(v))}
        sub="Média diária da frota"
        delay={55}
      />
      <KPICard
        icon={Trophy}
        label="Destaque da Frota"
        value={destaque}
        sub="Maior KM acumulado"
        delay={110}
      />
    </div>
  )
}
