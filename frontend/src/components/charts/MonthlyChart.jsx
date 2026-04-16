import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Area,
} from 'recharts'
import { brlShort, brl } from '../../utils/format'

const COLORS = {
  locacao:      '#22c55e',
  reembolso:    '#34d399',
  manutencao:   '#f97316',
  seguro:       '#ef4444',
  rastreamento: '#f59e0b',
  total:        '#86efac',
}

const TooltipContent = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-g-900 border border-g-700 rounded-lg p-3 shadow-xl text-xs min-w-[180px]">
      <p className="text-g-200 font-semibold mb-2">{label}</p>
      {payload.map(p => (
        <div key={p.dataKey} className="flex justify-between gap-4 mt-1">
          <span style={{ color: p.color }}>{p.name}</span>
          <span className="text-g-100 font-mono">{brl(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

export function MonthlyRevenueChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(22,101,52,0.3)" />
        <XAxis dataKey="MesLabel" tick={{ fill: '#4ade80', fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={brlShort} tick={{ fill: '#4ade80', fontSize: 10 }} axisLine={false} tickLine={false} width={64} />
        <Tooltip content={<TooltipContent />} />
        <Legend wrapperStyle={{ fontSize: 11, color: '#86efac', paddingTop: 8 }} />
        <Bar dataKey="Locacao"   name="Locação"    stackId="r" fill={COLORS.locacao}   radius={[0,0,0,0]} />
        <Bar dataKey="Reembolso" name="Reembolso"  stackId="r" fill={COLORS.reembolso} radius={[3,3,0,0]} />
        <Line dataKey="ReceitaTotal" name="Receita Total" type="monotone"
          stroke={COLORS.total} strokeWidth={2} dot={{ r: 3, fill: COLORS.total }} strokeDasharray="4 2" />
      </ComposedChart>
    </ResponsiveContainer>
  )
}

export function MonthlyCostChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(22,101,52,0.3)" />
        <XAxis dataKey="MesLabel" tick={{ fill: '#4ade80', fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={brlShort} tick={{ fill: '#4ade80', fontSize: 10 }} axisLine={false} tickLine={false} width={64} />
        <Tooltip content={<TooltipContent />} />
        <Legend wrapperStyle={{ fontSize: 11, color: '#86efac', paddingTop: 8 }} />
        <Bar dataKey="CustoManutencao"   name="Manutenção"    stackId="c" fill={COLORS.manutencao}   radius={[0,0,0,0]} />
        <Bar dataKey="CustoSeguro"       name="Seguro"         stackId="c" fill={COLORS.seguro}       radius={[0,0,0,0]} />
        <Bar dataKey="CustoRastreamento" name="Rastreamento"   stackId="c" fill={COLORS.rastreamento} radius={[3,3,0,0]} />
        <Line dataKey="ReceitaTotal" name="Receita Total" type="monotone"
          stroke={COLORS.locacao} strokeWidth={2.5} dot={{ r: 3, fill: COLORS.locacao }} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
