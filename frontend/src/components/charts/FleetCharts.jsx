import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, LabelList,
} from 'recharts'
import { brlShort, brl } from '../../utils/format'

const GREEN = '#22c55e'
const RED   = '#ef4444'

// Fleet health pie (profitable vs deficit)
export function FleetHealthPie({ lucrativos, deficitarios }) {
  const data = [
    { name: 'Lucrativos', value: lucrativos, color: GREEN },
    { name: 'Deficitários', value: deficitarios, color: RED },
  ]
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={55}
          outerRadius={80}
          paddingAngle={3}
          dataKey="value"
        >
          {data.map((d, i) => <Cell key={i} fill={d.color} stroke="transparent" />)}
        </Pie>
        <Tooltip
          contentStyle={{ background: '#083a1e', border: '1px solid #166534', borderRadius: 8, fontSize: 12 }}
          itemStyle={{ color: '#86efac' }}
          formatter={(v, n) => [`${v} veículos`, n]}
        />
        <Legend
          wrapperStyle={{ fontSize: 12, color: '#86efac', paddingTop: 8 }}
          formatter={(v, e) => <span style={{ color: e.color }}>{v}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}

// Cost composition pie
export function CostPie({ manutencao, seguro, impostos, rastreamento }) {
  const data = [
    { name: 'Manutenção',    value: manutencao,   color: '#f97316' },
    { name: 'Seguro',        value: seguro,        color: '#ef4444' },
    { name: 'Impostos',      value: impostos,      color: '#a855f7' },
    { name: 'Rastreamento',  value: rastreamento,  color: '#f59e0b' },
  ].filter(d => d.value > 0)

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={80}
          paddingAngle={2}
          dataKey="value"
        >
          {data.map((d, i) => <Cell key={i} fill={d.color} stroke="transparent" />)}
        </Pie>
        <Tooltip
          contentStyle={{ background: '#083a1e', border: '1px solid #166534', borderRadius: 8, fontSize: 12 }}
          itemStyle={{ color: '#86efac' }}
          formatter={(v) => [brl(v)]}
        />
        <Legend
          wrapperStyle={{ fontSize: 11, color: '#86efac', paddingTop: 8 }}
          formatter={(v, e) => <span style={{ color: e.color }}>{v}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}

// Top N vehicles by margin (horizontal bar)
export function TopVehiclesChart({ vehicles, n = 10 }) {
  const sorted = [...vehicles]
    .sort((a, b) => b.margem - a.margem)
    .slice(0, n)
    .reverse()

  const data = sorted.map(v => ({
    name:   `${v.placa}`,
    modelo: v.modelo,
    margem: v.margem,
    color:  v.margem >= 0 ? GREEN : RED,
  }))

  return (
    <ResponsiveContainer width="100%" height={Math.max(200, data.length * 30 + 40)}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 12, bottom: 4, left: 60 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(22,101,52,0.25)" horizontal={false} />
        <XAxis type="number" tickFormatter={brlShort} tick={{ fill: '#4ade80', fontSize: 10 }} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="name" tick={{ fill: '#86efac', fontSize: 11 }} axisLine={false} tickLine={false} width={58} />
        <Tooltip
          contentStyle={{ background: '#083a1e', border: '1px solid #166534', borderRadius: 8, fontSize: 12 }}
          formatter={(v, n, p) => [brl(v), `Margem · ${p.payload.modelo}`]}
          labelStyle={{ color: '#86efac' }}
        />
        <Bar dataKey="margem" radius={[0, 4, 4, 0]} maxBarSize={18}>
          {data.map((d, i) => <Cell key={i} fill={d.color} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
