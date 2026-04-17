import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Cell, PieChart, Pie,
} from 'recharts'
import { brl, brlShort } from '../../utils/format'

const TOOLTIP_STYLE = {
  background: '#18181b',
  border: '1px solid #3f3f46',
  borderRadius: 8,
  fontSize: 12,
  boxShadow: '0 4px 24px rgba(0,0,0,0.5)',
}

const AXIS_TICK = { fill: '#52525b', fontSize: 10 }

const TooltipContent = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={TOOLTIP_STYLE} className="p-3 min-w-[180px]">
      <p className="text-g-300 font-semibold mb-2 text-xs uppercase tracking-wide">{label}</p>
      {payload.map(p => (
        <div key={p.dataKey} className="flex justify-between gap-4 mt-1">
          <span className="text-xs" style={{ color: p.color }}>{p.name}</span>
          <span className="text-g-100 font-mono text-xs font-semibold">{brl(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

export function VehicleMonthlyChart({ monthly }) {
  const data = monthly.filter(m => m.receita_total > 0 || m.custo_total > 0)

  return (
    <ResponsiveContainer width="100%" height={240}>
      <ComposedChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey="monthName" tick={AXIS_TICK} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={brlShort} tick={AXIS_TICK} axisLine={false} tickLine={false} width={56} />
        <Tooltip content={<TooltipContent />} />
        <Legend wrapperStyle={{ fontSize: 11, paddingTop: 6 }}
          formatter={(v, e) => <span style={{ color: e.color, fontSize: 11 }}>{v}</span>} />
        <Bar dataKey="receita_locacao"    name="Locação"      stackId="r" fill="#6366f1" />
        <Bar dataKey="receita_reembolso"  name="Reembolso"    stackId="r" fill="#8b5cf6" radius={[3,3,0,0]} />
        <Bar dataKey="custo_manutencao"   name="Manutenção"   stackId="c" fill="#f97316" />
        <Bar dataKey="custo_seguro"       name="Seguro"       stackId="c" fill="#ef4444" />
        <Bar dataKey="custo_rastreamento" name="Rastreamento" stackId="c" fill="#f59e0b" radius={[3,3,0,0]} />
        <Line dataKey="margem" name="Margem" type="monotone"
          stroke="#e4e4e7" strokeWidth={2} dot={{ r: 3, fill: '#e4e4e7' }} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}

export function VehicleCostPie({ kpis }) {
  const data = [
    { name: 'Manutenção',   value: kpis.custo_manutencao,   color: '#f97316' },
    { name: 'Seguro',       value: kpis.custo_seguro,       color: '#ef4444' },
    { name: 'Impostos',     value: kpis.custo_impostos,     color: '#a855f7' },
    { name: 'Rastreamento', value: kpis.custo_rastreamento, color: '#f59e0b' },
  ].filter(d => d.value > 0)

  if (data.length === 0) return (
    <div className="flex items-center justify-center h-32 text-g-700 text-sm">
      Sem custos registrados
    </div>
  )

  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie data={data} cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={2} dataKey="value">
          {data.map((d, i) => <Cell key={i} fill={d.color} stroke="transparent" />)}
        </Pie>
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          itemStyle={{ color: '#d4d4d8' }}
          formatter={(v) => [brl(v)]}
        />
        <Legend
          wrapperStyle={{ fontSize: 10, paddingTop: 4 }}
          formatter={(v, e) => <span style={{ color: e.color }}>{v}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
