<template>
  <div class="chat-layout">
  <aside class="conv-sidebar">
      <div class="sidebar-header">
        <h2>对话</h2>
        <el-button type="primary" size="small" @click="handleNewConversation">
          新对话
        </el-button>
      </div>

      <div v-if="conversations.length === 0" class="empty-tip">
        暂无对话，点击「新对话」开始
      </div>

      <ul v-else class="conv-list">
        <li
          v-for="conv in conversations"
          :key="conv.id"
          :class="{ active: currentId === conv.id }"
          @click="selectConversation(conv.id)"
        >
          <div class="conv-title">{{ conv.title }}</div>
          <div class="conv-meta">
            {{ conv.message_count }}/{{ conv.max_messages }} 条
          </div>
          <el-button
            type="danger"
            link
            size="small"
            class="del-btn"
            @click.stop="handleDeleteConversation(conv.id)"
          >
            删除
          </el-button>
        </li>
      </ul>
    </aside>

    <main class="chat-main">
      <template v-if="currentId">
        <div class="chat-toolbar">
          <span class="toolbar-label">知识库：</span>
          <el-select
            v-model="selectedKbId"
            clearable
            placeholder="不使用知识库（直接对话）"
            style="width: 260px"
            @change="onKbChange"
          >
            <el-option
              v-for="kb in kbs"
              :key="kb.id"
              :label="kb.name"
              :value="kb.id"
            />
          </el-select>
          <span v-if="llmModel" class="model-tag">
            {{ llmProvider }} / {{ llmModel }}
          </span>
          <span class="msg-count">
            {{ messageCount }}/{{ maxMessages }} 条消息
          </span>
        </div>

        <el-alert
          v-if="shouldStartNew"
          type="warning"
          :closable="false"
          show-icon
          class="limit-alert"
          title="当前会话消息已达上限，建议点击左侧「新对话」开启新会话"
        />

        <div ref="chatBoxRef" class="chat-box">
          <div
            v-for="msg in messages"
            :key="msg.id ?? msg.localKey"
            :class="['msg-row', msg.role]"
          >
            <div class="msg-wrapper">
              <div v-if="msg.sources && msg.sources.length > 0" class="sources-bar">
                <span class="sources-label">📄 来源：</span>
                <span
                  v-for="(src, i) in msg.sources"
                  :key="i"
                  class="source-tag"
                >
                  {{ src.filename }}{{ src.chunk_total > 0 ? ` (片段 ${src.chunk_index + 1}/${src.chunk_total})` : '' }}
                </span>
              </div>
              <div class="bubble">{{ msg.content }}</div>
            </div>
          </div>
        </div>

        <div class="input-box">
          <input
            v-model="question"
            placeholder="请输入问题..."
            :disabled="loading || shouldStartNew"
            @keyup.enter="send"
          />
          <button :disabled="loading || shouldStartNew" @click="send">
            {{ loading ? '生成中...' : '发送' }}
          </button>
        </div>
      </template>

      <div v-else class="placeholder">
        请选择或创建一个对话
      </div>
    </main>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { getAppConfig } from '../api/config'
import { listKnowledgeBases } from '../api/knowledgeBase'
import {
  chatStreamInConversation,
  createConversation,
  deleteConversation,
  getChatLimits,
  getConversation,
  listConversations,
  updateConversation,
} from '../api/conversation'

const conversations = ref([])
const currentId = ref(null)
const messages = ref([])
const question = ref('')
const loading = ref(false)
const kbs = ref([])
const selectedKbId = ref(null)
const messageCount = ref(0)
const maxMessages = ref(50)
const shouldStartNew = ref(false)
const chatBoxRef = ref(null)
const llmProvider = ref('')
const llmModel = ref('')

let localKeySeq = 0

const scrollToBottom = async () => {
  await nextTick()
  if (chatBoxRef.value) {
    chatBoxRef.value.scrollTop = chatBoxRef.value.scrollHeight
  }
}

const loadConversationList = async () => {
  conversations.value = await listConversations()
}

const applyConversationMeta = (detail) => {
  messageCount.value = detail.message_count
  maxMessages.value = detail.max_messages
  shouldStartNew.value = detail.should_start_new
  selectedKbId.value = detail.knowledge_base_id
  messages.value = detail.messages.map((m) => ({ ...m }))
}

const selectConversation = async (id) => {
  currentId.value = id
  loading.value = false
  const detail = await getConversation(id)
  applyConversationMeta(detail)
  await scrollToBottom()
}

const handleNewConversation = async () => {
  const conv = await createConversation({
    knowledge_base_id: selectedKbId.value ?? null,
  })
  await loadConversationList()
  await selectConversation(conv.id)
}

const handleDeleteConversation = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除该对话？删除后无法恢复。', '确认删除', {
      type: 'warning',
    })
    await deleteConversation(id)
    if (currentId.value === id) {
      currentId.value = null
      messages.value = []
    }
    await loadConversationList()
  } catch {
    // cancelled
  }
}

const onKbChange = async (kbId) => {
  if (!currentId.value) return
  await updateConversation(currentId.value, {
    knowledge_base_id: kbId ?? null,
  })
  await loadConversationList()
}

const send = async () => {
  if (!question.value.trim() || loading.value || !currentId.value) return
  if (shouldStartNew.value) {
    ElMessage.warning('请先开启新对话')
    return
  }

  const q = question.value.trim()
  question.value = ''

  const userLocalKey = `local-${++localKeySeq}`
  messages.value.push({ role: 'user', content: q, localKey: userLocalKey })
  messageCount.value += 1

  const assistantLocalKey = `local-${++localKeySeq}`
  messages.value.push({ role: 'assistant', content: '', localKey: assistantLocalKey })
  const assistantIndex = messages.value.length - 1
  await scrollToBottom()

  loading.value = true
  try {
    await chatStreamInConversation(
      currentId.value,
      q,
      (chunk) => {
        messages.value[assistantIndex].content += chunk
      },
      (sources) => {
        messages.value[assistantIndex].sources = sources
      },
      (meta) => {
        messageCount.value = meta.message_count
        maxMessages.value = meta.max_messages
        shouldStartNew.value = meta.should_start_new
        if (meta.should_start_new) {
          ElMessage.warning(
            `当前会话已达 ${meta.max_messages} 条消息上限，请开启新对话`,
          )
        }
      },
    )
    await loadConversationList()
    const detail = await getConversation(currentId.value)
    applyConversationMeta(detail)
  } catch (e) {
    messages.value[assistantIndex].content =
      e instanceof Error ? e.message : '请求失败，请重试'
    messageCount.value = Math.max(0, messageCount.value - 1)
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

onMounted(async () => {
  try {
    const cfg = await getAppConfig()
    if (cfg.llm) {
      llmProvider.value = cfg.llm.provider
      llmModel.value = cfg.llm.model
    }
  } catch { /* config 加载失败不影响核心功能 */ }

  const limits = await getChatLimits()
  maxMessages.value = limits.max_messages_per_conversation
  kbs.value = await listKnowledgeBases()
  await loadConversationList()
  if (conversations.value.length > 0) {
    await selectConversation(conversations.value[0].id)
  } else {
    await handleNewConversation()
  }
})
</script>

<style scoped>
.chat-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.conv-sidebar {
  width: 280px;
  border-right: 1px solid #eee;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #eee;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 16px;
}

.empty-tip {
  padding: 16px;
  color: #999;
  font-size: 14px;
}

.conv-list {
  list-style: none;
  margin: 0;
  padding: 8px;
  overflow: auto;
  flex: 1;
}

.conv-list li {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  position: relative;
}

.conv-list li:hover {
  background: #f5f7fa;
}

.conv-list li.active {
  background: #e6f4ff;
}

.conv-title {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-right: 40px;
}

.conv-meta {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.del-btn {
  position: absolute;
  right: 8px;
  top: 10px;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
  background: #fafafa;
  flex-shrink: 0;
}

.toolbar-label {
  color: #666;
  font-size: 14px;
}

.model-tag {
  margin-left: auto;
  font-size: 12px;
  color: #1677ff;
  background: #e6f4ff;
  padding: 2px 10px;
  border-radius: 10px;
}

.msg-count {
  font-size: 13px;
  color: #999;
}

.limit-alert {
  margin: 8px 16px 0;
  flex-shrink: 0;
}

.chat-box {
  flex: 1;
  padding: 16px;
  overflow: auto;
}

.msg-row {
  display: flex;
  margin-bottom: 12px;
}

.msg-row.user {
  justify-content: flex-end;
}

.msg-row.assistant {
  justify-content: flex-start;
}

.msg-wrapper {
  max-width: 75%;
  display: flex;
  flex-direction: column;
}

.sources-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 4px;
  padding: 4px 0;
}

.sources-label {
  font-size: 11px;
  color: #999;
  flex-shrink: 0;
}

.source-tag {
  display: inline-block;
  font-size: 11px;
  padding: 1px 8px;
  background: #e6f4ff;
  color: #1677ff;
  border-radius: 10px;
  white-space: nowrap;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.bubble {
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.user .bubble {
  background: #1677ff;
  color: #fff;
}

.assistant .bubble {
  background: #f5f5f5;
  color: #333;
}

.input-box {
  display: flex;
  padding: 12px 16px;
  border-top: 1px solid #eee;
  gap: 8px;
  flex-shrink: 0;
}

.input-box input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
}

.input-box button {
  padding: 8px 20px;
  background: #1677ff;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.input-box button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
}
</style>
