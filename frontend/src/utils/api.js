import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const getYears              = ()                    => api.get('/years').then(r => r.data)
export const getKpis               = (year)                => api.get('/kpis',     { params: { year } }).then(r => r.data)
export const getMonthly            = (year)                => api.get('/monthly',  { params: { year } }).then(r => r.data)
export const getVehicles           = (year, region)        => api.get('/vehicles', { params: { year, ...(region ? { region } : {}) } }).then(r => r.data)
export const getVehicle            = (placa, year)         => api.get(`/vehicle/${encodeURIComponent(placa)}`, { params: { year } }).then(r => r.data)
export const getRegions            = (year)                => api.get('/regions',  { params: { year } }).then(r => r.data)
export const getMaintenanceAnalysis = (year, placa)        => api.get('/maintenance_analysis', { params: { year, ...(placa ? { placa } : {}) } }).then(r => r.data)

// ── Banco SQLite — CRUD de manutenções ──────────────────────────────
export const dbListFrota           = ()                    => api.get('/db/frota').then(r => r.data)
export const dbListManutencoes     = (status, placa)       => api.get('/db/manutencoes', { params: { ...(status ? { status } : {}), ...(placa ? { placa } : {}) } }).then(r => r.data)
export const dbGetManutencao       = (id)                  => api.get(`/db/manutencoes/${id}`).then(r => r.data)
export const dbAbrirManutencao     = (payload)             => api.post('/db/manutencoes', payload).then(r => r.data)
export const dbAtualizarManutencao = (id, payload)         => api.patch(`/db/manutencoes/${id}`, payload).then(r => r.data)
export const dbFinalizarManutencao = (id, payload)         => api.post(`/db/manutencoes/${id}/finalizar`, payload).then(r => r.data)
export const dbDeletarManutencao   = (id)                  => api.delete(`/db/manutencoes/${id}`)
export const dbAtualizarParcela    = (id, payload)         => api.patch(`/db/parcelas/${id}`, payload).then(r => r.data)
export const dbListParcelas        = ()                    => api.get('/db/parcelas').then(r => r.data)
