import { reactive } from 'vue'
import { api } from './api'

// The app currently tracks a single line (seed B12, id = 1).
// Centralize its active state so every view reacts to deactivate/activate
// together: 检测、试算、轴三处必须同一时刻关闭、同一时刻恢复。
export const CURRENT_LINE_ID = 1

interface LineState {
  loaded: boolean
  isActive: boolean
  name: string
  code: string
}

const state = reactive<LineState>({ loaded: false, isActive: true, name: '', code: '' })

let pending: Promise<void> | null = null

async function refresh() {
  const lines = await api<any[]>('/lines')
  const line = lines.find((l) => l.id === CURRENT_LINE_ID) ?? lines[0]
  if (line) {
    state.isActive = !!line.is_active
    state.name = line.name
    state.code = line.code
  }
  state.loaded = true
}

// 闸门未落下前不得先装成停用：状态未加载完时各入口等待首次拉取结果。
function ensureReady(): Promise<void> {
  if (state.loaded) return Promise.resolve()
  if (!pending) pending = refresh().finally(() => { pending = null })
  return pending
}

export function useLineStatus() {
  void ensureReady()
  return { state, refresh, ensureReady }
}
