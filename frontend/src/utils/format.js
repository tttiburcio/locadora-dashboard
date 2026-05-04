export function brl(v) {
  if (v == null || isNaN(v)) return 'R$ 0,00'
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    minimumFractionDigits: 2,
  }).format(v)
}

export function brlShort(v) {
  if (v == null || isNaN(v)) return 'R$ 0'
  const abs = Math.abs(v)
  const sign = v < 0 ? '-' : ''
  if (abs >= 1_000_000) return `${sign}R$ ${(abs / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000)     return `${sign}R$ ${(abs / 1_000).toFixed(1)}k`
  return `${sign}R$ ${abs.toFixed(0)}`
}

export function pct(v, decimals = 1) {
  if (v == null || isNaN(v)) return '0%'
  return `${Number(v).toFixed(decimals)}%`
}

export function num(v) {
  if (v == null || isNaN(v)) return '0'
  return new Intl.NumberFormat('pt-BR').format(Math.round(v))
}

export function dias(v) {
  if (v == null || isNaN(v)) return '0 dias'
  return `${Math.round(v)} dias`
}

export function isNeg(v) {
  return typeof v === 'number' && v < 0
}

export function km(v) {
  if (v == null || isNaN(v)) return '—'
  return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 }).format(v) + ' km'
}

export function dateBR(v) {
  if (!v) return '—'
  const [y, m, d] = String(v).split('-')
  if (!y || !m || !d) return v
  return `${d}/${m}/${y}`
}
