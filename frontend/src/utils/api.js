import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const getYears              = ()                    => api.get('/years').then(r => r.data)
export const getKpis               = (year)                => api.get('/kpis',     { params: { year } }).then(r => r.data)
export const getMonthly            = (year)                => api.get('/monthly',  { params: { year } }).then(r => r.data)
export const getVehicles           = (year, region)        => api.get('/vehicles', { params: { year, ...(region ? { region } : {}) } }).then(r => r.data)
export const getVehicle            = (placa, year)         => api.get(`/vehicle/${encodeURIComponent(placa)}`, { params: { year } }).then(r => r.data)
export const getRegions            = (year)                => api.get('/regions',  { params: { year } }).then(r => r.data)
export const getMaintenanceAnalysis = (year, placa)        => api.get('/maintenance_analysis', { params: { year, ...(placa ? { placa } : {}) } }).then(r => r.data)
