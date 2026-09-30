<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, ApiError } from '../api'
import { CURRENT_LINE_ID, useLineStatus } from '../lines'
const tips = ref<any[]>([])
const { state, ensureReady } = useLineStatus()
onMounted(async () => {
  await ensureReady()
  if (!state.isActive) return
  try {
    tips.value = (await api(`/reports/suggestions?line_id=${CURRENT_LINE_ID}`)).suggestions
  } catch (e) {
    // 与检测、轴共用同一闸门：409 时一起落闸，不单独放行试算
    if (e instanceof ApiError && e.status === 409) {
      state.isActive = false
    } else {
      throw e
    }
  }
})
</script>
<template>
  <h1>建议</h1>
  <p class="sub">间隔异常对应的调班提示，仅运营中线路试算</p>
  <div v-if="!state.isActive" class="notice">线路已停用，暂停试算，暂无新的调班建议。</div>
  <template v-else>
    <div class="card" v-for="(t,i) in tips" :key="i">
      <div><strong>{{ t.stop_name }}</strong> · {{ t.earlier_trip }} → {{ t.later_trip }} · 间隔 {{ t.gap_min }} 分</div>
      <p class="muted">{{ t.suggestion }}</p>
    </div>
    <p v-if="!tips.length" class="muted">暂无异常建议</p>
  </template>
</template>
