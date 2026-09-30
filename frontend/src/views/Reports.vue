<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, ApiError } from '../api'
import { unifyStatusLabel } from '../viewHints'
import { CURRENT_LINE_ID, useLineStatus } from '../lines'
const trips = ref<any[]>([])
const events = ref<any[]>([])
const history = ref<any[]>([])
const openReportId = ref<number | null>(null)
const loading = ref(false)
const notice = ref('')
const { state, refresh, ensureReady } = useLineStatus()

async function loadHistory() {
  // 历史报告只读：停用期间整栏仍在、可展开，且不会被新检测改写。
  history.value = await api('/reports')
}

async function run() {
  if (!state.isActive) return
  loading.value = true
  notice.value = ''
  try {
    events.value = (await api(`/reports/run?line_id=${CURRENT_LINE_ID}`, { method: 'POST' })).events || []
    await loadHistory()
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) {
      // 与后端闸门对齐：停用与「没有到站」互斥，只显示线路已停用。
      notice.value = '线路已停用，未执行新检测。'
      state.isActive = false
      events.value = []
    } else if (e instanceof ApiError && e.status === 404) {
      notice.value = e.message || '没有到站'
    } else {
      throw e
    }
  } finally { loading.value = false }
}

onMounted(async () => {
  await ensureReady()
  trips.value = await api('/trips')
  await loadHistory()
  if (state.isActive) await run()
})
function stripClass(s: string) {
  return s === 'bunching' ? 'bg-bunch' : s === 'large_gap' ? 'bg-large' : ''
}
function label(s: string) {
  return unifyStatusLabel(s)
}
</script>
<template>
  <h1>串车报告</h1>
  <p class="sub">按实际到站间隔对照计划发车间隔 · 竖直条带展示</p>
  <div v-if="!state.isActive" class="notice">
    线路已停用，检测已拦截，历史报告仍可只读查看。
  </div>
  <div v-else-if="notice" class="notice">{{ notice }}</div>
  <button v-if="state.isActive" class="btn" :disabled="loading" @click="run">重新检测</button>
  <div class="bg-split" style="margin-top:1rem">
    <aside class="bg-trip-col">
      <h2>关联班次</h2>
      <div v-for="r in trips" :key="r.id ?? r.trip_no" class="bg-trip-row">
        <div>
          <div>{{ r.trip_no }}</div>
          <div class="bg-trip-meta">{{ r.vehicle_no }}</div>
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
      </template>
      <p v-else class="muted">线路已停用，未执行新检测。</p>
    </div>
  </div>

  <h2 style="margin:1.2rem 0 0.6rem;font-size:1rem">历史报告</h2>
  <div class="card" v-for="r in history" :key="r.id">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:0.6rem">
      <div>
        <strong>#{{ r.id }}</strong>
        <span class="muted" style="margin-left:0.5rem">线路 {{ r.line_id }} · 站点 {{ r.stop_name }} · {{ r.created_at }}</span>
      </div>
      <button class="btn-ghost" @click="openReportId = openReportId === r.id ? null : r.id">{{ openReportId === r.id ? '收起' : '查看' }}</button>
    </div>
    <div v-if="openReportId === r.id" class="bg-strip-col" style="margin-top:0.7rem;min-height:auto">
      <article
        v-for="(e, i) in r.events"
        :key="i"
        class="bg-gap-strip"
        :class="stripClass(e.status)"
        style="min-height:200px"
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
      <p v-if="!r.events.length" class="muted">该报告无间隔事件</p>
    </div>
  </div>
  <p v-if="!history.length" class="muted">暂无历史报告</p>
</template>
