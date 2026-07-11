<template>
  <!-- 登录/注册页：纯净无侧栏 -->
  <div v-if="isAuthPage" class="app-plain">
    <router-view />
  </div>

  <!-- 主界面：侧栏 + 内容 -->
  <div v-else class="app-shell">
    <nav class="sidebar">
      <router-link to="/" class="sidebar-brand" title="AI Knowledge">
        <span class="brand-icon">◆</span>
      </router-link>

      <div class="sidebar-nav">
        <router-link
          to="/"
          :class="['sidebar-link', { active: $route.name === 'chat' }]"
          title="对话"
        >
          <span class="sidebar-link__icon">💬</span>
          <span class="sidebar-link__label">对话</span>
        </router-link>
        <router-link
          to="/knowledge"
          :class="['sidebar-link', { active: $route.name === 'knowledge' }]"
          title="知识库"
        >
          <span class="sidebar-link__icon">📚</span>
          <span class="sidebar-link__label">知识库</span>
        </router-link>
      </div>

    </nav>

    <div class="app-body">
      <header class="topbar">
        <span class="topbar-breadcrumb">
          {{ $route.name === 'knowledge' ? '知识库 / 文档管理' : '对话 / AI 问答' }}
        </span>
        <el-dropdown trigger="hover" @command="handleUserCommand">
          <span class="user-trigger">{{ user?.username }} ▾</span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </header>
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { clearAuth } from '@/stores/auth'
import { user } from '@/stores/auth'

const router = useRouter()
const route = useRoute()

const isAuthPage = computed(() =>
  route.name === 'login' || route.name === 'register',
)

const handleUserCommand = (cmd) => {
  if (cmd === 'logout') {
    clearAuth()
    router.replace('/login')
  }
}
</script>

<style scoped>
/* ---- 纯净模式（登录页） ---- */

.app-plain {
  height: 100vh;
}

/* ---- 主界面 ---- */

.app-shell {
  height: 100vh;
  display: flex;
  overflow: hidden;
  background: #f8f9fb;
}

/* ---- 侧边导航 ---- */

.sidebar {
  width: 72px;
  display: flex;
  flex-direction: column;
  align-items: center;
  background: #fff;
  border-right: 1px solid #edf0f4;
  flex-shrink: 0;
  padding: 16px 0 12px;
}

.sidebar-brand {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: linear-gradient(135deg, #1677ff, #4096ff);
  margin-bottom: 24px;
  text-decoration: none;
}

.brand-icon {
  color: #fff;
  font-size: 14px;
  line-height: 1;
}

.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.sidebar-link {
  width: 52px;
  height: 52px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: #8c8f96;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s ease;
  position: relative;
}

.sidebar-link:hover {
  background: #f0f2f5;
  color: #4e5158;
}

.sidebar-link.active {
  background: #eef4ff;
  color: #1677ff;
}

.sidebar-link.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 3px;
  background: #1677ff;
  border-radius: 0 2px 2px 0;
}

.sidebar-link__icon {
  font-size: 18px;
  line-height: 1;
}

.sidebar-link__label {
  font-size: 10px;
  font-weight: 500;
  line-height: 1;
}

/* ---- 内容区 ---- */

.app-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.topbar {
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid #edf0f4;
  flex-shrink: 0;
}

.topbar-breadcrumb {
  font-size: 12px;
  color: #a0a4ac;
  font-weight: 500;
  letter-spacing: 0.3px;
}

.user-trigger {
  font-size: 14px;
  color: #3d4048;
  cursor: pointer;
  padding: 5px 12px;
  border-radius: 6px;
  transition: background 0.15s;
  user-select: none;
  font-weight: 500;
}

.user-trigger:hover {
  background: #f0f2f5;
  color: #1677ff;
}
</style>
