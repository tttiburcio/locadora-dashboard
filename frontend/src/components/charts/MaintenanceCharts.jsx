import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Cell, PieChart, Pie, Legend,
  ComposedChart, Area, Line, ReferenceLine,
  RadialBarChart, RadialBar,
  Treemap,
} from 'recharts'
import { brl, brlShort } from '../../utils/format'

// ─── shared style ────────────────────────────────────────
const TOOLTIP_STYLE = {
  background: '#18181b',
  border: '1px solid #3f3f46',
  borderRadius: 8,
  fontSize: 12,
  boxShadow: '0 4px 24px rgba(0,0,0,0.5)',
}
const TICK = { fill: '#52525b', fontSize: 11 }

const PALETTE = [
  '#6366f1','#8b5cf6','#a78bfa',
  '#f97316','#fb923c','#fdba74',
  '#ef4444','#f87171',
  '#f59e0b','#fbbf24',
  '#22d3ee','#38bdf8',
]

function TipContent({ active, payload, label, fmt = brl }) {
  if (!active || !payload?.length) return null
  return (
    <div style={TOOLTIP_STYLE} className="p-3 min-w-[190px]">
      <p className="text-g-200 font-semibold text-xs mb-2">{label}</p>
      {payload.map((p, i) => (
        <div key={i} className="flex justify-between gap-4 mt-1">
          <span className="text-xs" style={{ color: p.color || p.fill }}>{p.name}</span>
          <span className="text-g-100 font-mono text-xs font-semibold">{fmt(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

// ── 1. Top fornecedores (horizontal bar) ─────────────────
export function FornecedorChart({ data = [] }) {
  const d = data.slice(0, 10).reverse()
  return (
    <ResponsiveContainer width="100%" height={Math.max(220, d.length * 36 + 40)}>
      <BarChart data={d} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 110 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
        <XAxis type="number" tickFormatter={brlShort} tick={TICK} axisLine={false} tickLine={false} />
        <YAxis
          type="category" dataKey="name" width={108}
          tick={{ fill: '#a1a1aa', fontSize: 10.5 }}
          axisLine={false} tickLine={false}
          tickFormatter={v => v.length > 18 ? v.slice(0, 17) + '…' : v}
        />
        <Tooltip content={<TipContent />} />
        <Bar dataKey="total" name="Custo" radius={[0, 4, 4, 0]} maxBarSize={20}>
          {d.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── 2. Sistema — Treemap ──────────────────────────────────
const TreemapContent = ({ x, y, width, height, name, total, depth }) => {
  if (width < 30 || height < 20) return null
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill="#27272a" stroke="#09090b" strokeWidth={2} rx={4} />
      {width > 60 && height > 30 && (
        <>
          <text x={x + 8} y={y + 18} fill="#e4e4e7" fontSize={11} fontWeight={600}
            style={{ pointerEvents: 'none' }}>
            {name?.length > 14 ? name.slice(0, 13) + '…' : name}
          </text>
          {height > 44 && (
            <text x={x + 8} y={y + 34} fill="#71717a" fontSize={10}
              style={{ pointerEvents: 'none' }}>
              {brlShort(total)}
            </text>
          )}
        </>
      )}
    </g>
  )
}

export function SistemaTreemap({ data = [] }) {
  const colored = data.map((d, i) => ({ ...d, fill: PALETTE[i % PALETTE.length] }))
  if (!colored.length) return <div className="flex items-center justify-center h-48 text-g-700 text-sm">Sem dados de sistema</div>
  return (
    <ResponsiveContainer width="100%" height={260}>
      <Treemap
        data={colored}
        dataKey="total"
        nameKey="name"
        content={<TreemapContent />}
        animationDuration={600}
      />
    </ResponsiveContainer>
  )
}

// ── 3. Tipo (Preventiva/Corretiva) — Donut ───────────────
export function TipoPie({ data = [] }) {
  const colors = { 'Corretiva': '#ef4444', 'Preventiva': '#6366f1', 'Preditiva': '#f59e0b' }
  const d = data.map(x => ({ ...x, color: colors[x.name] || '#71717a' }))
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={d} cx="50%" cy="50%" innerRadius={55} outerRadius={82}
          paddingAngle={3} dataKey="total">
          {d.map((x, i) => <Cell key={i} fill={x.color} stroke="transparent" />)}
        </Pie>
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={v => [brl(v)]} />
        <Legend wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
          formatter={(v, e) => <span style={{ color: e.color, fontSize: 11 }}>{v}</span>} />
      </PieChart>
    </ResponsiveContainer>
  )
}

// ── 4. Implemento — RadialBarChart ────────────────────────
export function ImplementoRadial({ data = [] }) {
  const max = Math.max(...data.map(d => d.total), 1)
  const d = data.slice(0, 8).map((x, i) => ({
    ...x,
    fill: PALETTE[i % PALETTE.length],
    pct: Math.round((x.total / max) * 100),
  }))
  return (
    <ResponsiveContainer width="100%" height={240}>
      <RadialBarChart cx="50%" cy="50%" innerRadius="20%" outerRadius="90%"
        data={d} startAngle={180} endAngle={-180}>
        <RadialBar dataKey="total" nameKey="name" background={{ fill: '#27272a' }}
          label={{ position: 'insideStart', fill: '#a1a1aa', fontSize: 10 }} />
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={v => [brl(v)]} />
        <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }}
          formatter={(v, e) => <span style={{ color: e.color, fontSize: 10 }}>{v?.length > 14 ? v.slice(0, 13) + '…' : v}</span>} />
      </RadialBarChart>
    </ResponsiveContainer>
  )
}

// ── 5. Tendência mensal + projeção (ComposedChart + Area) ─
export function TrendProjectionChart({ monthly = [], projection = [] }) {
  // Merge actuals + projected into one timeline
  const actuals  = monthly.map(m => ({ ...m, type: 'actual' }))
  const projOffset = actuals.filter(m => m.total > 0).length

  // Build combined dataset: actual months + projected months
  const projected = projection.map((p, i) => ({
    month: projOffset + i + 1,
    name: `Proj ${i + 1}`,
    total: null,
    projected: p.projected,
    low: p.low,
    high: p.high,
    type: 'projected',
  }))

  // last actual entry gets projected values for continuity
  const last = actuals.filter(m => m.total > 0).slice(-1)[0]
  const bridge = last
    ? [{ ...last, projected: last.total, low: last.total, high: last.total, type: 'bridge' }]
    : []

  const combined = [...actuals, ...bridge, ...projected]

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={combined} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="projGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#6366f1" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey="name" tick={TICK} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={brlShort} tick={TICK} axisLine={false} tickLine={false} width={64} />
        <Tooltip content={<TipContent />} />
        <Area dataKey="high"      name="Limite sup."  fill="url(#projGrad)" stroke="transparent" />
        <Area dataKey="low"       name="Limite inf."  fill="#09090b"        stroke="transparent" />
        <Bar  dataKey="total"     name="Realizado"    fill="#3f3f46"        radius={[3,3,0,0]} maxBarSize={28} />
        <Line dataKey="projected" name="Projeção"     stroke="#6366f1"      strokeWidth={2.5}
          strokeDasharray="6 3" dot={false} connectNulls />
        <ReferenceLine
          x={last?.name}
          stroke="rgba(255,255,255,0.2)"
          strokeDasharray="4 4"
          label={{ value: 'Hoje', fill: '#71717a', fontSize: 10 }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}

// ── 6. Custo por veículo — Scatter ────────────────────────
export function VehicleScatter({ vehicles = [] }) {
  // Simple scatter: X=receita, Y=custo_manutencao, colored by margin
  const d = vehicles.filter(v => v.receita_total > 0)
  return (
    <ResponsiveContainer width="100%" height={260}>
      <ComposedChart margin={{ top: 8, right: 8, bottom: 24, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis
          dataKey="receita_total" type="number"
          tickFormatter={brlShort} tick={TICK} axisLine={false} tickLine={false}
          label={{ value: 'Receita', position: 'insideBottom', offset: -16, fill: '#52525b', fontSize: 11 }}
        />
        <YAxis
          dataKey="custo_manutencao" type="number"
          tickFormatter={brlShort} tick={TICK} axisLine={false} tickLine={false} width={60}
          label={{ value: 'Manutenção', angle: -90, position: 'insideLeft', fill: '#52525b', fontSize: 11 }}
        />
        <Tooltip
          cursor={{ strokeDasharray: '3 3', stroke: '#3f3f46' }}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const v = payload[0]?.payload
            if (!v) return null
            return (
              <div style={TOOLTIP_STYLE} className="p-3">
                <p className="text-white font-bold font-mono text-sm mb-1">{v.placa}</p>
                <p className="text-g-500 text-xs mb-2">{v.modelo}</p>
                <div className="space-y-0.5 text-xs">
                  <div className="flex justify-between gap-4"><span className="text-g-500">Receita</span><span className="text-g-100 font-mono">{brl(v.receita_total)}</span></div>
                  <div className="flex justify-between gap-4"><span className="text-g-500">Manutenção</span><span className="text-orange-300 font-mono">{brl(v.custo_manutencao)}</span></div>
                  <div className="flex justify-between gap-4"><span className="text-g-500">Margem</span><span className={`font-mono font-bold ${v.margem >= 0 ? 'text-white' : 'text-red-300'}`}>{brl(v.margem)}</span></div>
                </div>
              </div>
            )
          }}
        />
        {d.map((v, i) => (
          <Bar
            key={v.placa}
            data={[v]}
            dataKey="custo_manutencao"
            name={v.placa}
            fill={v.margem >= 0 ? '#6366f1' : '#ef4444'}
            maxBarSize={12}
          />
        ))}
      </ComposedChart>
    </ResponsiveContainer>
  )
}

// ── 7. Serviços mais frequentes (bar) ─────────────────────
export function ServicosChart({ data = [] }) {
  const d = data.slice(0, 8)
  return (
    <ResponsiveContainer width="100%" height={Math.max(180, d.length * 34 + 40)}>
      <BarChart data={d} layout="vertical" margin={{ top: 4, right: 16, bottom: 4, left: 160 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
        <XAxis type="number" tickFormatter={brlShort} tick={TICK} axisLine={false} tickLine={false} />
        <YAxis
          type="category" dataKey="name" width={158}
          tick={{ fill: '#a1a1aa', fontSize: 10 }}
          axisLine={false} tickLine={false}
          tickFormatter={v => v?.length > 24 ? v.slice(0, 23) + '…' : v}
        />
        <Tooltip content={<TipContent />} />
        <Bar dataKey="total" name="Custo" radius={[0, 4, 4, 0]} maxBarSize={18}>
          {d.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── 8. Custo mensal (bar simples) ─────────────────────────
export function MonthlyBarChart({ data = [] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
        <XAxis dataKey="name" tick={TICK} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={brlShort} tick={TICK} axisLine={false} tickLine={false} width={64} />
        <Tooltip content={<TipContent />} />
        <Bar dataKey="total" name="Custo" radius={[3, 3, 0, 0]} maxBarSize={32}>
          {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
