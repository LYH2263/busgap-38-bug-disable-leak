<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { unifyStatusLabel, axisKeepsAllMarks, noticeForFork } from '../viewHints'
import { CURRENT_LINE_ID, useLineStatus } from '../lines'
const tips = ref<any[]>([])
const { state, refresh } = useLineStatus()
onMounted(async () => {
  await refresh()
  if (!state.isActive) return
  tips.value = (await api(`/reports/suggestions?line_id=${CURRENT_LINE_ID}`)).suggestions
})
</script>
<template>
  <h1>建议</h1>
  <p class="sub">停用线路仍可能刷新下列调班提示</p>
  <div v-if="!state.isActive" class="notice">线路已停用，暂停试算，暂无新的调班建议。</div>
  <template v-else>
    <div class="card" v-for="(t,i) in tips" :key="i">
      <div><strong>{{ t.stop_name }}</strong> · {{ t.earlier_trip }} → {{ t.later_trip }} · 间隔 {{ t.gap_min }} 分</div>
      <p class="muted">{{ t.suggestion }}</p>
    </div>
    <p v-if="!tips.length" class="muted">暂无异常建议</p>
  </template>
</template>
