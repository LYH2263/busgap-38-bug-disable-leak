<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { useLineStatus } from '../lines'
const rows = ref<any[]>([])
const busyId = ref<number | null>(null)
const { refresh } = useLineStatus()

async function load() {
  rows.value = await api('/lines')
}
async function toggle(r: any) {
  busyId.value = r.id
  try {
    await api(`/lines/${r.id}/${r.is_active ? 'deactivate' : 'activate'}`, { method: 'POST' })
    await load()
    await refresh()
  } finally {
    busyId.value = null
  }
}
onMounted(load)
</script>
<template>
  <h1>线路</h1>
  <p class="sub">运营线路与串车 / 大间隔判定阈值</p>
  <p class="muted">停用后检测、试算与建议刷新一起拦截，历史报告与时间轴保留只读</p>
  <div class="card">
    <table>
      <thead><tr><th>编码</th><th>名称</th><th>计划间隔(分)</th><th>串车阈值</th><th>大间隔阈值</th><th>状态</th><th>操作</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)">
          <td>{{ r.code }}</td><td>{{ r.name }}</td>
          <td>{{ r.planned_headway_min }}</td><td>{{ r.bunch_threshold }}</td><td>{{ r.large_threshold }}</td>
          <td>
            <span class="badge" :class="r.is_active ? 'badge-ok' : 'badge-warn'">
              {{ r.is_active ? '运营中' : '已停用' }}
            </span>
          </td>
          <td>
            <button
              v-if="r.is_active"
              class="btn-danger"
              :disabled="busyId === r.id"
              @click="toggle(r)"
            >停用</button>
            <button
              v-else
              class="btn-ghost"
              :disabled="busyId === r.id"
              @click="toggle(r)"
            >启用</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
