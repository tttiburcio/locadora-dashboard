import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.response.use(
  res => res,
  err => {
    const status = err.response?.status
    const url    = err.config?.url ?? ''
    if (status >= 500) {
      console.error(`[API] Erro ${status} em ${url}:`, err.response?.data)
    } else if (status >= 400) {
      console.warn(`[API] ${status} em ${url}:`, err.response?.data)
    }
    return Promise.reject(err)
  }
)

export const getYears              = ()                    => api.get('/years').then(r => r.data)
export const getKpis               = (year)                => api.get('/kpis',     { params: { year } }).then(r => r.data)
export const getMonthly            = (year)                => api.get('/monthly',  { params: { year } }).then(r => r.data)
export const getVehicles           = (year, region)        => api.get('/vehicles', { params: { year, ...(region ? { region } : {}) } }).then(r => r.data)
export const getVehicle            = (placa, year)         => api.get(`/vehicle/${encodeURIComponent(placa)}`, { params: { year } }).then(r => r.data)
export const getRegions            = (year)                => api.get('/regions',  { params: { year } }).then(r => r.data)
export const getMaintenanceAnalysis = (year, placa)        => api.get('/maintenance_analysis', { params: { year, ...(placa ? { placa } : {}) } }).then(r => r.data)
export const getImplementoAnalysis  = (year)               => api.get('/maintenance_analysis/implemento', { params: { year } }).then(r => r.data)
export const getIntervalosAnalysis  = (sistema)            => api.get('/maintenance_analysis/intervalos', { params: { sistema } }).then(r => r.data)

// ── Banco SQLite — CRUD legado (manutenções) ─────────────────────────
export const dbListFrota           = ()                    => api.get('/db/frota').then(r => r.data)
export const dbListManutencoes     = (status, placa)       => api.get('/db/manutencoes', { params: { ...(status ? { status } : {}), ...(placa ? { placa } : {}) } }).then(r => r.data)
export const dbGetManutencao       = (id)                  => api.get(`/db/manutencoes/${id}`).then(r => r.data)
export const dbAbrirManutencao     = (payload)             => api.post('/db/manutencoes', payload).then(r => r.data)
export const dbAtualizarManutencao = (id, payload)         => api.patch(`/db/manutencoes/${id}`, payload).then(r => r.data)
export const dbFinalizarManutencao = (id, payload)         => api.post(`/db/manutencoes/${id}/finalizar`, payload).then(r => r.data)
export const dbDeletarManutencao   = (id)                  => api.delete(`/db/manutencoes/${id}`)
export const dbAtualizarParcela    = (id, payload)         => api.patch(`/db/parcelas/${id}`, payload).then(r => r.data)
export const dbListParcelas        = (year)                => api.get('/db/parcelas', { params: { ...(year ? { year } : {}) } }).then(r => r.data)

// ── Ordens de Serviço (novo modelo) ─────────────────────────────────
export const dbListOs              = (status, placa)       => api.get('/db/os', { params: { ...(status ? { status } : {}), ...(placa ? { placa } : {}) } }).then(r => r.data)
export const dbGetOs               = (id)                  => api.get(`/db/os/${id}`).then(r => r.data)
export const dbAbrirOs             = (payload)             => api.post('/db/os', payload).then(r => r.data)
export const dbAtualizarOs         = (id, payload)         => api.patch(`/db/os/${id}`, payload).then(r => r.data)
export const dbEditarOsFinalizada  = (id, payload)         => api.patch(`/db/os/${id}/editar`, payload).then(r => r.data)
export const dbDeletarOs           = (id)                  => api.delete(`/db/os/${id}`)
export const dbExecutarOs          = (id, payload)         => api.post(`/db/os/${id}/executar`, payload).then(r => r.data)
export const dbFinalizarOs         = (id)                  => api.post(`/db/os/${id}/finalizar`).then(r => r.data)
export const dbValidarOs           = (id)                  => api.get(`/db/os/${id}/validacao`).then(r => r.data)

// ── Itens da OS ──────────────────────────────────────────────────────
export const dbCriarOsItem         = (os_id, payload)      => api.post(`/db/os/${os_id}/itens`, payload).then(r => r.data)
export const dbAtualizarOsItem     = (os_id, item_id, p)   => api.patch(`/db/os/${os_id}/itens/${item_id}`, p).then(r => r.data)
export const dbDeletarOsItem       = (os_id, item_id)      => api.delete(`/db/os/${os_id}/itens/${item_id}`)

// ── Notas Fiscais ────────────────────────────────────────────────────
export const dbListNfs             = (os_id)               => api.get(`/db/os/${os_id}/nfs`).then(r => r.data)
export const dbCriarNf             = (os_id, payload)      => api.post(`/db/os/${os_id}/nfs`, payload).then(r => r.data)
export const dbSyncNfs             = (os_id, payload)      => api.put(`/db/os/${os_id}/nfs-sync`, payload).then(r => r.data)
export const dbAtualizarNf         = (nf_id, payload)      => api.patch(`/db/nfs/${nf_id}`, payload).then(r => r.data)
export const dbDeletarNf           = (nf_id)               => api.delete(`/db/nfs/${nf_id}`)
export const dbCriarParcelaNf      = (nf_id, payload)      => api.post(`/db/nfs/${nf_id}/parcelas`, payload).then(r => r.data)

// ── Merge assistido ──────────────────────────────────────────────────
export const dbMergeSugestoes      = ()                    => api.get('/db/os/merge-sugestoes').then(r => r.data)
export const dbConfirmarMerge      = (payload)             => api.post('/db/os/merge', payload).then(r => r.data)

// ── Sincronização Excel ↔ SQLite ─────────────────────────────────────
export const runSync               = ()                    => api.post('/sync').then(r => r.data)

// ── Pneu rodízio ─────────────────────────────────────────────────────
export const listPneuRodizios      = (placa)               => api.get(`/manut/pneu-rodizios/${encodeURIComponent(placa)}`).then(r => r.data)
export const createPneuRodizio     = (payload)             => api.post('/manut/pneu-rodizios', payload).then(r => r.data)
export const deletePneuRodizio     = (id)                  => api.delete(`/manut/pneu-rodizios/${id}`)
