<template>
  <div class="app-container">
    <header v-if="isLoggedIn" class="top-bar">
      <div class="title">AI Knowledge Base</div>
      <div class="nav-right">
        <span class="username">{{ user?.username }}</span>
        <button class="nav-btn" @click="goUpload">上传文档</button>
        <button class="nav-btn" @click="goChat">知识库问答</button>
        <button class="logout-btn" @click="handleLogout">退出</button>
      </div>
    </header>

    <router-view />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { clearAuth, getUser, isLoggedIn } from '@/stores/auth'

const router = useRouter()
const user = computed(() => getUser())

const goUpload = () => {
  router.push('/upload')
}

const goChat = () => {
  router.push('/')
}

const handleLogout = () => {
  clearAuth()
  router.replace('/login')
}
</script>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.top-bar {
  height: 56px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 16px;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.username {
  color: #666;
  font-size: 14px;
  margin-right: 4px;
}

.nav-btn {
  padding: 6px 12px;
  background: #1677ff;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.logout-btn {
  padding: 6px 12px;
  background: transparent;
  color: #666;
  border: 1px solid #ddd;
  border-radius: 6px;
  cursor: pointer;
}

.logout-btn:hover {
  color: #1677ff;
  border-color: #1677ff;
}
</style>
