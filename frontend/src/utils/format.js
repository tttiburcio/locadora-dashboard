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

export function titleCase(str) {
  if (!str) return str
  const connectors = ['de', 'da', 'do', 'das', 'dos', 'e', 'para', 'com', 'em', 'um', 'uma']
  return str
    .toLowerCase()
    .split(' ')
    .map((word, index) => {
      if (index > 0 && connectors.includes(word)) return word
      return word.charAt(0).toUpperCase() + word.slice(1)
    })
    .join(' ')
}

export function shortenProviderName(name, maxLen = 20) {
  if (!name || name.length <= maxLen) return name
  const parts = name.split(' ').filter(p => p.length > 0)
  if (parts.length <= 1) return name
  const first = parts[0]
  const rest = parts.slice(1).map(p => {
    if (['de', 'da', 'do', 'das', 'dos', 'e'].includes(p.toLowerCase())) return ''
    return p.charAt(0).toUpperCase() + '.'
  }).filter(p => p !== '').join(' ')
  return `${first} ${rest}`
}
