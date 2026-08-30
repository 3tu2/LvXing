<template>
  <div class="users">
    <h2 class="page-title">用户管理</h2>
    <a-table :data-source="users" :columns="columns" row-key="id" :loading="loading" :pagination="{ pageSize: 10 }">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="record.status === 'active' ? 'green' : 'red'">
            {{ record.status === 'active' ? '正常' : '已禁用' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'role'">
          <a-tag :color="record.role === 'admin' ? 'purple' : 'default'">
            {{ record.role === 'admin' ? '管理员' : '用户' }}
          </a-tag>
        </template>
        <template v-if="column.key === 'action'">
          <a-popconfirm
            :title="record.status === 'active' ? '确定禁用该用户?' : '确定恢复该用户?'"
            @confirm="toggleStatus(record)"
          >
            <a-button size="small" :danger="record.status === 'active'">
              {{ record.status === 'active' ? '禁用' : '恢复' }}
            </a-button>
          </a-popconfirm>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { listAdminUsers, updateUserStatus } from '@/services/api'
import type { AdminUserItem } from '@/types'

const users = ref<AdminUserItem[]>([])
const loading = ref(false)

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: '用户名', dataIndex: 'username', key: 'username' },
  { title: '昵称', dataIndex: 'nickname', key: 'nickname' },
  { title: '角色', dataIndex: 'role', key: 'role' },
  { title: '状态', dataIndex: 'status', key: 'status' },
  { title: '行程数', dataIndex: 'trips_count', key: 'trips_count', width: 80 },
  { title: '注册时间', dataIndex: 'created_at', key: 'created_at' },
  { title: '操作', key: 'action', width: 90 },
]

const load = async () => {
  loading.value = true
  try {
    users.value = await listAdminUsers()
  } catch (e: any) {
    message.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const toggleStatus = async (record: AdminUserItem) => {
  const next = record.status === 'active' ? 'disabled' : 'active'
  try {
    await updateUserStatus(record.id, next)
    message.success(next === 'active' ? '已恢复' : '已禁用')
    await load()
  } catch (e: any) {
    message.error(e.message || '操作失败')
  }
}

onMounted(load)
</script>

<style scoped>
.users { padding: 20px; }
.page-title { margin: 0 0 20px; color: #0f766e; }
</style>
