import { useState, useEffect, useRef } from 'react'
import { trackerGetDetailsYear, trackerGetAlerts, normalizePlaca } from '../utils/trackerApi'

function monthsForYear(year) {
  const now = new Date()
  const total = year < now.getFullYear() ? 12 : now.getMonth() + 1
  return Array.from({ length: total }, (_, i) => i + 1)
}

export function useVehicleTrackerData({ placa, year, activeTab }) {
  const [loading, setLoading] = useState(false)
  const [kmData, setKmData]   = useState(null)
  const [alerts, setAlerts]   = useState(null)
  const cache = useRef({})

  useEffect(() => {
    if (activeTab !== 'tracker' || !placa) return

    const key = `${normalizePlaca(placa)}_${year}`
    if (cache.current[key]) {
      const c = cache.current[key]
      setKmData(c.kmData)
      setAlerts(c.alerts)
      return
    }

    const months = monthsForYear(year)

    setLoading(true)
    Promise.all([
      // Full-year details via start_date/end_date
      trackerGetDetailsYear(placa, year),
      // Alerts for every month of the year in parallel
      Promise.all(months.map(m => trackerGetAlerts(m, year))),
    ]).then(([details, alertsByMonth]) => {
      // Details: handle plain array or { value: [...] } wrapper
      const rawArr = Array.isArray(details) ? details
        : Array.isArray(details?.value) ? details.value
        : []

      // Merge and normalize alert dicts from all months
      const mergedAlerts = {}
      alertsByMonth.forEach(dict => {
        if (!dict || typeof dict !== 'object') return
        Object.entries(dict).forEach(([k, v]) => {
          const key = normalizePlaca(k)
          if (!mergedAlerts[key]) mergedAlerts[key] = []
          mergedAlerts[key].push(...(Array.isArray(v) ? v : []))
        })
      })
      const al = mergedAlerts[normalizePlaca(placa)] ?? []

      cache.current[key] = { kmData: rawArr, alerts: al }
      setKmData(rawArr)
      setAlerts(al)
    }).finally(() => setLoading(false))
  }, [placa, year, activeTab])

  const hasData = (kmData !== null && kmData.length > 0) || (alerts !== null && alerts.length > 0)

  return { loading, kmData, alerts, hasData }
}
