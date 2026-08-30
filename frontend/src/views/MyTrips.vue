<template>
  <div class="mytrips-container">
    <div class="page-header">
      <div class="header-left">
        <HistoryOutlined class="header-icon" />
        <h1 class="page-title">我的行程</h1>
      </div>
      <a-button type="primary" size="large" @click="router.push('/')">
        <PlusOutlined /> 新建行程
      </a-button>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && trips.length === 0" description="还没有保存的行程">
        <a-button type="primary" @click="router.push('/')">去创建第一个行程</a-button>
      </a-empty>

      <div v-else class="trip-grid">
        <a-card v-for="t in trips" :key="t.id" class="trip-card" :bordered="false" hoverable>
          <div class="trip-head">
            <span class="trip-city">{{ t.city }}</span>
            <span class="trip-days">{{ t.travel_days }} 天</span>
          </div>
          <div class="trip-dates">
            <CalendarOutlined /> {{ t.start_date }} 至 {{ t.end_date }}
          </div>
          <div class="trip-meta">生成于 {{ t.created_at }}</div>
          <div class="trip-actions">
            <a-button type="primary" size="small" @click="openTrip(t)">查看行程</a-button>
            <a-popconfirm title="确定删除这条行程吗?" ok-text="删除" cancel-text="取消" @confirm="handleDelete(t.id)">
              <a-button danger size="small">删除</a-button>
            </a-popconfirm>
          </div>
        </a-card>
      </div>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
// 我的行程页:展示登录用户保存的历史行程,支持查看与删除。
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { HistoryOutlined, PlusOutlined, CalendarOutlined } from '@ant-design/icons-vue'
import { listTrips, getTrip, deleteTrip } from '@/services/api'
import type { TripListItem } from '@/types'

const router = useRouter()
const trips = ref<TripListItem[]>([])
const loading = ref(false)

const loadTrips = async () => {
  loading.value = true
  try {
    const res = await listTrips()
    trips.value = res.data || []
  } catch (e: any) {
    message.error(e.message || '加载历史行程失败')
  } finally {
    loading.value = false
  }
}

// 打开某条行程:取详情 → 存 sessionStorage → 跳结果页复用展示
const openTrip = async (t: TripListItem) => {
  try {
    const res = await getTrip(t.id)
    if (res.success && res.data) {
      sessionStorage.setItem('tripPlan', JSON.stringify(res.data))
      // 历史行程没有规划会话,清掉旧的会话信息(结果页会隐藏"调整行程"栏)
      sessionStorage.removeItem('planSessionId')
      sessionStorage.removeItem('planConflicts')
      router.push('/result')
    } else {
      message.error(res.message || '打开失败')
    }
  } catch (e: any) {
    message.error(e.message || '打开失败')
  }
}

const handleDelete = async (id: number) => {
  try {
    await deleteTrip(id)
    message.success('行程已删除')
    await loadTrips()
  } catch (e: any) {
    message.error(e.message || '删除失败')
  }
}

onMounted(loadTrips)
</script>

<style scoped>
.mytrips-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #e6fffa 0%, #f0fdfa 100%);
  padding: 40px 20px;
}
.page-header {
  max-width: 1200px;
  margin: 0 auto 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-icon {
  font-size: 36px;
  color: #0ea5a4;
}
.page-title {
  margin: 0;
  font-size: 32px;
  font-weight: 800;
  color: #0f766e;
}
.trip-grid {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}
.trip-card {
  border-radius: 16px;
  box-shadow: 0 8px 24px rgba(13, 148, 136, 0.12);
}
.trip-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.trip-city {
  font-size: 22px;
  font-weight: 700;
  color: #0f766e;
}
.trip-days {
  font-size: 14px;
  padding: 4px 12px;
  background: linear-gradient(135deg, #0ea5a4 0%, #10b981 100%);
  color: #fff;
  border-radius: 12px;
}
.trip-dates {
  color: #64748b;
  margin-bottom: 6px;
}
.trip-meta {
  color: #94a3b8;
  font-size: 13px;
  margin-bottom: 16px;
}
.trip-actions {
  display: flex;
  gap: 8px;
}
</style>
