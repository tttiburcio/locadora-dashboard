import { useState } from 'react'
import { trackerActions } from '../utils/trackerActions'

const STORAGE_KEY = 'tracker_action_logs'

function loadLogs() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') } catch { return [] }
}

function saveLogs(logs) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(logs)) } catch {}
}

export function useTrackerActions() {
  const [actionLogs, setActionLogs] = useState(loadLogs)

  function executeAction(action) {
    const entry = trackerActions.execute(action)
    const updated = [entry, ...actionLogs].slice(0, 100)
    setActionLogs(updated)
    saveLogs(updated)
    return entry
  }

  return { actionLogs, executeAction }
}
