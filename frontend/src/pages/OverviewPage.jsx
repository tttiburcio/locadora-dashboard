import { brl, pct, num, brlShort } from '../utils/format'
import { useTrackerData } from '../hooks/useTrackerData'
import TrackerKpiRow from '../components/tracker/TrackerKpiRow'
import TrackerStatusBadge from '../components/tracker/TrackerStatusBadge'
import TrackerInsightsCard from '../components/tracker/TrackerInsightsCard'
import TrackerActionCenter from '../components/tracker/TrackerActionCenter'
import KPICard from '../components/KPICard'
import { MonthlyRevenueChart, MonthlyCostChart } from '../components/charts/MonthlyChart'
import { FleetHealthPie, CostPie, TopVehiclesChart } from '../components/charts/FleetCharts'
import {
  Truck, DollarSign, TrendingUp, TrendingDown, Percent,
  Activity, Award, AlertCircle, Wrench, Shield, FileText, MapPin,
  BarChart2, Target, AlertTriangle,
} from 'lucide-react'

function Section({ title, icon: Icon, badge, children }) {
  return (
    <section>
      <div className="flex items-center gap-2.5 mb-4">
        <div className="p-1.5 bg-g-850 border border-g-800 rounded-lg">
          <Icon className="w-4 h-4 text-g-600" />
        </div>
        <h2 className="text-g-500 font-semibold text-xs uppercase tracking-widest">{title}</h2>
        {badge && <span>{badge}</span>}
        <div className="flex-1 h-px bg-g-800" />
      </div>
      {children}
    </section>
  )
}

function ChartCard({ title, children, className = '' }) {
  return (
    <div className={`card p-4 ${className}`}>
      <p className="text-g-600 text-xs font-semibold uppercase tracking-widest mb-4">{title}</p>
      {children}
    </div>
  )
}

function SummaryRow({ label, value, valueClass = 'text-g-200', pctVal }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-g-800 last:border-0">
      <span className="text-g-600 text-xs">{label}</span>
      <div className="flex items-center gap-2">
        {pctVal !== undefined && (
          <span className="text-g-700 text-xs tabular-nums">{pct(pctVal)}</span>
        )}
        <span className={`text-sm font-semibold font-mono tabular-nums ${valueClass}`}>{value}</span>
      </div>
    </div>
  )
}

function InconsistencyBanner({ items }) {
  if (!items?.length) return null
  return (
    <div className="flex flex-col gap-2 p-4 bg-amber-50 border border-amber-200 rounded-xl animate-fade-in">
      <div className="flex items-center gap-2 mb-1">
        <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
        <p className="text-amber-700 text-xs font-semibold uppercase tracking-wider">
          Inconsistências detectadas nos dados
        </p>
      </div>
      {items.map((issue, i) => (
        <p key={i} className="text-amber-600 text-xs pl-6">{issue.descricao}</p>
      ))}
    </div>
  )
}

export default function OverviewPage({ kpis: k, monthly, vehicles, year, setPage, setTrackerFilter }) {
  const {
    trackerOnline, trackerKpis, trackerUsage,
    highUsageVehicles, idleVehicles, topKmVehicles,
    fleetHealthScore, recommendedActions,
  } = useTrackerData({ year })

  function handleDrillDown(filterTarget) {
    if (!setTrackerFilter || !setPage) return
    setTrackerFilter(filterTarget)
    setPage('vehicles')
  }

  const margem_pos  = k.margem >= 0
  const pct_lucr    = k.veiculos_ativos > 0 ? k.veiculos_lucrativos / k.veiculos_ativos * 100 : 0

  return (
    <div className="flex flex-col gap-8">

      {/* Inconsistency warnings */}
      <InconsistencyBanner items={k.inconsistencias} />

      {/* ── KPIs primários ── */}
      <Section title="Indicadores Chave" icon={BarChart2}
        badge={<TrackerStatusBadge online={trackerOnline} />}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { icon: Truck,      label: 'Veículos Ativos',  rawValue: k.veiculos_ativos,
              formatter: num,   sub: `${num(k.veiculos_total)} total · ${num(k.veiculos_lucrativos)} lucrativos`,
              trend: k.veiculos_lucrativos - k.veiculos_deficitarios,
              trendLabel: `${num(k.veiculos_lucrativos)} lucrat.`, delay: 0 },
            { icon: DollarSign, label: 'Receita Total',    rawValue: k.receita_total,
              formatter: brlShort, sub: `Faturado ${brlShort(k.faturado)} · Recebido ${brlShort(k.recebido)}`,
              delay: 55 },
            { icon: margem_pos ? TrendingUp : TrendingDown, label: 'Margem Líquida',
              rawValue: k.margem, formatter: brlShort,
              sub: `${pct(k.margem_pct)} sobre receita`,
              accent: margem_pos, danger: !margem_pos,
              trend: k.margem, trendLabel: pct(k.margem_pct), delay: 110 },
            { icon: Activity,   label: 'Taxa Utilização',  rawValue: k.taxa_utilizacao,
              formatter: v => pct(v),
              sub: 'Dias trabalhados / total',
              trend: k.taxa_utilizacao - 70,
              trendLabel: k.taxa_utilizacao >= 70 ? 'Meta OK' : 'Abaixo 70%', delay: 165 },
          ].map(({ delay, ...props }) => (
            <KPICard key={props.label} {...props} delay={delay} />
          ))}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-3">
          {[
            { icon: Percent,  label: '% Lucrativos',   rawValue: pct_lucr,
              formatter: v => pct(v),
              sub: `${num(k.veiculos_lucrativos)} de ${num(k.veiculos_ativos)} veículos`,
              accent: pct_lucr >= 70, danger: pct_lucr < 50, delay: 0 },
            { icon: Target,   label: 'Receita / Veículo', rawValue: k.receita_por_veiculo,
              formatter: brlShort, sub: 'Média por veículo ativo', delay: 55 },
            { icon: Target,   label: 'Margem / Veículo',  rawValue: k.margem_por_veiculo,
              formatter: brlShort, sub: 'Média por veículo ativo',
              accent: k.margem_por_veiculo > 0, danger: k.margem_por_veiculo < 0, delay: 110 },
            { icon: Percent,  label: 'Custo / Receita',   rawValue: k.custo_sobre_receita,
              formatter: v => pct(v), sub: 'Índice de eficiência',
              danger: k.custo_sobre_receita > 80, accent: k.custo_sobre_receita < 50, delay: 165 },
          ].map(({ delay, ...props }) => (
            <KPICard key={props.label} {...props} delay={delay} />
          ))}
        </div>

        <TrackerKpiRow trackerKpis={trackerKpis} />
        <TrackerInsightsCard
          highUsageVehicles={highUsageVehicles}
          idleVehicles={idleVehicles}
          topKmVehicles={topKmVehicles}
          trackerUsage={trackerUsage}
        />
        <TrackerActionCenter
          recommendedActions={recommendedActions}
          fleetHealthScore={fleetHealthScore}
          trackerUsage={trackerUsage}
          onDrillDown={handleDrillDown}
        />
      </Section>

      {/* ── Melhor / Pior ── */}
      {(k.melhor_veiculo || k.pior_veiculo) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {k.melhor_veiculo && (
            <div className="card border-g-700/60 p-4 flex items-center gap-3 stagger-child" style={{'--i': 1}}>
              <div className="p-2.5 bg-g-800 rounded-lg shrink-0 border border-g-700">
                <Award className="w-5 h-5 text-g-300" />
              </div>
              <div>
                <p className="text-g-600 text-xs uppercase tracking-widest">Melhor Resultado</p>
                <p className="text-g-50 font-bold font-mono mt-0.5">{k.melhor_veiculo.placa}</p>
                <p className="text-g-500 text-xs">{k.melhor_veiculo.modelo}</p>
                <p className="text-g-200 text-sm font-semibold mt-1 tabular-nums">{brl(k.melhor_veiculo.margem)}</p>
              </div>
            </div>
          )}
          {k.pior_veiculo && (
            <div className={`card p-4 flex items-center gap-3 stagger-child ${k.pior_veiculo.margem < 0 ? 'border-red-900/40' : ''}`}
              style={{'--i': 2}}>
              <div className={`p-2.5 rounded-lg shrink-0 border ${k.pior_veiculo.margem < 0 ? 'bg-red-950/40 border-red-900/40' : 'bg-g-800 border-g-700'}`}>
                <AlertCircle className={`w-5 h-5 ${k.pior_veiculo.margem < 0 ? 'text-red-400' : 'text-amber-400'}`} />
              </div>
              <div>
                <p className="text-g-600 text-xs uppercase tracking-widest">Menor Resultado</p>
                <p className="text-g-50 font-bold font-mono mt-0.5">{k.pior_veiculo.placa}</p>
                <p className="text-g-500 text-xs">{k.pior_veiculo.modelo}</p>
                <p className={`text-sm font-semibold mt-1 tabular-nums ${k.pior_veiculo.margem < 0 ? 'text-red-300' : 'text-g-200'}`}>
                  {brl(k.pior_veiculo.margem)}
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Receita ── */}
      <Section title="Receita" icon={DollarSign}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
          <KPICard icon={DollarSign} label="Rec. Locação"
            rawValue={k.receita_locacao} formatter={brlShort}
            sub={pct(k.receita_total > 0 ? k.receita_locacao / k.receita_total * 100 : 0) + ' do total'} />
          <KPICard icon={FileText}   label="Rec. Reembolso"
            rawValue={k.receita_reembolso} formatter={brlShort}
            sub={pct(k.receita_total > 0 ? k.receita_reembolso / k.receita_total * 100 : 0) + ' do total'} />
          <div className="card p-4">
            <p className="text-g-600 text-xs uppercase tracking-widest mb-3">Faturamento</p>
            <SummaryRow label="Faturado"      value={brl(k.faturado)} />
            <SummaryRow label="Recebido"      value={brl(k.recebido)}           valueClass="text-g-200"
              pctVal={k.faturado > 0 ? k.recebido / k.faturado * 100 : 0} />
            <SummaryRow
              label="Inadimplência"
              value={brl(k.faturado - k.recebido)}
              valueClass={k.faturado - k.recebido > 0 ? 'text-red-300' : 'text-g-500'}
            />
          </div>
        </div>
        <ChartCard title="Evolução Mensal de Receita">
          <MonthlyRevenueChart data={monthly} />
        </ChartCard>
      </Section>

      {/* ── Custos ── */}
      <Section title="Estrutura de Custos" icon={Wrench}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          <KPICard icon={Wrench}   label="Manutenção"   rawValue={k.custo_manutencao}   formatter={brlShort}
            sub={pct(k.custo_total > 0 ? k.custo_manutencao   / k.custo_total * 100 : 0) + ' dos custos'} />
          <KPICard icon={Shield}   label="Seguro"        rawValue={k.custo_seguro}        formatter={brlShort}
            sub={pct(k.custo_total > 0 ? k.custo_seguro        / k.custo_total * 100 : 0) + ' dos custos'} />
          <KPICard icon={FileText} label="Impostos"      rawValue={k.custo_impostos}      formatter={brlShort}
            sub={pct(k.custo_total > 0 ? k.custo_impostos      / k.custo_total * 100 : 0) + ' dos custos'} />
          <KPICard icon={MapPin}   label="Rastreamento"  rawValue={k.custo_rastreamento}  formatter={brlShort}
            sub={pct(k.custo_total > 0 ? k.custo_rastreamento  / k.custo_total * 100 : 0) + ' dos custos'} />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <ChartCard title="Receita vs Custos por Mês">
              <MonthlyCostChart data={monthly} />
            </ChartCard>
          </div>
          <ChartCard title="Composição de Custos">
            <CostPie
              manutencao={k.custo_manutencao}
              seguro={k.custo_seguro}
              impostos={k.custo_impostos}
              rastreamento={k.custo_rastreamento}
            />
          </ChartCard>
        </div>
      </Section>

      {/* ── Saúde da frota ── */}
      {vehicles.length > 0 && (
        <Section title="Saúde da Frota" icon={Activity}>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <ChartCard title="Lucrativos vs Deficitários">
              <FleetHealthPie
                lucrativos={k.veiculos_lucrativos}
                deficitarios={k.veiculos_deficitarios}
              />
            </ChartCard>
            <div className="lg:col-span-2">
              <ChartCard title={`Top ${Math.min(10, vehicles.length)} Veículos por Margem`}>
                <TopVehiclesChart vehicles={vehicles} n={10} />
              </ChartCard>
            </div>
          </div>
        </Section>
      )}
    </div>
  )
}
