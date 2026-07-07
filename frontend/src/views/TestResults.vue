<template>
  <div>
    <!-- 测试轮次列表 -->
    <el-card shadow="hover" style="margin-bottom: 16px" v-if="!route.params.runId">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-weight: 600">测试轮次列表</span>
          <el-radio-group v-model="statusFilter" size="small" @change="loadRuns">
            <el-radio-button label="">全部</el-radio-button>
            <el-radio-button label="completed">已完成</el-radio-button>
            <el-radio-button label="running">运行中</el-radio-button>
            <el-radio-button label="failed">失败</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <el-table :data="runs" stripe style="width: 100%" @row-click="goToDetail">
        <el-table-column prop="id" label="Run ID" width="100" />
        <el-table-column label="SVN 版本" width="120">
          <template #default="{ row }">{{ row.svn_revision?.revision || '-' }}</template>
        </el-table-column>
        <el-table-column prop="triggered_by" label="触发方式" width="100">
          <template #default="{ row }">
            <el-tag :type="row.triggered_by === 'auto' ? 'success' : 'warning'" size="small">
              {{ row.triggered_by === 'auto' ? '自动' : '手动' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="180">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :status="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'exception' : ''" />
          </template>
        </el-table-column>
        <el-table-column label="通过/失败" width="120">
          <template #default="{ row }">
            <span style="color: #67c23a">{{ row.completed_tasks - row.failed_tasks }}</span> /
            <span style="color: #f56c6c">{{ row.failed_tasks }}</span>
          </template>
        </el-table-column>
        <el-table-column label="开始时间" min-width="160">
          <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page"
        :page-size="20"
        :total="total"
        layout="total, prev, pager, next"
        style="margin-top: 16px"
        @current-change="loadRuns"
      />
    </el-card>

    <!-- 单轮详情 -->
    <div v-if="route.params.runId">
      <el-page-header @back="$router.push('/results')" style="margin-bottom: 16px">
        <template #content>
          <span>Run #{{ route.params.runId }} 详情</span>
        </template>
      </el-page-header>

      <el-card shadow="hover" style="margin-bottom: 16px">
        <el-descriptions :column="4" border>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(runDetail.status)">{{ statusText(runDetail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="SVN">{{ runDetail.svn_revision?.revision || '-' }}</el-descriptions-item>
          <el-descriptions-item label="触发">{{ runDetail.triggered_by === 'auto' ? '自动' : '手动' }}</el-descriptions-item>
          <el-descriptions-item label="进度">{{ runDetail.progress }}%</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 筛选 -->
      <el-card shadow="hover">
        <template #header>
          <div style="display: flex; gap: 12px; align-items: center; flex-wrap: wrap">
            <span style="font-weight: 600">测试结果</span>
            <el-select v-model="filterAlgo" placeholder="按算法筛选" clearable size="small" style="width: 180px" @change="loadResults">
              <el-option v-for="a in algorithms" :key="a.id" :label="a.display_name || a.name" :value="a.id" />
            </el-select>
            <el-select v-model="filterCore" placeholder="按核心筛选" clearable size="small" style="width: 180px" @change="loadResults">
              <el-option v-for="c in cores" :key="c.id" :label="c.display_name || c.name" :value="c.id" />
            </el-select>
            <el-select v-model="filterStatus" placeholder="按状态筛选" clearable size="small" style="width: 120px" @change="loadResults">
              <el-option label="通过" value="passed" />
              <el-option label="失败" value="failed" />
              <el-option label="错误" value="error" />
            </el-select>
          </div>
        </template>
        <el-table :data="results" stripe>
          <el-table-column label="算法" width="160">
            <template #default="{ row }">{{ row.algorithm?.display_name || row.algorithm?.name }}</template>
          </el-table-column>
          <el-table-column label="核心" width="140">
            <template #default="{ row }">{{ row.core?.display_name || row.core?.name }}</template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="通过" width="80" prop="pass_count" />
          <el-table-column label="失败" width="80" prop="fail_count" />
          <el-table-column label="总计" width="80" prop="total_count" />
          <el-table-column label="耗时(s)" width="100">
            <template #default="{ row }">{{ row.execution_time?.toFixed(2) || '-' }}</template>
          </el-table-column>
          <el-table-column label="错误信息" min-width="200">
            <template #default="{ row }">
              <el-text v-if="row.error_message" type="danger" truncated>{{ row.error_message }}</el-text>
              <span v-else style="color: #ccc">-</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'

const route = useRoute()
const router = useRouter()

const runs = ref([])
const page = ref(1)
const total = ref(0)
const statusFilter = ref('')

const runDetail = ref({})
const results = ref([])
const algorithms = ref([])
const cores = ref([])
const filterAlgo = ref(null)
const filterCore = ref(null)
const filterStatus = ref(null)

const statusType = (s) => ({ passed: 'success', completed: 'success', failed: 'danger', error: 'warning', running: '', pending: 'info' }[s] || 'info')
const statusText = (s) => ({ passed: '通过', completed: '已完成', failed: '失败', error: '错误', running: '运行中', pending: '等待中' }[s] || s)
const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN') : '-'

const loadRuns = async () => {
  const res = await api.get('/results/runs', { params: { page: page.value, per_page: 20, status: statusFilter.value || undefined } })
  runs.value = res.data.runs
  total.value = res.data.total
}

const goToDetail = (row) => {
  router.push(`/results/${row.id}`)
}

const loadResults = async () => {
  const runId = route.params.runId
  if (!runId) return
  const params = {}
  if (filterAlgo.value) params.algorithm_id = filterAlgo.value
  if (filterCore.value) params.core_id = filterCore.value
  if (filterStatus.value) params.status = filterStatus.value
  const res = await api.get(`/results/${runId}`, { params })
  runDetail.value = res.data.run
  results.value = res.data.results
}

const loadAlgorithmsAndCores = async () => {
  const [aRes, cRes] = await Promise.all([
    api.get('/config/algorithms'),
    api.get('/config/cores'),
  ])
  algorithms.value = aRes.data.algorithms
  cores.value = cRes.data.cores
}

onMounted(() => {
  if (route.params.runId) {
    loadResults()
    loadAlgorithmsAndCores()
  } else {
    loadRuns()
  }
})

watch(() => route.params.runId, (val) => {
  if (val) {
    loadResults()
    loadAlgorithmsAndCores()
  } else {
    loadRuns()
  }
})
</script>
