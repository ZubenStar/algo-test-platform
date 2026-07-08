import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
  },
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
  },
  {
    path: '/results',
    name: 'TestResults',
    component: () => import('../views/TestResults.vue'),
  },
  {
    path: '/results/:runId',
    name: 'TestResultsDetail',
    component: () => import('../views/TestResults.vue'),
  },
  {
    path: '/consistency',
    name: 'ConsistencyReport',
    component: () => import('../views/ConsistencyReport.vue'),
  },
  {
    path: '/consistency/:runId',
    name: 'ConsistencyReportDetail',
    component: () => import('../views/ConsistencyReport.vue'),
  },
  {
    path: '/svn',
    name: 'SvnMonitor',
    component: () => import('../views/SvnMonitor.vue'),
  },
  {
    path: '/tasks',
    name: 'TaskManager',
    component: () => import('../views/TaskManager.vue'),
  },
  {
    path: '/users',
    name: 'UserManage',
    component: () => import('../views/UserManage.vue'),
  },
  {
    path: '/config',
    name: 'ConfigManage',
    component: () => import('../views/ConfigManage.vue'),
  },
  {
    path: '/audit',
    name: 'AuditLogs',
    component: () => import('../views/AuditLogs.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 获取当前用户信息（如果还没有）
  if (!authStore.user) {
    try {
      await authStore.fetchUser()
    } catch {
      // 未登录
    }
  }

  if (to.path !== '/login' && !authStore.user) {
    next('/login')
  } else if (to.path === '/login' && authStore.user) {
    next('/')
  } else {
    // 管理员页面权限检查
    const adminPages = ['/users', '/config', '/audit']
    if (adminPages.includes(to.path) && !authStore.isAdmin) {
      next('/')
    } else {
      next()
    }
  }
})

export default router
