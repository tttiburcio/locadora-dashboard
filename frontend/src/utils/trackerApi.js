import axios from 'axios'

// Remove hífens, espaços e caracteres especiais; uppercase
// Garante consistência entre os dois sistemas (locadora usa "ABC1234", tracker pode ter "ABC-1234")
export function normalizePlaca(placa) {
  return String(placa ?? '').replace(/[-\s]/g, '').toUpperCase().trim()
}

const _tracker = axios.create({
  baseURL: '/tracker/api',
  timeout: 5000,
})

_tracker.interceptors.response.use(
  res => res,
  err => {
    const url    = err.config?.url ?? '(desconhecido)'
    const status = err.response?.status ?? (err.code === 'ECONNABORTED' ? 'timeout' : 'offline')
    console.warn(`[trackerApi] ${status} em ${url}`)
    // Retorna null — NUNCA rejeita a Promise, garante fail-safe total
    return Promise.resolve(null)
  }
)

async function _get(path, params) {
  const res = await _tracker.get(path, params ? { params } : undefined)
  return res?.data ?? null
}

export const trackerGetKpis    = ()                   => _get('/kpis')
export const trackerGetUsage   = (month, year)        => _get('/usage',  { month, year })
export const trackerGetAlerts  = (month, year)        => _get('/alerts', { month, year })
export const trackerGetDetails = (placa, month, year) => _get(`/details/${normalizePlaca(placa)}`, { month, year })

// Retorna todos os registros do ano via start_date/end_date (sem filtro de mês)
export const trackerGetDetailsYear = (placa, year) =>
  _get(`/details/${normalizePlaca(placa)}`, {
    start_date: `${year}-01-01`,
    end_date:   `${year}-12-31`,
  })
