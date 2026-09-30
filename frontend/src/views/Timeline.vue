<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { CURRENT_LINE_ID, useLineStatus } from '../lines'
const data = ref<{ stop_name: string; marks: any[]; is_active: boolean }>({ stop_name: '', marks: [], is_active: true })
const loadError = ref('')
const { state, refresh } = useLineStatus()
onMounted(async () => {
  await refresh()
  // 轴是只读视图：停用线路仍可打开，照常显示历史到站，不发起任何新检测。
  try {
    const body = await api(`/reports/timeline?line_id=${CURRENT_LINE_ID}`)
    data.value = body
    state.isActive = body.is_active !== false
  } catch (e: any) {
    // 停用与「没有到站」互斥：绝不能把停用提示写成没有到站。
    const raw = String(e?.message || '')
    loadError.value = raw.includes('线路已停用') ? '线路已停用' : '没有到站'
  }
})
</script>
<template>
  <h1>时间轴明细</h1>
  <p class="sub">站点「{{ data.stop_name }}」到站分布（顶部已展示发车间隔轴）</p>
  <p v-if="!state.isActive" class="notice">线路已停用，以下为停用前历史到站（只读），不会触发新检测。</p>
  <p v-else-if="loadError" class="notice">{{ loadError }}</p>
  <div class="card">
    <div class="tl-track">
      <div v-for="m in data.marks" :key="m.trip_no" class="tl-mark"
        :style="{ left: m.pct + '%', background: m.pct < 15 ? 'var(--bg-red)' : 'var(--bg-cyan)' }"
        :title="m.trip_no + ' ' + m.actual_arrive" />
    </div>
    <table>
      <thead><tr><th>班次</th><th>到站时间</th><th>相对位置</th></tr></thead>
      <tbody>
        <tr v-for="m in data.marks" :key="m.trip_no">
          <td>{{ m.trip_no }}</td><td>{{ m.actual_arrive }}</td><td>{{ m.pct }}%</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
