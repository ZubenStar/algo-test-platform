<template>
  <div>
    <el-card shadow="hover">
      <template #header>
        <span style="font-weight: 600">审计日志</span>
      </template>
      <PageState :loading="loading" :empty="logs.length === 0" description="暂无审计日志">
        <el-table :data="logs" stripe>
          <el-table-column prop="created_at" label="时间" width="180">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column prop="username" label="用户" width="120" />
          <el-table-column prop="action" label="操作" width="140" />
          <el-table-column prop="target_type" label="对象类型" width="140" />
          <el-table-column prop="target_id" label="对象 ID" width="120" />
          <el-table-column label="详情" min-width="240" show-overflow-tooltip>
            <template #default="{ row }">{{ JSON.stringify(row.detail || {}) }}</template>
          </el-table-column>
        </el-table>
      </PageState>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '../api'
import PageState from '../components/PageState.vue'

const logs = ref([])
const loading = ref(false)

const formatTime = (value) => value ? new Date(value).toLocaleString('zh-CN') : '-'

const loadLogs = async () => {
  loading.value = true
  try {
    const res = await api.get('/audit')
    logs.value = res.data.logs
  } finally {
    loading.value = false
  }
}

onMounted(loadLogs)
</script>
