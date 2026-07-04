<template>
  <div class="layout">
    <div class="upload-panel">
      <h2>上传文档</h2>

      <p v-if="uploadLimits" class="upload-hint">{{ uploadLimits.hint }}</p>

      <input
        ref="fileInputRef"
        type="file"
        :accept="acceptAttr"
        @change="onFileChange"
      />

      <button :disabled="!file || uploading" @click="upload">
        {{ uploading ? '上传中...' : '上传' }}
      </button>

      <p :class="['msg', msgError ? 'error' : '']">{{ msg }}</p>
    </div>

    <div class="doc-panel">
      <h3>已上传文档</h3>

      <div v-if="docs.length === 0">
        暂无文档
      </div>

      <ul>
        <li v-for="doc in docs" :key="doc.id" class="doc-item">
          <div class="name">
            <span>📄 {{ doc.filename }}</span>
            <span :class="['status-badge', `status-${doc.status}`]">
              {{ statusLabel(doc.status) }}
            </span>
          </div>

          <div class="meta">
            <span>📦 {{ doc.size }}</span>
            <span>🕒 {{ formatToCNTime(doc.created_at) }}</span>
            <span v-if="doc.status === 'ready'" class="vector-info">
              🧬 {{ doc.vector_count ?? 0 }} chunks
            </span>
          </div>

          <div v-if="doc.status === 'failed' && doc.error_message" class="err-msg">
            ❌ {{ doc.error_message }}
          </div>

          <div class="actions">
            <button
              v-if="doc.status === 'failed' || doc.status === 'processing'"
              class="retry-btn"
              :disabled="retryingIds.includes(doc.id)"
              @click="retryDoc(doc.id)"
            >
              {{ retryingIds.includes(doc.id) ? '重试中…' : '重试' }}
            </button>
            <button class="del-btn" @click="removeDoc(doc.id)">
              删除
            </button>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getAppConfig } from '../api/config'
import { uploadDocument, getDocuments, deleteDocument, reindexDocument } from '../api/document'
import {
  buildAcceptAttr,
  getMaxSizeBytes,
  uploadConfigFromEnv,
} from '../config/upload'
import { formatToCNTime } from '../utils/time'
import { validateUploadFile } from '../utils/uploadValidate'

const props = defineProps({
  knowledgeBaseId: {
    type: Number,
    required: true,
  },
})

const file = ref(null)
const msg = ref('')
const msgError = ref(false)
const uploading = ref(false)
const docs = ref([])
const uploadLimits = ref(null)
const fileInputRef = ref(null)
const retryingIds = ref([])

const acceptAttr = computed(() => {
  if (uploadLimits.value?.accept) {
    return uploadLimits.value.accept
  }
  return buildAcceptAttr(uploadConfigFromEnv.allowedExtensions)
})

const STATUS_LABELS = {
  pending: '等待处理',
  processing: '向量化中…',
  ready: '就绪',
  failed: '失败',
}

const statusLabel = (s) => STATUS_LABELS[s] || s

const loadUploadLimits = async () => {
  try {
    const config = await getAppConfig()
    if (config.upload) {
      uploadLimits.value = config.upload
      return
    }
  } catch {
    // 使用前端环境变量兜底
  }
  const { maxSizeMb, allowedExtensions } = uploadConfigFromEnv
  uploadLimits.value = {
    max_size_mb: maxSizeMb,
    max_size_bytes: getMaxSizeBytes(maxSizeMb),
    allowed_extensions: allowedExtensions,
    accept: buildAcceptAttr(allowedExtensions),
    hint: `支持 ${allowedExtensions.join(', ')}，单文件不超过 ${maxSizeMb}MB`,
  }
}

const loadDocs = async () => {
  docs.value = await getDocuments(props.knowledgeBaseId)
}

watch(
  () => props.knowledgeBaseId,
  () => {
    loadDocs()
  },
  { immediate: true },
)

// —— 轮询：仅当存在 processing 文档时启动 ——
let pollTimer = null
const startPolling = () => {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    const hasProcessing = docs.value.some(
      (d) => d.status === 'pending' || d.status === 'processing',
    )
    if (!hasProcessing) {
      stopPolling()
      return
    }
    try {
      await loadDocs()
    } catch (e) {
      // 静默失败，下次继续
    }
  }, 2000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

watch(
  () => docs.value.map((d) => d.status).join(','),
  (next) => {
    if (next.includes('pending') || next.includes('processing')) {
      startPolling()
    } else {
      stopPolling()
    }
  },
)

onBeforeUnmount(stopPolling)
onMounted(loadUploadLimits)

const onFileChange = (e) => {
  msgError.value = false
  const selected = e.target.files?.[0]
  if (!selected) {
    file.value = null
    return
  }

  if (!uploadLimits.value) {
    file.value = selected
    return
  }

  const err = validateUploadFile(selected, uploadLimits.value)
  if (err) {
    msg.value = err
    msgError.value = true
    file.value = null
    if (fileInputRef.value) {
      fileInputRef.value.value = ''
    }
    return
  }

  file.value = selected
  msg.value = `已选择: ${selected.name}`
}

const removeDoc = async (id) => {
  if (!confirm('确定删除该文档吗？相关向量也会一并删除。')) return
  await deleteDocument(id)
  await loadDocs()
}

const retryDoc = async (id) => {
  retryingIds.value.push(id)
  try {
    await reindexDocument(id)
    msg.value = '已提交重试，正在重新向量化…'
    msgError.value = false
    await loadDocs()
    startPolling()
  } catch (e) {
    const detail = e?.response?.data?.detail
    msg.value = typeof detail === 'string' ? detail : '重试失败'
    msgError.value = true
  } finally {
    retryingIds.value = retryingIds.value.filter((x) => x !== id)
  }
}

const upload = async () => {
  if (!file.value || !uploadLimits.value) return

  const err = validateUploadFile(file.value, uploadLimits.value)
  if (err) {
    msg.value = err
    msgError.value = true
    return
  }

  uploading.value = true
  msgError.value = false
  msg.value = '上传中...'
  try {
    await uploadDocument(file.value, props.knowledgeBaseId)
    msg.value = '上传成功，正在向量化…'
    file.value = null
    if (fileInputRef.value) {
      fileInputRef.value.value = ''
    }
    await loadDocs()
    startPolling()
  } catch (e) {
    const detail = e?.response?.data?.detail
    msg.value = typeof detail === 'string' ? detail : '上传失败'
    msgError.value = true
  } finally {
    uploading.value = false
  }
}
</script>

<style scoped>
.layout {
  display: flex;
  height: 100%;
}

.upload-panel {
  width: 40%;
  padding: 20px;
  border-right: 1px solid #eee;
}

.upload-hint {
  font-size: 13px;
  color: #666;
  margin: 0 0 12px;
  line-height: 1.5;
}

.doc-panel {
  width: 60%;
  padding: 20px;
  overflow: auto;
}

ul {
  padding: 0;
}

li {
  list-style: none;
  padding: 10px;
  border-bottom: 1px solid #eee;
}

.doc-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #888;
  align-items: center;
}

.vector-info {
  color: #52c41a;
}

.err-msg {
  font-size: 12px;
  color: #ff4d4f;
  background: #fff1f0;
  border: 1px solid #ffccc7;
  border-radius: 4px;
  padding: 4px 8px;
  word-break: break-all;
}

.actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.status-badge {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
  line-height: 1.4;
}

.status-pending {
  background: #f0f0f0;
  color: #666;
}
.status-processing {
  background: #e6f4ff;
  color: #1677ff;
}
.status-ready {
  background: #f6ffed;
  color: #389e0d;
}
.status-failed {
  background: #fff1f0;
  color: #cf1322;
}

.msg {
  margin-top: 8px;
  font-size: 14px;
  color: #52c41a;
}

.msg.error {
  color: #ff4d4f;
}

.del-btn,
.retry-btn {
  padding: 4px 10px;
  font-size: 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: white;
}

.del-btn {
  background: #ff4d4f;
}
.del-btn:hover {
  background: #d9363e;
}

.retry-btn {
  background: #1677ff;
}
.retry-btn:hover:not(:disabled) {
  background: #0958d9;
}
.retry-btn:disabled {
  background: #91caff;
  cursor: not-allowed;
}
</style>
