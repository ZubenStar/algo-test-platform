<template>
  <div>
    <!-- 操作栏 -->
    <el-card shadow="hover" style="margin-bottom: 16px">
      <div style="display: flex; justify-content: space-between; align-items: center">
        <span style="font-weight: 600; font-size: 16px">任务管理</span>
        <el-button type="primary" @click="triggerRun" :loading="triggering">
          <el-icon><VideoPlay /></el-icon> 手动触发测试
        </el-button>
      </div>
    </el-card>

    <!-- 运行中的任务 -->
    <el-card shadow="hover" style="margin-bottom: 16px" v-if="running.length > 0">
      <template #header>
        <div style="display: flex; align-items: center; gap: 8px">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span style="font-weight: 600">运行中的任务 ({{ running.length }})</span>
        </div>
      </template>
      <el-table :data="running" stripe>
        <el-table-column prop="id" label="Run ID" width="100" />
        <el-table-column label="SVN 版本" width="120">
          <template #default="{ row }">{{ row.svn_revision?.revision || '-' }}</template>
        </el-table-column>
        <el-table-column label="触发方式" width="100">
          <template #default="{ row }">
            <el-tag :type="row.triggered_by === 'auto' ? 'success' : 'warning'" size="small">
              {{ row.triggered_by === 'auto' ? '自动' : '手动' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'running' ? '' : 'info'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" min-width="200">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :stroke-width="16" :text-inside="true" />
          </template>
        </el-table-column>
        <el-table-column label="完成/失败" width="140">
          <template #default="{ row }">
            {{ row.completed_tasks }} / <span style="color: #f56c6c">{{ row.failed_tasks }}</span>
            (共 {{ row.total_tasks }})
          </template>
        </el-table-column>
        <el-table-column label="开始时间" width="180">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 最近完成的任务 -->
    <el-card shadow="hover">
      <template #header>
        <span style="font-weight: 600">最近完成的任务</span>
      </template>
      <el-table :data="completed" stripe>
        <el-table-column prop="id" label="Run ID" width="100" />
        <el-table-column label="SVN 版本" width="120">
          <template #default="{ row }">{{ row.svn_revision?.revision || '-' }}</template>
        </el-table-column>
        <el-table-column label="触发方式" width="100">
          <template #default="{ row }">
            <el-tag :type="row.triggered_by === 'auto' ? 'success' : 'warning'" size="small">
              {{ row.triggered_by === 'auto' ? '自动' : '手动' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : 'danger'" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="160">
          <template #default="{ row }">
            <span style="color: #67c23a">✓ {{ row.completed_tasks - row.failed_tasks }}</span>
            <span style="margin: 0 4px">/</span>
            <span style="color: #f56c6c">✗ {{ row.failed_tasks }}</span>
            <span style="color: #909399"> ({{ row.total_tasks }})</span>
          </template>
        </el-table-column>
        <el-table-column label="开始时间" min-width="180">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="完成时间" min-width="180">
          <template #default="{ row }">{{ formatTime(row.finished_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button v-if="row.failed_tasks > 0" type="warning" size="small" text @click="retryRun(row.id)">
              重试失败
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const running = ref([])
const completed = ref([])
const triggering = ref(false)
let timer = null

const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN') : '-'
const statusText = (s) => ({ completed: '已完成', failed: '失败' }[s] || s)

const loadRunning = async () => {
  const res = await api.get('/tasks/running')
  running.value = res.data.runs
}

const loadCompleted = async () => {
  const res = await api.get('/results/runs', { params: { per_page: 15, status: 'completed' } })
  // 也加载 failed 的
  const res2 = await api.get('/results/runs', { params: { per_page: 15, status: 'failed' } })
  const all = [...res.data.runs, ...res2.data.runs]
  all.sort((a, b) => b.id - a.id)
  completed.value = all.slice(0, 20)
}

const triggerRun = async () => {
  triggering.value = true
  try {
    const res = await api.post('/tasks/trigger')
    ElMessage.success(`测试任务已触发: Run #${res.data.run.id}`)
    await loadRunning()
  } catch {
    // handled
  } finally {
    triggering.value = false
  }
}

const retryRun = async (runId) => {
  try {
    const res = await api.post(`/tasks/retry/${runId}`)
    ElMessage.success(res.data.message)
    await loadRunning()
    await loadCompleted()
  } catch {
    // handled
  }
}

// 自动刷新运行中的任务
const startPolling = () => {
  timer = setInterval(() => {
    if (running.value.length > 0) {
      loadRunning()
    }
  }, 5000)
}

onMounted(() => {
  loadRunning()
  loadCompleted()
  startPolling()
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
