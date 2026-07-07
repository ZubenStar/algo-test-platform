import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)

  const isAdmin = computed(() => user.value?.role === 'admin')

  async function fetchUser() {
    try {
      const res = await api.get('/auth/me')
      user.value = res.data.user
    } catch {
      user.value = null
    }
  }

  async function login(username, password) {
    const res = await api.post('/auth/login', { username, password })
    user.value = res.data.user
    return res.data
  }

  async function logout() {
    try {
      await api.post('/auth/logout')
    } catch {
      // ignore
    }
    user.value = null
  }

  async function changePassword(oldPassword, newPassword) {
    const res = await api.put('/auth/password', {
      old_password: oldPassword,
      new_password: newPassword,
    })
    return res.data
  }

  return { user, isAdmin, fetchUser, login, logout, changePassword }
})
