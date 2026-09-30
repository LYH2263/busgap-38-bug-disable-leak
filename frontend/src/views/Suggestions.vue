<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { CURRENT_LINE_ID, useLineStatus } from '../lines'
const tips = ref<any[]>([])
const loadError = ref('')
const { state, refresh } = useLineStatus()

function errorToNotice(e: any): string {
  const raw = String(e?.message || '')
  // 停用与「没有到站」互斥：停用时只说明线路已停用。
  if (raw.includes('线路已停用')) return '线路已停用'
  if (raw.includes('没有到站')) return '没有到站'
  return raw || '试算失败'
}

onMounted(async () => {
  await refresh()
  // 建议刷新（试算）与检测共用闸门：停用不发请求，与后端 409 双保险。
  if (!state.isActive) return
  try {
    tips.value = (await api(`/reports/suggestions?line_id=${CURRENT_LINE_ID}`)).suggestions
  } catch (e: any) {
    loadError.value = errorToNotice(e)
    await refresh()
  }
})
</script>
<template>
  <h1>建议</h1>
  <p class="sub">停用线路后暂停试算，不刷新调班提示</p>
  <div v-if="!state.isActive" class="notice">线路已停用，暂停试算，暂无新的调班建议。</div>
  <div v-else-if="loadError" class="notice">{{ loadError }}</div>
  <template v-else>
    <div class="card" v-for="(t,i) in tips" :key="i">
      <div><strong>{{ t.stop_name }}</strong> · {{ t.earlier_trip }} → {{ t.later_trip }} · 间隔 {{ t.gap_min }} 分</div>
      <p class="muted">{{ t.suggestion }}</p>
    </div>
    <p v-if="!tips.length" class="muted">暂无异常建议</p>
  </template>
</template>
