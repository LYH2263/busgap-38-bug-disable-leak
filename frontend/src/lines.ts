import { reactive } from 'vue'
import { api } from './api'

// The app currently tracks a single line (seed B12, id = 1).
// Centralize its active state so every view reacts to deactivate/activate.
export const CURRENT_LINE_ID = 1

interface LineState {
  loaded: boolean
  isActive: boolean
  name: string
  code: string
}

const state = reactive<LineState>({ loaded: false, isActive: true, name: '', code: '' })

async function refresh() {
  try {
    const lines = await api<any[]>('/lines')
    const line = lines.find((l) => l.id === CURRENT_LINE_ID) ?? lines[0]
    if (line) {
      state.isActive = !!line.is_active
      state.name = line.name
      state.code = line.code
    }
  } finally {
    state.loaded = true
  }
}

export function useLineStatus() {
  if (!state.loaded) void refresh()
  return { state, refresh }
}
