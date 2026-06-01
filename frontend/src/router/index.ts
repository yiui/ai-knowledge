import { createRouter, createWebHistory } from 'vue-router'

import ChatView from '@/views/ChatView.vue'
import UploadView from '@/views/DocumentUpload.vue'
import LoginView from '@/views/LoginView.vue'
import RegisterView from '@/views/RegisterView.vue'
import { fetchMe } from '@/api/auth'
import {
  clearAuth,
  getToken,
  isLoggedIn,
  sessionValidated,
  setAuth,
} from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { guestOnly: true },
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView,
      meta: { guestOnly: true },
    },
    {
      path: '/',
      name: 'chat',
      component: ChatView,
      meta: { requiresAuth: true },
    },
    {
      path: '/upload',
      name: 'upload',
      component: UploadView,
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const token = getToken()

  if (to.meta.requiresAuth) {
    if (!token) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }

    if (!sessionValidated.value) {
      try {
        const user = await fetchMe()
        setAuth(token, user)
      } catch {
        clearAuth()
        return { name: 'login', query: { redirect: to.fullPath } }
      }
    }
    return true
  }

  if (to.meta.guestOnly && isLoggedIn.value) {
    return { name: 'chat' }
  }

  return true
})

export default router
