<template>
  <div class="dashboard">
    <h2 class="page-title">仪表盘</h2>
    <a-row :gutter="16">
      <a-col :span="6">
        <a-card :bordered="false" class="stat-card">
          <a-statistic title="注册用户" :value="stats.users_count" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :bordered="false" class="stat-card">
          <a-statistic title="行程总数" :value="stats.trips_count" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :bordered="false" class="stat-card">
          <a-statistic title="问答对话" :value="stats.chat_count" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :bordered="false" class="stat-card">
          <a-statistic title="知识库切片" :value="stats.kb_chunks" />
        </a-card>
      </a-col>
    </a-row>

    <a-card title="近 7 日行程趋势" :bordered="false" class="trend-card">
      <div class="trend">
        <div v-for="d in stats.trips_last_7d" :key="d.date" class="trend-item">
          <div class="trend-value">{{ d.count }}</div>
          <div class="trend-bar" :style="{ height: Math.min(d.count * 24, 120) + 'px' }"></div>
          <div class="trend-date">{{ d.date.slice(5) }}</div>
        </div>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getAdminStats } from '@/services/api'
import type { AdminStats } from '@/types'

const stats = ref<AdminStats>({
  users_count: 0, trips_count: 0, chat_count: 0, kb_chunks: 0, trips_last_7d: [],
})

onMounted(async () => {
  try {
    stats.value = await getAdminStats()
  } catch (e) {
    console.error(e)
  }
})
</script>

<style scoped>
.dashboard { padding: 20px; }
.page-title { margin: 0 0 20px; color: #0f766e; }
.stat-card { border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.trend-card { margin-top: 20px; border-radius: 12px; }
.trend { display: flex; align-items: flex-end; gap: 16px; height: 160px; padding: 8px; }
.trend-item { display: flex; flex-direction: column; align-items: center; gap: 4px; flex: 1; }
.trend-value { font-size: 14px; color: #0ea5a4; font-weight: 600; }
.trend-bar { width: 28px; background: linear-gradient(180deg, #0ea5a4 0%, #10b981 100%); border-radius: 6px 6px 0 0; min-height: 2px; }
.trend-date { font-size: 12px; color: #94a3b8; }
</style>
