import { brl, pct, num, brlShort } from '../utils/format'
import KPICard from '../components/KPICard'
import { MonthlyRevenueChart, MonthlyCostChart } from '../components/charts/MonthlyChart'
import { FleetHealthPie, CostPie, TopVehiclesChart } from '../components/charts/FleetCharts'
import {
  Truck, DollarSign, TrendingUp, TrendingDown, Percent,
  Activity, Award, AlertCircle, Wrench, Shield, FileText, MapPin,
  BarChart2, Target,
} from 'lucide-react'

function Section({ title, icon: Icon, children }) {
  return (
    <section>
      <div className="flex items-center gap-2 mb-4">
        <div className="p-1.5 bg-g-800 rounded-lg">
          <Icon className="w-4 h-4 text-g-500" />
        </div>
        <h2 className="text-g-200 font-semibold text-sm uppercase tracking-wider">{title}</h2>
        <div className="flex-1 h-px bg-g-800" />
      </div>
      {children}
    </section>
  )
}

function ChartCard({ title, children, className = '' }) {
  return (
    <div className={`card p-4 ${className}`}>
      <p className="text-g-400 text-xs font-semibold uppercase tracking-wider mb-4">{title}</p>
      {children}
    </div>
  )
}

function SummaryRow({ label, value, valueClass = 'text-g-200', pctVal }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-g-900 last:border-0">
      <span className="text-g-500 text-xs">{label}</span>
      <div className="flex items-center gap-2">
        {pctVal !== undefined && (
          <span className="text-g-600 text-xs">{pct(pctVal)}</span>
        )}
        <span className={`text-sm font-semibold font-mono ${valueClass}`}>{value}</span>
      </div>
    </div>
  )
}

export default function OverviewPage({ kpis: k, monthly, vehicles }) {
  const margem_pos = k.margem >= 0
  const margem_receita = k.receita_total > 0 ? k.margem / k.receita_total * 100 : 0
  const pct_lucr = k.veiculos_ativos > 0 ? k.veiculos_lucrativos / k.veiculos_ativos * 100 : 0

  return (
    <div className="flex flex-col gap-8">

      {/* ── KPIs primários ── */}
      <Section title="Indicadores Chave" icon={BarChart2}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <KPICard
            icon={Truck}
            label="Veículos Ativos"
            value={num(k.veiculos_ativos)}
            sub={`${num(k.veiculos_total)} no total · ${num(k.veiculos_lucrativos)} lucrativos`}
            trend={k.veiculos_lucrativos - k.veiculos_deficitarios}
            trendLabel={`${num(k.veiculos_lucrativos)} lucrat.`}
          />
          <KPICard
            icon={DollarSign}
            label="Receita Total"
            value={brlShort(k.receita_total)}
            sub={`Faturado: ${brlShort(k.faturado)} · Recebido: ${brlShort(k.recebido)}`}
          />
          <KPICard
            icon={margem_pos ? TrendingUp : TrendingDown}
            label="Margem Líquida"
            value={brlShort(k.margem)}
            sub={`${pct(k.margem_pct)} sobre receita`}
            accent={margem_pos}
            danger={!margem_pos}
            trend={k.margem}
            trendLabel={pct(k.margem_pct)}
          />
          <KPICard
            icon={Activity}
            label="Taxa de Utilização"
            value={pct(k.taxa_utilizacao)}
            sub="Dias trabalhados / total"
            trend={k.taxa_utilizacao - 70}
            trendLabel={k.taxa_utilizacao >= 70 ? 'Meta OK' : 'Abaixo 70%'}
          />
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3">
          <KPICard
            icon={Percent}
            label="% Lucrativos"
            value={pct(pct_lucr)}
            sub={`${num(k.veiculos_lucrativos)} de ${num(k.veiculos_ativos)} veículos`}
            accent={pct_lucr >= 70}
            danger={pct_lucr < 50}
          />
          <KPICard
            icon={Target}
            label="Receita / Veículo"
            value={brlShort(k.receita_por_veiculo)}
            sub="Média por veículo ativo"
          />
          <KPICard
            icon={Target}
            label="Margem / Veículo"
            value={brlShort(k.margem_por_veiculo)}
            sub="Média por veículo ativo"
            accent={k.margem_por_veiculo > 0}
            danger={k.margem_por_veiculo < 0}
          />
          <KPICard
            icon={Percent}
            label="Custo / Receita"
            value={pct(k.custo_sobre_receita)}
            sub="Índice de eficiência"
            danger={k.custo_sobre_receita > 80}
            accent={k.custo_sobre_receita < 50}
          />
        </div>
      </Section>

      {/* ── Melhor / Pior veículo ── */}
      {(k.melhor_veiculo || k.pior_veiculo) && (
        <div className="grid grid-cols-2 gap-3">
          {k.melhor_veiculo && (
            <div className="card border-g-700 p-4 flex items-center gap-3">
              <div className="p-2.5 bg-g-800 rounded-lg shrink-0">
                <Award className="w-5 h-5 text-g-400" />
              </div>
              <div>
                <p className="text-g-500 text-xs uppercase tracking-wider">Melhor Resultado</p>
                <p className="text-g-100 font-bold font-mono">{k.melhor_veiculo.placa}</p>
                <p className="text-g-400 text-xs">{k.melhor_veiculo.modelo}</p>
                <p className="text-g-300 text-sm font-semibold mt-1">{brl(k.melhor_veiculo.margem)}</p>
              </div>
            </div>
          )}
          {k.pior_veiculo && (
            <div className={`card p-4 flex items-center gap-3 ${k.pior_veiculo.margem < 0 ? 'border-red-900' : ''}`}>
              <div className={`p-2.5 rounded-lg shrink-0 ${k.pior_veiculo.margem < 0 ? 'bg-red-950' : 'bg-g-800'}`}>
                <AlertCircle className={`w-5 h-5 ${k.pior_veiculo.margem < 0 ? 'text-red-400' : 'text-amber-400'}`} />
              </div>
              <div>
                <p className="text-g-500 text-xs uppercase tracking-wider">Menor Resultado</p>
                <p className="text-g-100 font-bold font-mono">{k.pior_veiculo.placa}</p>
                <p className="text-g-400 text-xs">{k.pior_veiculo.modelo}</p>
                <p className={`text-sm font-semibold mt-1 ${k.pior_veiculo.margem < 0 ? 'text-red-300' : 'text-g-300'}`}>{brl(k.pior_veiculo.margem)}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Receita e Custos ── */}
      <Section title="Receita" icon={DollarSign}>
        <div className="grid grid-cols-3 gap-3 mb-4">
          <KPICard icon={DollarSign} label="Rec. Locação"   value={brlShort(k.receita_locacao)}
            sub={pct(k.receita_total > 0 ? k.receita_locacao / k.receita_total * 100 : 0) + ' do total'} />
          <KPICard icon={FileText}   label="Rec. Reembolso" value={brlShort(k.receita_reembolso)}
            sub={pct(k.receita_total > 0 ? k.receita_reembolso / k.receita_total * 100 : 0) + ' do total'} />
          <div className="card p-4">
            <p className="text-g-500 text-xs uppercase tracking-wider mb-3">Faturamento</p>
            <SummaryRow label="Faturado"  value={brl(k.faturado)}  />
            <SummaryRow label="Recebido"  value={brl(k.recebido)} valueClass="text-g-300"
              pctVal={k.faturado > 0 ? k.recebido / k.faturado * 100 : 0} />
            <SummaryRow
              label="Inadimplência"
              value={brl(k.faturado - k.recebido)}
              valueClass={k.faturado - k.recebido > 0 ? 'text-red-300' : 'text-g-400'}
            />
          </div>
        </div>
        <ChartCard title="Evolução Mensal de Receita">
          <MonthlyRevenueChart data={monthly} />
        </ChartCard>
      </Section>

      {/* ── Custos ── */}
      <Section title="Estrutura de Custos" icon={Wrench}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <KPICard icon={Wrench}   label="Manutenção"    value={brlShort(k.custo_manutencao)}
            sub={pct(k.custo_total > 0 ? k.custo_manutencao / k.custo_total * 100 : 0) + ' dos custos'} />
          <KPICard icon={Shield}   label="Seguro"        value={brlShort(k.custo_seguro)}
            sub={pct(k.custo_total > 0 ? k.custo_seguro / k.custo_total * 100 : 0) + ' dos custos'} />
          <KPICard icon={FileText} label="Impostos"      value={brlShort(k.custo_impostos)}
            sub={pct(k.custo_total > 0 ? k.custo_impostos / k.custo_total * 100 : 0) + ' dos custos'} />
          <KPICard icon={MapPin}   label="Rastreamento"  value={brlShort(k.custo_rastreamento)}
            sub={pct(k.custo_total > 0 ? k.custo_rastreamento / k.custo_total * 100 : 0) + ' dos custos'} />
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2">
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
          <div className="grid grid-cols-3 gap-4">
            <ChartCard title="Veículos Lucrativos vs Deficitários">
              <FleetHealthPie
                lucrativos={k.veiculos_lucrativos}
                deficitarios={k.veiculos_deficitarios}
              />
            </ChartCard>
            <div className="col-span-2">
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
