<template>
  <div>
    <!-- 选择测试轮次 -->
    <el-card shadow="hover" style="margin-bottom: 16px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-weight: 600">一致性报告</span>
          <el-select v-model="selectedRunId" placeholder="选择测试轮次" style="width: 240px" @change="loadReports">
            <el-option v-for="r in runs" :key="r.id" :label="`Run #${r.id} - ${r.svn_revision?.revision || '手动'} (${formatTime(r.finished_at)})`" :value="r.id" />
          </el-select>
        </div>
      </template>
    </el-card>

    <!-- 一致性总览 -->
    <el-row :gutter="16" style="margin-bottom: 16px" v-if="reports.length > 0">
      <el-col :span="8">
        <el-card shadow="hover">
          <el-statistic title="算法总数" :value="reports.length" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <el-statistic title="一致性通过" :value="consistentCount" value-style="color: #67c23a" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <el-statistic title="不一致" :value="inconsistentCount" value-style="color: #f56c6c" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 报告列表 -->
    <el-card shadow="hover" v-if="reports.length > 0">
      <el-collapse v-model="activeNames">
        <el-collapse-item v-for="report in reports" :key="report.id" :name="report.id">
          <template #title>
            <div style="display: flex; align-items: center; gap: 12px; width: 100%">
              <el-icon :size="20" :color="report.is_consistent ? '#67c23a' : '#f56c6c'">
                <CircleCheck v-if="report.is_consistent" />
                <CircleClose v-else />
              </el-icon>
              <span style="font-weight: 600">{{ report.algorithm?.display_name || report.algorithm?.name }}</span>
              <el-tag :type="report.is_consistent ? 'success' : 'danger'" size="small" style="margin-left: auto; margin-right: 20px">
                {{ report.is_consistent ? '一致' : '不一致' }}
              </el-tag>
            </div>
          </template>
          <div style="padding: 12px">
            <el-descriptions :column="3" border size="small" style="margin-bottom: 16px">
              <el-descriptions-item label="参考核">{{ report.reference_core?.display_name || '-' }}</el-descriptions-item>
              <el-descriptions-item label="最大差异">
                <span :style="{ color: report.is_consistent ? '#67c23a' : '#f56c6c', fontWeight: 600 }">
                  {{ report.max_diff?.toExponential(4) || '-' }}
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="阈值">{{ consistencyThreshold.toExponential(1) }}</el-descriptions-item>
            </el-descriptions>

            <!-- 差异详情表格 -->
            <el-table :data="report.details?.comparisons || []" border size="small" v-if="report.details?.comparisons">
              <el-table-column prop="core" label="对比核" width="140" />
              <el-table-column label="最大绝对差" width="160">
                <template #default="{ row }">
                  <span :style="{ color: row.is_consistent ? '#67c23a' : '#f56c6c' }">
                    {{ row.max_abs_diff?.toExponential(4) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="平均绝对差" width="160">
                <template #default="{ row }">{{ row.mean_abs_diff?.toExponential(4) }}</template>
              </el-table-column>
              <el-table-column label="参考核通过/失败" width="140">
                <template #default="{ row }">
                  <span style="color: #67c23a">{{ row.ref_pass_count }}</span> / <span style="color: #f56c6c">{{ row.ref_fail_count }}</span>
                </template>
              </el-table-column>
              <el-table-column label="对比核通过/失败" width="140">
                <template #default="{ row }">
                  <span style="color: #67c23a">{{ row.cur_pass_count }}</span> / <span style="color: #f56c6c">{{ row.cur_fail_count }}</span>
                </template>
              </el-table-column>
              <el-table-column label="一致性" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.is_consistent ? 'success' : 'danger'" size="small">
                    {{ row.is_consistent ? '一致' : '不一致' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>

            <div v-if="report.details?.error" style="color: #909399; padding: 12px 0">
              {{ report.details.error }}
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <el-empty v-else-if="selectedRunId" description="该轮次暂无一致性报告" />
    <el-empty v-else description="请先选择一个测试轮次" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'

const route = useRoute()

const runs = ref([])
const selectedRunId = ref(null)
const reports = ref([])
const activeNames = ref([])
const consistencyThreshold = ref(1e-6)

const consistentCount = computed(() => reports.value.filter(r => r.is_consistent).length)
const inconsistentCount = computed(() => reports.value.filter(r => r.is_consistent === false).length)

const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN') : '-'

const loadRuns = async () => {
  const res = await api.get('/results/runs', { params: { per_page: 20, status: 'completed' } })
  runs.value = res.data.runs
  if (route.params.runId) {
    selectedRunId.value = parseInt(route.params.runId)
    loadReports()
  } else if (runs.value.length > 0) {
    selectedRunId.value = runs.value[0].id
    loadReports()
  }
}

const loadReports = async () => {
  if (!selectedRunId.value) return
  const res = await api.get(`/consistency/${selectedRunId.value}`)
  reports.value = res.data.reports
  // 默认展开第一个不一致的
  const firstInconsistent = reports.value.find(r => !r.is_consistent)
  activeNames.value = firstInconsistent ? [firstInconsistent.id] : []
}

onMounted(loadRuns)
</script>
