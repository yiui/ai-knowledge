<template>
  <div class="app-container">
    <!-- 顶部导航 -->
    <header class="top-bar">
      <div class="title">AI Knowledge Base</div>
<div class="button-container">
  <button class="upload-btn" @click="goUpload">
        上传文档
      </button>
      <button class="chat-btn" @click="goChat">
        知识库问答
      </button>
</div>
  
    </header>

    <!-- 页面内容 -->
    <router-view />
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goUpload = () => {
  router.push('/upload')
}

const goChat = () => {
  router.push('/')
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
}

  .upload-btn {
    padding: 6px 12px;
    background: #1677ff;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    margin-right: 10px; /* 添加间距 */
  }

  .chat-btn {
    padding: 6px 12px;
    background: #1677ff;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    margin-right: 10px; /* 添加间距 */
  }
</style>