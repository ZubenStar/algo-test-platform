<template>
  <div class="login-container">
    <el-card class="login-card" shadow="hover">
      <template #header>
        <div class="login-header">
          <el-icon :size="40" color="#409EFF"><Monitor /></el-icon>
          <h2>算法单元测试平台</h2>
        </div>
      </template>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="0"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            :prefix-icon="User"
            size="large"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            :prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            style="width: 100%"
            :loading="loading"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 强制修改密码对话框 -->
    <el-dialog v-model="showChangePwd" title="修改密码" width="400px" :close-on-click-modal="false" :close-on-press-escape="false" :show-close="false">
      <el-alert type="warning" :closable="false" style="margin-bottom: 16px">
        首次登录，请修改默认密码
      </el-alert>
      <el-form :model="pwdForm" label-width="80px">
        <el-form-item label="旧密码">
          <el-input v-model="pwdForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.new_password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button type="primary" :loading="pwdLoading" @click="handleChangePwd">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref()
const loading = ref(false)
const showChangePwd = ref(false)
const pwdLoading = ref(false)

const form = reactive({ username: '', password: '' })
const pwdForm = reactive({ old_password: '', new_password: '' })

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const handleLogin = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      const data = await authStore.login(form.username, form.password)
      ElMessage.success('登录成功')
      if (data.force_change_password) {
        pwdForm.old_password = form.password
        showChangePwd.value = true
      } else {
        router.push('/')
      }
    } catch {
      // 错误已由 interceptor 处理
    } finally {
      loading.value = false
    }
  })
}

const handleChangePwd = async () => {
  if (!pwdForm.new_password || pwdForm.new_password.length < 6) {
    ElMessage.warning('新密码至少6位')
    return
  }
  pwdLoading.value = true
  try {
    await authStore.changePassword(pwdForm.old_password, pwdForm.new_password)
    ElMessage.success('密码修改成功')
    showChangePwd.value = false
    router.push('/')
  } catch {
    // handled
  } finally {
    pwdLoading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  width: 420px;
}
.login-header {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.login-header h2 {
  margin: 0;
  color: #303133;
}
</style>
