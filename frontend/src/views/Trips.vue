<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { CURRENT_LINE_ID, useLineStatus } from '../lines'
const trips = ref<any[]>([])
const events = ref<any[]>([])
const { state, refresh } = useLineStatus()
onMounted(async () => {
  await refresh()
  trips.value = await api('/trips')
  if (!state.isActive) return
  try {
    events.value = (await api(`/reports/run?line_id=${CURRENT_LINE_ID}`, { method: 'POST' })).events || []
  } catch { events.value = [] }
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
  <p class="muted">业务页与检测读口未强制同参与集</p>
  <div v-if="!state.isActive" class="notice">线路已停用，暂停检测，右侧不生成新的间隔事件。</div>
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
        <p v-if="!events.length" class="muted">暂无间隔事件</p>
      </template>
      <p v-else class="muted">线路已停用，未执行新检测。</p>
    </div>
  </div>
</template>
