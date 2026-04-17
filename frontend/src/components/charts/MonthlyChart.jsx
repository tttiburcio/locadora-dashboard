import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { brlShort, brl } from '../../utils/format'

// B&W-friendly palette — indigo/violet for revenue, warm for costs
const COLORS = {
  locacao:      '#6366f1',   // indigo-500
  reembolso:    '#8b5cf6',   // violet-500
  manutencao:   '#f97316',   // orange-500
  seguro:       '#ef4444',   // red-500
  rastreamento: '#f59e0b',   // amber-500
  total:        '#e4e4e7',   // zinc-200 (white-ish line)
}

const TOOLTIP_STYLE = {
  background: '#18181b',
  border: '1px solid #3f3f46',
  borderRadius: 8,
  fontSize: 12,
  boxShadow: '0 4px 24px rgba(0,0,0,0.5)',
}

const TooltipContent = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={TOOLTIP_STYLE} className="p-3 min-w-[190px]">
      <p className="text-g-200 font-semibold mb-2 text-xs uppercase tracking-wide">{label}</p>
      {payload.map(p => (
        <div key={p.dataKey} className="flex justify-between gap-4 mt-1">
          <span className="text-xs" style={{ color: p.color }}>{p.name}</span>
          <span className="text-g-100 font-mono text-xs font-semibold">{brl(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

const AXIS_TICK = { fill: '#52525b', fontSize: 11 }

export function MonthlyRevenueChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey="MesLabel" tick={AXIS_TICK} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={brlShort} tick={AXIS_TICK} axisLine={false} tickLine={false} width={64} />
        <Tooltip content={<TooltipContent />} />
        <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
          formatter={(v, e) => <span style={{ color: e.color, fontSize: 11 }}>{v}</span>} />
        <Bar dataKey="Locacao"      name="Locação"    stackId="r" fill={COLORS.locacao}   radius={[0,0,0,0]} />
        <Bar dataKey="Reembolso"    name="Reembolso"  stackId="r" fill={COLORS.reembolso} radius={[3,3,0,0]} />
        <Line dataKey="ReceitaTotal" name="Total"     type="monotone"
          stroke={COLORS.total} strokeWidth={2} dot={{ r: 3, fill: COLORS.total }} strokeDasharray="4 2" />
      </ComposedChart>
    </ResponsiveContainer>
  )
}

export function MonthlyCostChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey="MesLabel" tick={AXIS_TICK} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={brlShort} tick={AXIS_TICK} axisLine={false} tickLine={false} width={64} />
        <Tooltip content={<TooltipContent />} />
        <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
          formatter={(v, e) => <span style={{ color: e.color, fontSize: 11 }}>{v}</span>} />
        <Bar dataKey="CustoManutencao"   name="Manutenção"  stackId="c" fill={COLORS.manutencao}   radius={[0,0,0,0]} />
        <Bar dataKey="CustoSeguro"       name="Seguro"       stackId="c" fill={COLORS.seguro}       radius={[0,0,0,0]} />
        <Bar dataKey="CustoRastreamento" name="Rastreamento" stackId="c" fill={COLORS.rastreamento} radius={[3,3,0,0]} />
        <Line dataKey="ReceitaTotal" name="Receita" type="monotone"
          stroke={COLORS.total} strokeWidth={2.5} dot={{ r: 3, fill: COLORS.total }} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
