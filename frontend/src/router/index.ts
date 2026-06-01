import { createRouter, createWebHistory } from 'vue-router'

import ChatView from '@/views/ChatView.vue'
import UploadView from '@/views/DocumentUpload.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: ChatView,
    },
    {
      path: '/upload',
      component: UploadView,
    },
  ],
})

export default router