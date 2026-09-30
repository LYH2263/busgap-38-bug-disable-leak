<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, ApiError } from '../api'
import { unifyStatusLabel } from '../viewHints'
import { CURRENT_LINE_ID, useLineStatus } from '../lines'
const data = ref<{ stop_name: string; marks: any[]; is_active: boolean }>({ stop_name: '', marks: [], is_active: true })
const loadError = ref('')
const { state, ensureReady } = useLineStatus()
onMounted(async () => {
  await ensureReady()
  try {
    data.value = await api(`/reports/timeline?line_id=${CURRENT_LINE_ID}`)
    // 以轴返回的实时状态为准，三处提示保持一致
    state.isActive = data.value.is_active !== false
  } catch (e) {
    // 停用走 200 + is_active=false；真正失败（如线路缺失/无到站）才落到这里
    loadError.value = e instanceof ApiError ? e.message : '没有到站'
  }
})
</script>
<template>
  <h1>时间轴明细</h1>
  <p class="sub">站点「{{ data.stop_name }}」到站分布（顶部已展示发车间隔轴）</p>
  <p v-if="!state.isActive" class="notice">线路已停用，轴上仅展示历史到站，不发起新检测。</p>
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
