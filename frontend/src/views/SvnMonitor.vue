<template>
  <div>
    <!-- 状态卡片 -->
    <el-card shadow="hover" style="margin-bottom: 16px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-weight: 600">SVN 监控状态</span>
          <el-button type="primary" size="small" :loading="checking" @click="manualCheck">
            <el-icon><Refresh /></el-icon> 手动检查
          </el-button>
        </div>
      </template>
      <PageState :empty="!status.latest_revision" description="暂无 SVN 版本记录">
      <el-descriptions :column="3" border>
        <el-descriptions-item label="最新版本">
          <el-tag type="primary">r{{ status.latest_revision.revision }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="提交者">{{ status.latest_revision.author || '-' }}</el-descriptions-item>
        <el-descriptions-item label="检测时间">{{ formatTime(status.latest_revision.detected_at) }}</el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ formatTime(status.latest_revision.commit_time) }}</el-descriptions-item>
        <el-descriptions-item label="已触发测试" :span="2">
          <el-tag :type="status.latest_revision.triggered_run ? 'success' : 'info'" size="small">
            {{ status.latest_revision.triggered_run ? '是' : '否' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="提交消息" :span="3">
          {{ status.latest_revision.message || '-' }}
        </el-descriptions-item>
      </el-descriptions>
      </PageState>
    </el-card>

    <!-- 提交历史 -->
    <el-card shadow="hover">
      <template #header>
        <span style="font-weight: 600">提交历史</span>
      </template>
      <el-table :data="history" stripe>
        <el-table-column prop="revision" label="版本号" width="100">
          <template #default="{ row }">
            <el-tag size="small">r{{ row.revision }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="author" label="提交者" width="120" />
        <el-table-column prop="message" label="提交消息" min-width="300" show-overflow-tooltip />
        <el-table-column label="提交时间" width="180">
          <template #default="{ row }">{{ formatTime(row.commit_time) }}</template>
        </el-table-column>
        <el-table-column label="已触发测试" width="120">
          <template #default="{ row }">
            <el-tag :type="row.triggered_run ? 'success' : 'info'" size="small">
              {{ row.triggered_run ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="检测时间" width="180">
          <template #default="{ row }">{{ formatTime(row.detected_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'
import PageState from '../components/PageState.vue'

const status = ref({})
const history = ref([])
const checking = ref(false)

const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN') : '-'

const loadStatus = async () => {
  const res = await api.get('/svn/status')
  status.value = res.data
}

const loadHistory = async () => {
  const res = await api.get('/svn/history')
  history.value = res.data.revisions
}

const manualCheck = async () => {
  checking.value = true
  try {
    const res = await api.post('/svn/check')
    if (res.data.has_update) {
      ElMessage.success(`发现新版本: r${res.data.revision.revision}`)
    } else {
      ElMessage.info('没有新的 SVN 更新')
    }
    await loadStatus()
    await loadHistory()
  } catch {
    // handled by interceptor
  } finally {
    checking.value = false
  }
}

onMounted(() => {
  loadStatus()
  loadHistory()
})
</script>
