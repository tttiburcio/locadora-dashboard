import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const getYears    = ()            => api.get('/years').then(r => r.data)
export const getKpis     = (year)        => api.get('/kpis',     { params: { year } }).then(r => r.data)
export const getMonthly  = (year)        => api.get('/monthly',  { params: { year } }).then(r => r.data)
export const getVehicles = (year)        => api.get('/vehicles', { params: { year } }).then(r => r.data)
export const getVehicle  = (placa, year) => api.get(`/vehicle/${encodeURIComponent(placa)}`, { params: { year } }).then(r => r.data)
