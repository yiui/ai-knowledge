<template>
  <div class="chat-page">
    <div class="chat-toolbar">
      <span class="toolbar-label">知识库：</span>
      <el-select
        v-model="selectedKbId"
        clearable
        placeholder="不使用知识库（直接对话）"
        style="width: 280px"
      >
        <el-option
          v-for="kb in kbs"
          :key="kb.id"
          :label="kb.name"
          :value="kb.id"
        />
      </el-select>
      <span v-if="!selectedKbId" class="mode-hint">当前为直接对话模式</span>
    </div>

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
import { onMounted, ref } from 'vue'
import { chatStreamApi } from '../api/chat'
import { listKnowledgeBases } from '../api/knowledgeBase'

const question = ref('')
const messages = ref([])
const loading = ref(false)
const kbs = ref([])
const selectedKbId = ref(null)

onMounted(async () => {
  kbs.value = await listKnowledgeBases()
})

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
    }, selectedKbId.value)
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

.chat-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
  background: #fafafa;
}

.toolbar-label {
  color: #666;
  font-size: 14px;
}

.mode-hint {
  color: #999;
  font-size: 13px;
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
