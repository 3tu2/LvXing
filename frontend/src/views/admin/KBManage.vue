<template>
  <div class="kb">
    <div class="kb-header">
      <h2 class="page-title">知识库管理</h2>
      <a-space>
        <a-button @click="load">刷新</a-button>
        <a-button :loading="importing" @click="triggerImport">批量导入</a-button>
        <a-button type="primary" @click="openAdd">+ 添加知识</a-button>
      </a-space>
    </div>
    <input
      ref="fileInputRef"
      type="file"
      accept=".md,.json,.txt"
      multiple
      style="display: none"
      @change="handleImport"
    />
    <a-alert
      type="info"
      show-icon
      message="知识库可通过离线脚本批量摄取(python scripts/kb_ingest.py),也可在此单条增删改"
      style="margin-bottom: 16px"
    />

    <a-table :data-source="items" :columns="columns" row-key="id" :loading="loading" :pagination="{ pageSize: 10 }">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'category'">
          <a-tag color="cyan">{{ record.category }}</a-tag>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button size="small" @click="openEdit(record)">编辑</a-button>
            <a-popconfirm title="确定删除这条知识?" @confirm="handleDelete(record)">
              <a-button size="small" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 添加/编辑弹窗 -->
    <a-modal
      v-model:open="modalOpen"
      :title="editing ? '编辑知识' : '添加知识'"
      :confirm-loading="saving"
      @ok="handleSubmit"
      :width="640"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="类别" required>
          <a-select v-model:value="form.category" :options="categoryOptions" />
        </a-form-item>
        <a-form-item label="标题">
          <a-input v-model:value="form.title" placeholder="如: 滕王阁 / 南昌拌粉" />
        </a-form-item>
        <a-form-item label="关联景点名(可选,用于营业时间等精确匹配)">
          <a-input v-model:value="form.poi_name" placeholder="如: 滕王阁" />
        </a-form-item>
        <a-form-item label="知识内容" required>
          <a-textarea v-model:value="form.text" :rows="6" placeholder="填写知识内容,会被切片并向量化" />
        </a-form-item>
        <a-form-item label="来源">
          <a-input v-model:value="form.source" placeholder="如: 后台添加 / 公开资料整理" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { listKb, deleteKb, addKb, updateKb, importKbFiles, type KBPayload } from '@/services/api'
import type { KBItem } from '@/types'

const items = ref<KBItem[]>([])
const loading = ref(false)
const modalOpen = ref(false)
const saving = ref(false)
const editing = ref(false)
const editId = ref('')
const importing = ref(false)
const fileInputRef = ref<HTMLInputElement>()

const categoryOptions = ['攻略', '景点', '美食', '拍照点', '交通枢纽', '营业时间'].map((c) => ({ label: c, value: c }))

const form = reactive<KBPayload>({ text: '', category: '攻略', title: '', source: '后台添加', poi_name: '' })

const columns = [
  { title: '类别', dataIndex: 'category', key: 'category', width: 100 },
  { title: '标题', dataIndex: 'title', key: 'title', width: 180 },
  { title: '内容摘要', dataIndex: 'text', key: 'text', ellipsis: true },
  { title: '来源', dataIndex: 'source', key: 'source', width: 160 },
  { title: '操作', key: 'action', width: 140 },
]

const load = async () => {
  loading.value = true
  try {
    items.value = await listKb()
  } catch (e: any) {
    message.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.text = ''
  form.category = '攻略'
  form.title = ''
  form.source = '后台添加'
  form.poi_name = ''
}

const openAdd = () => {
  editing.value = false
  editId.value = ''
  resetForm()
  modalOpen.value = true
}

const openEdit = (record: KBItem) => {
  editing.value = true
  editId.value = record.id
  form.text = record.text
  form.category = record.category || '攻略'
  form.title = record.title
  form.source = record.source
  form.poi_name = ''
  modalOpen.value = true
}

const handleSubmit = async () => {
  if (!form.text.trim()) {
    message.warning('请填写知识内容')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await updateKb(editId.value, form)
      message.success('知识已更新')
    } else {
      await addKb(form)
      message.success('知识已添加')
    }
    modalOpen.value = false
    await load()
  } catch (e: any) {
    message.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const handleDelete = async (record: KBItem) => {
  try {
    await deleteKb(record.id)
    message.success('已删除')
    await load()
  } catch (e: any) {
    message.error(e.message || '删除失败')
  }
}

const triggerImport = () => {
  fileInputRef.value?.click()
}

const handleImport = async (e: Event) => {
  const input = e.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (!files.length) return
  importing.value = true
  try {
    const res = await importKbFiles(files)
    message.success(res.message)
    await load()
  } catch (err: any) {
    message.error(err.message || '导入失败')
  } finally {
    importing.value = false
    input.value = ''
  }
}

onMounted(load)
</script>

<style scoped>
.kb { padding: 20px; }
.kb-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-title { margin: 0; color: #0f766e; }
</style>
