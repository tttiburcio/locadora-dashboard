import { useState, useEffect, useRef, useMemo } from 'react'
import { trackerGetKpis, trackerGetUsage, normalizePlaca } from '../utils/trackerApi'
import {
  HIGH_USAGE_THRESHOLD, IDLE_KM_MONTH, HIGH_KM_MONTH, TOP_KM_COUNT,
} from '../constants/trackerThresholds'

// Months to aggregate for a given year (all 12 for past years, 1..current for current year)
function monthsForYear(year) {
  const now = new Date()
  const currentYear  = now.getFullYear()
  const currentMonth = now.getMonth() + 1
  const total = year < currentYear ? 12 : currentMonth
  return Array.from({ length: total }, (_, i) => i + 1)
}

export function useTrackerData({ year, enabled = true }) {
  const [trackerOnline, setTrackerOnline] = useState(null)
  const [trackerKpis,   setTrackerKpis]   = useState(null)
  const [trackerUsage,  setTrackerUsage]  = useState(null)
  const [monthsCount,   setMonthsCount]   = useState(1)
  const [loading,       setLoading]       = useState(false)
  const [_tick,         setTick]          = useState(0)

  const loadedForYear = useRef(null)

  useEffect(() => {
    if (!enabled) return
    if (loadedForYear.current === year) return

    let cancelled = false
    setLoading(true)
    setTrackerOnline(null)

    const months = monthsForYear(year)
    const daysInPeriod = months.length * 30  // approximation for daily avg
    const nMonths = months.length

    Promise.all([
      trackerGetKpis(),
      // Fetch all months in parallel, then aggregate
      Promise.all(months.map(m => trackerGetUsage(m, year))),
    ]).then(([kpis, usageByMonth]) => {
      if (cancelled) return

      const online = kpis !== null || usageByMonth.some(u => u !== null)
      setTrackerOnline(online)
      setTrackerKpis(kpis)

      // Aggregate KM per vehicle across all months
      const kmByPlaca = {}
      usageByMonth.forEach(monthData => {
        const arr = Array.isArray(monthData) ? monthData
          : Array.isArray(monthData?.value) ? monthData.value
          : null
        if (!arr) return
        arr.forEach(v => {
          const p  = normalizePlaca(v.Placa || v.placa || '')
          const km = v.KM ?? v.km ?? v.total_km ?? 0
          kmByPlaca[p] = (kmByPlaca[p] || 0) + km
        })
      })

      const usageArr = Object.entries(kmByPlaca).map(([Placa, KM]) => ({
        Placa,
        KM,
        km_dia: KM / daysInPeriod,  // pre-computed daily average for the period
      }))

      setTrackerUsage(usageArr.length > 0 ? usageArr : null)
      setMonthsCount(nMonths)
      loadedForYear.current = year
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })

    return () => { cancelled = true }
  }, [year, enabled, _tick])

  function reloadTracker() {
    loadedForYear.current = null
    setTrackerOnline(null)
    setTrackerKpis(null)
    setTrackerUsage(null)
    setTick(n => n + 1)
  }

  function getVehicleKm(placa) {
    if (!trackerUsage || !placa) return null
    const norm  = normalizePlaca(placa)
    const found = trackerUsage.find(v =>
      normalizePlaca(v.Placa || v.placa || '') === norm
    )
    if (!found) return null
    const totalKm = found.KM ?? found.km ?? 0
    const kmDia   = found.km_dia ?? (totalKm / 365)
    return { ...found, km: totalKm, kmDia }
  }

  const analytics = useMemo(() => {
    if (!trackerUsage || !trackerUsage.length) return null

    const vehicles = trackerUsage.map(v => {
      const totalKm = v.KM ?? v.km ?? 0
      const kmDia   = v.km_dia ?? (totalKm / 365)
      return { placa: normalizePlaca(v.Placa || v.placa || ''), km: totalKm, kmDia }
    })

    const total              = vehicles.length
    const highUsageVehicles  = vehicles.filter(v => v.kmDia > HIGH_USAGE_THRESHOLD)
    // Ocioso: média km/mês < IDLE_KM_MONTH (100 km/mês)
    const idleVehicles       = vehicles.filter(v => {
      const avgPerMonth = monthsCount > 0 ? v.km / monthsCount : v.km
      return v.km > 0 && avgPerMonth < IDLE_KM_MONTH
    })
    const topKmVehicles      = [...vehicles].sort((a, b) => b.km - a.km).slice(0, TOP_KM_COUNT)
    const maintenanceCandidates = vehicles.filter(v => v.km > HIGH_KM_MONTH)

    const normalCount      = total - highUsageVehicles.length - idleVehicles.length
    const fleetHealthScore = Math.round(Math.max(0, (normalCount / total) * 100))

    const recommendedActions = []
    if (highUsageVehicles.length > 0 && idleVehicles.length > 0) {
      const n = highUsageVehicles.length
      recommendedActions.push({
        type: 'redistribution', severity: 'high', filterTarget: 'high_usage',
        message: `Redistribuir ${n} veículo${n > 1 ? 's' : ''} com uso excessivo para equilibrar a frota`,
      })
    }
    if (maintenanceCandidates.length > 0) {
      const n = maintenanceCandidates.length
      recommendedActions.push({
        type: 'maintenance', severity: 'medium', filterTarget: 'high_usage',
        message: `${n} veículo${n > 1 ? 's' : ''} com KM acumulado elevado — verificar manutenção preventiva`,
      })
    }
    const idlePct = (idleVehicles.length / total) * 100
    if (idlePct > 30) {
      recommendedActions.push({
        type: 'reallocation', severity: 'medium', filterTarget: 'idle',
        message: `${Math.round(idlePct)}% da frota com baixo uso — reavaliar alocação ou demanda`,
      })
    }

    return { highUsageVehicles, idleVehicles, topKmVehicles, fleetHealthScore, recommendedActions }
  }, [trackerUsage, monthsCount])

  return {
    trackerOnline, trackerKpis, trackerUsage, loading,
    getVehicleKm, reloadTracker,
    highUsageVehicles:  analytics?.highUsageVehicles  ?? [],
    idleVehicles:       analytics?.idleVehicles       ?? [],
    topKmVehicles:      analytics?.topKmVehicles      ?? [],
    fleetHealthScore:   analytics?.fleetHealthScore   ?? null,
    recommendedActions: analytics?.recommendedActions ?? [],
  }
}
