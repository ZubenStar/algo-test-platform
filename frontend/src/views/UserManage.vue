<template>
  <div>
    <el-card shadow="hover">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-weight: 600">用户管理</span>
          <el-button type="primary" @click="showAdd = true"><el-icon><Plus /></el-icon> 新增用户</el-button>
        </div>
      </template>
      <el-table :data="users" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="首次改密" width="100">
          <template #default="{ row }">
            <el-tag :type="row.force_change_password ? 'warning' : 'info'" size="small">
              {{ row.force_change_password ? '待改' : '已完成' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后登录" min-width="180">
          <template #default="{ row }">{{ formatTime(row.last_login) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="180">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" text @click="editUser(row)">编辑</el-button>
            <el-button type="warning" size="small" text @click="resetPwd(row)">重置密码</el-button>
            <el-popconfirm title="确认删除此用户？" @confirm="deleteUser(row.id)">
              <template #reference>
                <el-button type="danger" size="small" text :disabled="row.id === currentUserId">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑用户 -->
    <el-dialog v-model="showAdd" :title="editingUser ? '编辑用户' : '新增用户'" width="420px" @close="resetForm">
      <el-form :model="userForm" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="userForm.username" :disabled="!!editingUser" />
        </el-form-item>
        <el-form-item label="密码" v-if="!editingUser">
          <el-input v-model="userForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="userForm.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" v-if="editingUser">
          <el-switch v-model="userForm.is_active" active-text="正常" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAdd = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码 -->
    <el-dialog v-model="showResetPwd" title="重置密码" width="400px">
      <el-form label-width="80px">
        <el-form-item label="用户">{{ resetTarget?.username }}</el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="newPassword" type="password" show-password placeholder="至少6位" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showResetPwd = false">取消</el-button>
        <el-button type="primary" :loading="resetting" @click="doResetPwd">确认重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const authStore = useAuthStore()
const currentUserId = computed(() => authStore.user?.id)

const users = ref([])
const showAdd = ref(false)
const editingUser = ref(null)
const saving = ref(false)
const showResetPwd = ref(false)
const resetTarget = ref(null)
const newPassword = ref('')
const resetting = ref(false)

const userForm = ref({ username: '', password: '', role: 'user', is_active: true })

const formatTime = (t) => t ? new Date(t).toLocaleString('zh-CN') : '-'

const loadUsers = async () => {
  const res = await api.get('/users')
  users.value = res.data.users
}

const editUser = (user) => {
  editingUser.value = user
  userForm.value = { username: user.username, role: user.role, is_active: user.is_active }
  showAdd.value = true
}

const resetForm = () => {
  editingUser.value = null
  userForm.value = { username: '', password: '', role: 'user', is_active: true }
}

const saveUser = async () => {
  saving.value = true
  try {
    if (editingUser.value) {
      await api.put(`/users/${editingUser.value.id}`, userForm.value)
      ElMessage.success('更新成功')
    } else {
      await api.post('/users', userForm.value)
      ElMessage.success('创建成功')
    }
    showAdd.value = false
    resetForm()
    await loadUsers()
  } catch {
    // handled
  } finally {
    saving.value = false
  }
}

const deleteUser = async (id) => {
  await api.delete(`/users/${id}`)
  ElMessage.success('已删除')
  await loadUsers()
}

const resetPwd = (user) => {
  resetTarget.value = user
  newPassword.value = ''
  showResetPwd.value = true
}

const doResetPwd = async () => {
  if (!newPassword.value || newPassword.value.length < 6) {
    ElMessage.warning('密码至少6位')
    return
  }
  resetting.value = true
  try {
    await api.put(`/users/${resetTarget.value.id}/reset-password`, { new_password: newPassword.value })
    ElMessage.success('密码已重置')
    showResetPwd.value = false
    await loadUsers()
  } catch {
    // handled
  } finally {
    resetting.value = false
  }
}

onMounted(loadUsers)
</script>
