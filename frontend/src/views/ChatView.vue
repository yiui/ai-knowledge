<template>
    <div class="chat-page">
      <div class="chat-box">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="msg.role"
        >
          {{ msg.content }}
        </div>
      </div>
  
      <div class="input-box">
        <input
          v-model="question"
          placeholder="请输入问题..."
          :disabled="loading"
          @keyup.enter="send"
        />
        <button :disabled="loading" @click="send">
          {{ loading ? '生成中...' : '发送' }}
        </button>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref } from 'vue'
  import { chatStreamApi } from '../api/chat'
  
  const question = ref('')
  const messages = ref([])
  const loading = ref(false)
  
  const send = async () => {
    if (!question.value || loading.value) return
  
    const q = question.value
    messages.value.push({ role: 'user', content: q })
    question.value = ''

    messages.value.push({ role: 'assistant', content: '' })
    const assistantIndex = messages.value.length - 1

    loading.value = true
    try {
      await chatStreamApi(q, (chunk) => {
        messages.value[assistantIndex].content += chunk
      })
    } catch {
      messages.value[assistantIndex].content = '请求失败，请重试'
    } finally {
      loading.value = false
    }
  }
  </script>
  
  <style scoped>
  .chat-page {
    flex: 1;
    display: flex;
    flex-direction: column;
  }
  
  .chat-box {
    flex: 1;
    padding: 16px;
    overflow: auto;
  }
  
  .user {
    text-align: right;
    margin: 8px;
    color: #1677ff;
  }
  
  .assistant {
    text-align: left;
    margin: 8px;
    color: #333;
  }
  
  .input-box {
    display: flex;
    padding: 10px;
    border-top: 1px solid #eee;
  }
  
  input {
    flex: 1;
    padding: 8px;
  }
  </style>