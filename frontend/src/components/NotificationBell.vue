<template>
  <el-popover placement="bottom-end" width="320" trigger="click" @show="loadNotifications">
    <template #reference>
      <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99">
        <el-button text circle>
          <el-icon><Bell /></el-icon>
        </el-button>
      </el-badge>
    </template>
    <div class="notification-list">
      <PageState :loading="loading" :empty="notifications.length === 0" description="暂无通知">
        <div
          v-for="item in notifications"
          :key="item.id"
          class="notification-item"
          :class="{ unread: !item.is_read }"
          @click="markRead(item)"
        >
          <div class="message">{{ item.message }}</div>
          <div class="time">{{ formatTime(item.created_at) }}</div>
        </div>
      </PageState>
    </div>
  </el-popover>
</template>

<script setup>
import { ref } from 'vue'
import { Bell } from '@element-plus/icons-vue'
import api from '../api'
import PageState from './PageState.vue'

const notifications = ref([])
const unreadCount = ref(0)
const loading = ref(false)

const formatTime = (value) => value ? new Date(value).toLocaleString('zh-CN') : '-'

const loadNotifications = async () => {
  loading.value = true
  try {
    const res = await api.get('/notifications')
    notifications.value = res.data.notifications
    unreadCount.value = res.data.unread_count
  } finally {
    loading.value = false
  }
}

const markRead = async (item) => {
  if (item.is_read) return
  await api.post(`/notifications/${item.id}/read`)
  item.is_read = true
  unreadCount.value = Math.max(0, unreadCount.value - 1)
}

const incrementUnread = () => {
  unreadCount.value += 1
}

defineExpose({ loadNotifications, incrementUnread })
</script>

<style scoped>
.notification-list {
  min-height: 120px;
}
.notification-item {
  padding: 10px 4px;
  border-bottom: 1px solid #ebeef5;
  cursor: pointer;
}
.notification-item:last-child {
  border-bottom: 0;
}
.notification-item.unread .message {
  font-weight: 600;
  color: #303133;
}
.message {
  font-size: 13px;
  color: #606266;
}
.time {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}
</style>
