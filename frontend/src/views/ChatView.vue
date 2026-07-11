<template>
  <div class="chat-layout">
    <aside class="conv-sidebar">
      <div class="sidebar-header">
        <h2>对话</h2>
        <el-button type="primary" size="small" @click="handleNewConversation">
          新对话
        </el-button>
      </div>
      <div class="sidebar-search">
        <el-input
          v-model="convSearch"
          placeholder="搜索对话..."
          size="small"
          clearable
        />
      </div>
      <div v-if="filteredConversations.length === 0" class="empty-tip">
        {{ conversations.length === 0 ? '暂无对话，点击「新对话」开始' : '无匹配结果' }}
      </div>
      <ul v-else class="conv-list">
        <li
          v-for="conv in filteredConversations"
          :key="conv.id"
          :class="{ active: currentId === conv.id }"
          @click="selectConversation(conv.id)"
        >
          <div class="conv-title">{{ conv.title }}</div>
          <div class="conv-meta">{{ conv.message_count }}/{{ conv.max_messages }} 条</div>
          <el-button
            type="danger" link size="small" class="del-btn"
            @click.stop="handleDeleteConversation(conv.id)"
          >删除</el-button>
        </li>
      </ul>
    </aside>

    <main class="chat-main">
      <template v-if="currentId">
        <!-- 顶栏：标题 + 模型 -->
        <div class="chat-topbar">
          <span class="chat-topbar__title">{{ currentTitle }}</span>
          <span class="chat-topbar__meta">
            <span v-if="llmModel" class="model-badge">{{ llmProvider }} / {{ llmModel }}</span>
            <span class="msg-badge">{{ messageCount }}/{{ maxMessages }}</span>
          </span>
        </div>

        <el-alert
          v-if="shouldStartNew"
          type="warning" :closable="false" show-icon class="limit-alert"
          title="当前会话消息已达上限，建议点击左侧「新对话」开启新会话"
        />

        <!-- 消息区 -->
        <div ref="chatBoxRef" class="chat-box">
          <div
            v-for="msg in messages"
            :key="msg.id ?? msg.localKey"
            :class="['msg-row', msg.role]"
          >
            <div class="msg-wrapper">
              <div class="bubble" :class="{ 'bubble--user': msg.role === 'user' }">
                <div v-if="msg.sources && msg.sources.length > 0" class="bubble-sources">
                  <span
                    v-for="(src, i) in msg.sources"
                    :key="i"
                    class="source-chip"
                  >
                    {{ src.filename }}{{ src.chunk_total > 0 ? ` · 片段 ${src.chunk_index + 1}/${src.chunk_total}` : '' }}
                  </span>
                </div>
                <div class="bubble-text">{{ msg.content }}</div>
              </div>
            </div>
          </div>
          <div v-if="loading" class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
        </div>

        <!-- 输入区 -->
        <div class="input-area">
          <textarea
            v-model="question"
            ref="inputRef"
            placeholder="输入问题... Shift+Enter 换行，Enter 发送"
            :disabled="loading || shouldStartNew"
            rows="1"
            @keydown.enter="onInputKeydown"
            @input="autoResizeInput"
          />
          <div class="input-actions">
            <el-select
              v-model="selectedKbId"
              clearable
              size="small"
              placeholder="选择知识库"
              style="width: 180px"
              @change="onKbChange"
            >
              <el-option v-for="kb in kbs" :key="kb.id" :label="kb.name" :value="kb.id" />
            </el-select>
            <el-button
              v-if="loading"
              type="danger"
              size="small"
              @click="stopGeneration"
            >⏹ 停止</el-button>
            <el-button
              type="primary"
              size="small"
              :disabled="!question.trim() || loading || shouldStartNew"
              @click="send"
            >发送</el-button>
          </div>
        </div>
      </template>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <div class="empty-state__icon">💬</div>
        <div class="empty-state__title">开始对话</div>
        <div class="empty-state__desc">选择一个知识库开始 RAG 问答，或直接提问进行通用对话</div>
        <el-button type="primary" @click="handleNewConversation">新对话</el-button>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
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
const inputRef = ref(null)
const llmProvider = ref('')
const llmModel = ref('')
const convSearch = ref('')
let abortController = null
let localKeySeq = 0

const filteredConversations = computed(() => {
  if (!convSearch.value.trim()) return conversations.value
  const q = convSearch.value.toLowerCase()
  return conversations.value.filter((c) => c.title.toLowerCase().includes(q))
})

const currentTitle = computed(() => {
  const conv = conversations.value.find((c) => c.id === currentId.value)
  return conv?.title ?? ''
})

const scrollToBottom = async () => {
  await nextTick()
  if (chatBoxRef.value) {
    chatBoxRef.value.scrollTop = chatBoxRef.value.scrollHeight
  }
}

const autoResizeInput = () => {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 120) + 'px'
}

const onInputKeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
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
  const conv = await createConversation({ knowledge_base_id: selectedKbId.value ?? null })
  await loadConversationList()
  await selectConversation(conv.id)
}

const handleDeleteConversation = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除该对话？删除后无法恢复。', '确认删除', { type: 'warning' })
    await deleteConversation(id)
    if (currentId.value === id) { currentId.value = null; messages.value = [] }
    await loadConversationList()
  } catch { /* cancelled */ }
}

const onKbChange = async (kbId) => {
  if (!currentId.value) return
  await updateConversation(currentId.value, { knowledge_base_id: kbId ?? null })
  await loadConversationList()
}

const stopGeneration = () => {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
  loading.value = false
}

const send = async () => {
  if (!question.value.trim() || loading.value || !currentId.value) return
  if (shouldStartNew.value) { ElMessage.warning('请先开启新对话'); return }

  const q = question.value.trim()
  question.value = ''
  autoResizeInput()

  messages.value.push({ role: 'user', content: q, localKey: `local-${++localKeySeq}` })
  messageCount.value += 1

  const assistantLocalKey = `local-${++localKeySeq}`
  messages.value.push({ role: 'assistant', content: '', localKey: assistantLocalKey })
  const assistantIndex = messages.value.length - 1
  await scrollToBottom()

  loading.value = true
  abortController = new AbortController()
  try {
    await chatStreamInConversation(
      currentId.value, q,
      (chunk) => { messages.value[assistantIndex].content += chunk; scrollToBottom() },
      (sources) => { messages.value[assistantIndex].sources = sources },
      (meta) => {
        messageCount.value = meta.message_count
        maxMessages.value = meta.max_messages
        shouldStartNew.value = meta.should_start_new
        if (meta.should_start_new) ElMessage.warning(`当前会话已达 ${meta.max_messages} 条消息上限`)
      },
      abortController.signal,
    )
    await loadConversationList()
    const detail = await getConversation(currentId.value)
    applyConversationMeta(detail)
  } catch (e) {
    if (e?.name === 'AbortError') return
    messages.value[assistantIndex].content = e instanceof Error ? e.message : '请求失败'
    messageCount.value = Math.max(0, messageCount.value - 1)
  } finally {
    loading.value = false
    abortController = null
    await scrollToBottom()
  }
}

onMounted(async () => {
  try {
    const cfg = await getAppConfig()
    if (cfg.llm) { llmProvider.value = cfg.llm.provider; llmModel.value = cfg.llm.model }
  } catch { /* ok */ }
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

/* ---- 对话侧栏 ---- */

.conv-sidebar {
  width: 260px;
  border-right: 1px solid #edf0f4;
  background: #fff;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #1d1f24;
}

.sidebar-search {
  padding: 0 12px 12px;
}

.empty-tip {
  padding: 32px 16px;
  color: #a0a4ac;
  font-size: 13px;
  text-align: center;
}

.conv-list {
  list-style: none;
  margin: 0;
  padding: 0 8px 8px;
  overflow: auto;
  flex: 1;
}

.conv-list li {
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  margin-bottom: 2px;
  position: relative;
  transition: all 0.15s ease;
}

.conv-list li:hover { background: #f3f5f8; }
.conv-list li.active { background: #eef4ff; }

.conv-title {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding-right: 36px;
  font-weight: 500;
  color: #1d1f24;
}

.conv-meta {
  font-size: 12px;
  color: #a0a4ac;
  margin-top: 3px;
}

.del-btn {
  position: absolute;
  right: 4px;
  top: 8px;
  opacity: 0;
  transition: opacity 0.15s;
}

.conv-list li:hover .del-btn { opacity: 1; }

/* ---- 对话主区 ---- */

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f8f9fb;
}

.chat-topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  height: 44px;
  background: #fff;
  border-bottom: 1px solid #edf0f4;
  flex-shrink: 0;
}

.chat-topbar__title {
  font-size: 14px;
  font-weight: 600;
  color: #1d1f24;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-topbar__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.model-badge {
  font-size: 11px;
  color: #1677ff;
  background: #eef4ff;
  padding: 2px 10px;
  border-radius: 10px;
  font-weight: 500;
}

.msg-badge { font-size: 12px; color: #a0a4ac; }

.limit-alert {
  margin: 0 16px;
  margin-top: 8px;
  flex-shrink: 0;
}

/* ---- 消息区 ---- */

.chat-box {
  flex: 1;
  padding: 20px 24px;
  overflow: auto;
}

.msg-row {
  display: flex;
  margin-bottom: 20px;
}

.msg-row.user { justify-content: flex-end; }
.msg-row.assistant { justify-content: flex-start; }

.msg-wrapper { max-width: 78%; }

.bubble {
  border-radius: 12px;
  overflow: hidden;
}

.bubble--user {
  background: #1677ff;
  color: #fff;
  box-shadow: 0 1px 3px rgba(22,119,255,0.2);
}

.bubble--user .bubble-text {
  padding: 10px 16px;
}

.assistant .bubble {
  background: #fff;
  border: 1px solid #edf0f4;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}

.bubble-sources {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  padding: 7px 12px 5px;
  background: #f8f9fc;
  border-bottom: 1px solid #edf0f4;
}

.source-chip {
  font-size: 11px;
  padding: 2px 8px;
  background: #eef4ff;
  color: #1677ff;
  border-radius: 6px;
}

.bubble-text {
  padding: 12px 16px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 14px;
  color: #2d3037;
}

.assistant .bubble-text {
  color: #2d3037;
}

/* ---- 打字动画 ---- */

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 4px 0 12px;
}

.typing-indicator span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #c0c4cc;
  animation: typing 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: 0s; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* ---- 输入区 ---- */

.input-area {
  padding: 16px 24px 20px;
  flex-shrink: 0;
  background: #fff;
  border-top: 1px solid #edf0f4;
}

.input-area textarea {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #e0e3e8;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.5;
  resize: none;
  outline: none;
  box-sizing: border-box;
  font-family: inherit;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: #f8f9fb;
}

.input-area textarea:focus {
  border-color: #1677ff;
  box-shadow: 0 0 0 3px rgba(22,119,255,0.08);
  background: #fff;
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
}

/* ---- 空状态 ---- */

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #f8f9fb;
}

.empty-state__icon { font-size: 52px; }
.empty-state__title { font-size: 20px; font-weight: 700; color: #1d1f24; }
.empty-state__desc { font-size: 14px; color: #a0a4ac; margin-bottom: 12px; }
</style>
