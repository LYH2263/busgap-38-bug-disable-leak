<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { CURRENT_LINE_ID, useLineStatus } from '../lines'
const trips = ref<any[]>([])
const events = ref<any[]>([])
const runError = ref('')
const { state, refresh } = useLineStatus()

function errorToNotice(e: any): string {
  const raw = String(e?.message || '')
  // 停用与「没有到站」互斥：停用时只说明线路已停用。
  if (raw.includes('线路已停用')) return '线路已停用'
  if (raw.includes('没有到站')) return '没有到站'
  return raw || '检测失败'
}

onMounted(async () => {
  await refresh()
  trips.value = await api('/trips')
  // 停用即闸门：不发检测请求，避免后台仍触发新检、生成新行。
  if (!state.isActive) return
  try {
    events.value = (await api(`/reports/run?line_id=${CURRENT_LINE_ID}`, { method: 'POST' })).events || []
  } catch (e: any) {
    events.value = []
    runError.value = errorToNotice(e)
    await refresh()
  }
})
function stripClass(s: string) {
  return s === 'bunching' ? 'bg-bunch' : s === 'large_gap' ? 'bg-large' : ''
}
function label(s: string) {
  return s === 'bunching' ? '串车' : s === 'large_gap' ? '大间隔' : '正常'
}
</script>
<template>
  <h1>班次 · 间隔条带</h1>
  <p class="sub">左侧班次清单，右侧串车/间隔竖直条带</p>
  <div v-if="!state.isActive" class="notice">线路已停用，暂停检测，右侧不生成新的间隔事件。</div>
  <div v-else-if="runError" class="notice">{{ runError }}</div>
  <div class="bg-split">
    <aside class="bg-trip-col">
      <h2>班次列表</h2>
      <div v-for="r in trips" :key="r.id ?? r.trip_no" class="bg-trip-row">
        <div>
          <div>{{ r.trip_no }}</div>
          <div class="bg-trip-meta">线路 {{ r.line_id }} · 车 {{ r.vehicle_no }}</div>
        </div>
        <div class="bg-trip-meta">{{ r.planned_depart }}</div>
      </div>
    </aside>
    <div class="bg-strip-col">
      <template v-if="state.isActive">
        <article
          v-for="(e, i) in events"
          :key="i"
          class="bg-gap-strip"
          :class="stripClass(e.status)"
        >
          <header>{{ e.stop_name }}</header>
          <div class="bg-gap-body">
            <div class="bg-gap-val">{{ e.gap_min }}′</div>
            <div>计划 {{ e.planned_headway_min }}′</div>
            <div>{{ e.earlier_trip }} → {{ e.later_trip }}</div>
            <span class="badge" :class="e.status === 'bunching' ? 'badge-bad' : e.status === 'large_gap' ? 'badge-warn' : 'badge-ok'">
              {{ label(e.status) }}
            </span>
          </div>
        </article>
        <p v-if="!events.length && !runError" class="muted">暂无间隔事件</p>
      </template>
      <p v-else class="muted">线路已停用，未执行新检测。</p>
    </div>
  </div>
</template>
