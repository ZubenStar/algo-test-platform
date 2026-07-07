<template>
  <div>
    <!-- 算法管理 -->
    <el-card shadow="hover" style="margin-bottom: 16px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-weight: 600">算法配置</span>
          <el-button type="primary" size="small" @click="showAlgoDialog(null)"><el-icon><Plus /></el-icon> 新增算法</el-button>
        </div>
      </template>
      <el-table :data="algorithms" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="标识" width="150" />
        <el-table-column prop="display_name" label="显示名称" width="200" />
        <el-table-column prop="script_path" label="脚本路径" min-width="300" show-overflow-tooltip />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button type="primary" size="small" text @click="showAlgoDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除？" @confirm="deleteAlgo(row.id)">
              <template #reference><el-button type="danger" size="small" text>删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 核配置 -->
    <el-card shadow="hover">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-weight: 600">核心配置</span>
          <el-button type="primary" size="small" @click="showCoreDialog(null)"><el-icon><Plus /></el-icon> 新增核心</el-button>
        </div>
      </template>
      <el-table :data="cores" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="标识" width="120" />
        <el-table-column prop="display_name" label="显示名称" width="180" />
        <el-table-column prop="arch" label="架构" width="100" />
        <el-table-column prop="sim_cmd_template" label="仿真命令模板" min-width="300" show-overflow-tooltip />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button type="primary" size="small" text @click="showCoreDialog(row)">编辑</el-button>
            <el-popconfirm title="确认删除？" @confirm="deleteCore(row.id)">
              <template #reference><el-button type="danger" size="small" text>删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 算法编辑对话框 -->
    <el-dialog v-model="algoDialogVisible" :title="editingAlgo ? '编辑算法' : '新增算法'" width="500px">
      <el-form :model="algoForm" label-width="100px">
        <el-form-item label="标识">
          <el-input v-model="algoForm.name" :disabled="!!editingAlgo" placeholder="如 Algorithm_A" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="algoForm.display_name" placeholder="如 算法A - 降噪" />
        </el-form-item>
        <el-form-item label="脚本路径">
          <el-input v-model="algoForm.script_path" placeholder="/path/to/sim_script.py" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="algoForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="启用" v-if="editingAlgo">
          <el-switch v-model="algoForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="algoDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveAlgo">保存</el-button>
      </template>
    </el-dialog>

    <!-- 核编辑对话框 -->
    <el-dialog v-model="coreDialogVisible" :title="editingCore ? '编辑核心' : '新增核心'" width="500px">
      <el-form :model="coreForm" label-width="120px">
        <el-form-item label="标识">
          <el-input v-model="coreForm.name" :disabled="!!editingCore" placeholder="如 ARM_M55" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="coreForm.display_name" placeholder="如 ARM Cortex-M55" />
        </el-form-item>
        <el-form-item label="架构">
          <el-input v-model="coreForm.arch" placeholder="arm / xtensa / x86" />
        </el-form-item>
        <el-form-item label="仿真命令模板">
          <el-input v-model="coreForm.sim_cmd_template" placeholder="python {script} --core m55" />
        </el-form-item>
        <el-form-item label="启用" v-if="editingCore">
          <el-switch v-model="coreForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="coreDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveCore">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const algorithms = ref([])
const cores = ref([])
const saving = ref(false)

// 算法
const algoDialogVisible = ref(false)
const editingAlgo = ref(null)
const algoForm = ref({ name: '', display_name: '', script_path: '', description: '', is_active: true })

const showAlgoDialog = (algo) => {
  editingAlgo.value = algo
  algoForm.value = algo ? { ...algo } : { name: '', display_name: '', script_path: '', description: '', is_active: true }
  algoDialogVisible.value = true
}

const saveAlgo = async () => {
  saving.value = true
  try {
    if (editingAlgo.value) {
      await api.put(`/config/algorithms/${editingAlgo.value.id}`, algoForm.value)
    } else {
      await api.post('/config/algorithms', algoForm.value)
    }
    ElMessage.success('保存成功')
    algoDialogVisible.value = false
    await loadAlgorithms()
  } catch { } finally { saving.value = false }
}

const deleteAlgo = async (id) => {
  await api.delete(`/config/algorithms/${id}`)
  ElMessage.success('已删除')
  await loadAlgorithms()
}

// 核
const coreDialogVisible = ref(false)
const editingCore = ref(null)
const coreForm = ref({ name: '', display_name: '', arch: '', sim_cmd_template: '', is_active: true })

const showCoreDialog = (core) => {
  editingCore.value = core
  coreForm.value = core ? { ...core } : { name: '', display_name: '', arch: '', sim_cmd_template: '', is_active: true }
  coreDialogVisible.value = true
}

const saveCore = async () => {
  saving.value = true
  try {
    if (editingCore.value) {
      await api.put(`/config/cores/${editingCore.value.id}`, coreForm.value)
    } else {
      await api.post('/config/cores', coreForm.value)
    }
    ElMessage.success('保存成功')
    coreDialogVisible.value = false
    await loadCores()
  } catch { } finally { saving.value = false }
}

const deleteCore = async (id) => {
  await api.delete(`/config/cores/${id}`)
  ElMessage.success('已删除')
  await loadCores()
}

const loadAlgorithms = async () => {
  const res = await api.get('/config/algorithms')
  algorithms.value = res.data.algorithms
}

const loadCores = async () => {
  const res = await api.get('/config/cores')
  cores.value = res.data.cores
}

onMounted(() => {
  loadAlgorithms()
  loadCores()
})
</script>
