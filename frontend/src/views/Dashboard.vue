<template>
  <div class="dashboard">
    <!-- 顶部统计卡片 -->
    <el-row :gutter="16" style="margin-bottom: 20px">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #e6f7ff"><el-icon :size="28" color="#1890ff"><Cpu /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ dashboard.algo_count || 0 }}</div>
            <div class="stat-label">活跃算法</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #f6ffed"><el-icon :size="28" color="#52c41a"><Monitor /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ dashboard.core_count || 0 }}</div>
            <div class="stat-label">活跃核心</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #fff7e6"><el-icon :size="28" color="#faad14"><TrendCharts /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ dashboard.pass_rate != null ? dashboard.pass_rate + '%' : '-' }}</div>
            <div class="stat-label">最近通过率</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #fff1f0"><el-icon :size="28" color="#f5222d"><Connection /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ dashboard.latest_svn?.revision || '-' }}</div>
            <div class="stat-label">最新 SVN 版本</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 矩阵热力图 -->
    <el-row :gutter="16" style="margin-bottom: 20px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span style="font-weight: 600">算法 × 核心 矩阵（最近一次测试）</span>
              <el-select v-model="selectedRunId" placeholder="选择测试轮次" style="width: 200px" @change="loadMatrix">
                <el-option v-for="r in recentRuns" :key="r.id" :label="`Run #${r.id} (${r.status})`" :value="r.id" />
              </el-select>
            </div>
          </template>
          <div v-if="matrixData.algorithms.length > 0">
            <table class="matrix-table">
              <thead>
                <tr>
                  <th>算法 \ 核心</th>
                  <th v-for="core in matrixData.cores" :key="core">{{ core }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="algo in matrixData.algorithms" :key="algo">
                  <td class="algo-name">{{ algo }}</td>
                  <td v-for="core in matrixData.cores" :key="core">
                    <el-tag
                      :type="getStatusType(matrixData.matrix[algo]?.[core]?.status)"
                      size="small"
                      effect="dark"
                    >
                      {{ matrixData.matrix[algo]?.[core]?.status || '-' }}
                    </el-tag>
                    <div v-if="matrixData.matrix[algo]?.[core]" style="font-size: 11px; color: #999; margin-top: 2px">
                      {{ matrixData.matrix[algo][core].pass_count }}/{{ matrixData.matrix[algo][core].total_count }}
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <el-empty v-else description="暂无测试数据" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 趋势图 -->
    <el-row :gutter="16">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <span style="font-weight: 600">通过率趋势</span>
          </template>
          <div ref="trendChartRef" style="height: 350px"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import api from '../api'

const dashboard = ref({})
const selectedRunId = ref(null)
const recentRuns = ref([])
const matrixData = reactive({ matrix: {}, algorithms: [], cores: [] })
const trendChartRef = ref(null)

const getStatusType = (status) => {
  const map = { passed: 'success', failed: 'danger', error: 'warning', running: '', pending: 'info' }
  return map[status] || 'info'
}

const loadDashboard = async () => {
  const res = await api.get('/dashboard')
  Object.assign(dashboard.value, res.data)
  if (res.data.latest_run) {
    selectedRunId.value = res.data.latest_run.id
    loadMatrix()
  }
}

const loadRecentRuns = async () => {
  const res = await api.get('/results/runs', { params: { per_page: 10 } })
  recentRuns.value = res.data.runs
}

const loadMatrix = async () => {
  if (!selectedRunId.value) return
  const res = await api.get(`/dashboard/matrix/${selectedRunId.value}`)
  Object.assign(matrixData, res.data)
}

const loadTrend = async () => {
  const res = await api.get('/dashboard/trend', { params: { limit: 15 } })
  await nextTick()
  if (!trendChartRef.value) return
  const chart = echarts.init(trendChartRef.value)
  const data = res.data.trend
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: data.map(d => `Run #${d.run_id}`),
      axisLabel: { rotate: 30 },
    },
    yAxis: {
      type: 'value',
      name: '通过率 (%)',
      min: 0,
      max: 100,
    },
    series: [{
      name: '通过率',
      type: 'line',
      data: data.map(d => d.pass_rate),
      smooth: true,
      areaStyle: { opacity: 0.3 },
      itemStyle: { color: '#409EFF' },
    }],
    grid: { left: 60, right: 30, bottom: 60, top: 30 },
  })
  window.addEventListener('resize', () => chart.resize())
}

onMounted(() => {
  loadDashboard()
  loadRecentRuns()
  loadTrend()
})
</script>

<style scoped>
.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}
.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #303133;
}
.stat-label {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}
.matrix-table {
  width: 100%;
  border-collapse: collapse;
  text-align: center;
}
.matrix-table th, .matrix-table td {
  border: 1px solid #ebeef5;
  padding: 10px 12px;
}
.matrix-table th {
  background: #fafafa;
  font-weight: 600;
  color: #606266;
}
.algo-name {
  font-weight: 600;
  text-align: left;
  color: #303133;
}
</style>
