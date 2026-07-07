<template>
  <div id="app">
    <!-- 登录页面不需要侧边栏布局 -->
    <router-view v-if="route.path === '/login'" />

    <el-container v-else style="height: 100vh">
      <!-- 侧边栏 -->
      <el-aside width="220px" style="background-color: #001529">
        <div class="logo">
          <el-icon><Monitor /></el-icon>
          <span>算法测试平台</span>
        </div>
        <el-menu
          :default-active="route.path"
          router
          background-color="#001529"
          text-color="#ffffffa6"
          active-text-color="#1890ff"
        >
          <el-menu-item index="/">
            <el-icon><DataBoard /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>
          <el-menu-item index="/results">
            <el-icon><Document /></el-icon>
            <span>测试结果</span>
          </el-menu-item>
          <el-menu-item index="/consistency">
            <el-icon><ScaleToOriginal /></el-icon>
            <span>一致性报告</span>
          </el-menu-item>
          <el-menu-item index="/svn">
            <el-icon><Connection /></el-icon>
            <span>SVN 监控</span>
          </el-menu-item>
          <el-menu-item index="/tasks">
            <el-icon><Loading /></el-icon>
            <span>任务管理</span>
          </el-menu-item>
          <!-- 管理员菜单 -->
          <template v-if="authStore.isAdmin">
            <el-divider style="border-color: #ffffff30; margin: 10px 16px" />
            <el-menu-item index="/users">
              <el-icon><User /></el-icon>
              <span>用户管理</span>
            </el-menu-item>
            <el-menu-item index="/config">
              <el-icon><Setting /></el-icon>
              <span>配置管理</span>
            </el-menu-item>
          </template>
        </el-menu>
      </el-aside>

      <el-container>
        <!-- 顶部栏 -->
        <el-header style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #e8e8e8">
          <span style="font-size: 18px; font-weight: 500">{{ currentTitle }}</span>
          <div style="display: flex; align-items: center; gap: 16px">
            <span style="color: #666">{{ authStore.user?.username }}</span>
            <el-tag :type="authStore.isAdmin ? 'danger' : 'info'" size="small">
              {{ authStore.isAdmin ? '管理员' : '普通用户' }}
            </el-tag>
            <el-button text @click="handleLogout">注销</el-button>
          </div>
        </el-header>

        <!-- 主内容 -->
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const titleMap = {
  '/': '仪表盘',
  '/results': '测试结果',
  '/consistency': '一致性报告',
  '/svn': 'SVN 监控',
  '/tasks': '任务管理',
  '/users': '用户管理',
  '/config': '配置管理',
}

const currentTitle = computed(() => titleMap[route.path] || '算法单元测试平台')

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid #ffffff1a;
}
.el-menu {
  border-right: none !important;
}
</style>
