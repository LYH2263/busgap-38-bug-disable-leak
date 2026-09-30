<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { api } from './api'
import { CURRENT_LINE_ID, useLineStatus } from './lines'

const marks = ref<any[]>([])
const stopName = ref('')
const { state, ensureReady } = useLineStatus()

onMounted(async () => {
  await ensureReady()
  // 轴只读：GET timeline 不触发检测、不新增报告；停用时照常展示历史到站。
  try {
    const data = await api(`/reports/timeline?line_id=${CURRENT_LINE_ID}`)
    marks.value = data.marks || []
    stopName.value = data.stop_name || ''
    state.isActive = data.is_active !== false
  } catch {
    marks.value = []
  }
})
</script>
<template>
  <div class="bg-shell">
    <header class="bg-headway">
      <div class="bg-headway-meta">
        <span class="bg-brand">BusGap · 串车检测</span>
        <span class="bg-stop">发车间隔轴 · {{ stopName || '主站' }}</span>
        <span v-if="!state.isActive" class="badge badge-warn">线路已停用</span>
      </div>
      <div class="bg-rail">
        <div class="bg-rail-ticks">
          <span v-for="t in 11" :key="t">{{ (t - 1) * 10 }}%</span>
        </div>
        <div class="bg-rail-track">
          <div
            v-for="m in marks"
            :key="m.trip_no"
            class="bg-bus-dot"
            :class="{ 'bg-bus-tight': m.pct < 15 }"
            :style="{ left: m.pct + '%' }"
            :title="`${m.trip_no} ${m.actual_arrive}`"
          >
            <span class="bg-bus-label">{{ m.trip_no }}</span>
          </div>
        </div>
      </div>
      <nav class="bg-segments">
        <RouterLink to="/timeline">时间轴</RouterLink>
        <RouterLink to="/trips">班次</RouterLink>
        <RouterLink to="/arrivals">到站</RouterLink>
        <RouterLink to="/reports">串车报告</RouterLink>
        <RouterLink to="/lines">线路</RouterLink>
        <RouterLink to="/suggestions">建议</RouterLink>
      </nav>
    </header>
    <div class="bg-deck">
      <RouterView />
    </div>
  </div>
</template>
