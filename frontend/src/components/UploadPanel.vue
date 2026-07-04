<template>
  <div class="layout">
    <div class="upload-panel">
      <h2>上传文档</h2>

      <p v-if="uploadLimits" class="upload-hint">{{ uploadLimits.hint }}</p>

      <!-- 拖拽上传区 -->
      <div
        :class="['drop-zone', { 'drop-zone--active': dragOver }]"
        @dragover.prevent="onDragOver"
        @dragenter.prevent="onDragEnter"
        @dragleave="onDragLeave"
        @drop.prevent="onDrop"
      >
        <div class="drop-zone__icon">📂</div>
        <div class="drop-zone__text">拖拽文件或文件夹到此处</div>
        <div class="drop-zone__actions">
          <el-button size="small" @click="openFilePicker">选择文件</el-button>
          <el-button size="small" @click="openFolderPicker">选择文件夹</el-button>
        </div>
      </div>

      <!-- 隐藏的文件选择 input -->
      <input
        ref="fileInputRef"
        type="file"
        :accept="acceptAttr"
        multiple
        hidden
        @change="onInputChange"
      />
      <input
        ref="folderInputRef"
        type="file"
        :accept="acceptAttr"
        webkitdirectory
        hidden
        @change="onInputChange"
      />

      <!-- 上传队列 -->
      <div v-if="queue.length > 0" class="queue-panel">
        <div class="queue-header">
          <span>
            📋 上传队列
            ({{ doneCount }}/{{ queue.length }} 完成)
          </span>
          <el-button
            v-if="doneCount > 0"
            link
            size="small"
            @click="clearDone"
          >
            清空已完成
          </el-button>
        </div>
        <ul class="queue-list">
          <li
            v-for="task in queue"
            :key="task.id"
            :class="['queue-item', `queue-item--${task.status}`]"
          >
            <span class="queue-item__icon">{{ statusIcon(task.status) }}</span>
            <span class="queue-item__name" :title="task.file.name">
              {{ task.file.name }}
            </span>
            <span class="queue-item__size">{{ formatFileSize(task.file.size) }}</span>
            <span v-if="task.status === 'uploading'" class="queue-item__hint">上传中...</span>
            <span
              v-else-if="task.status === 'failed' && task.error"
              class="queue-item__err"
              :title="task.error"
            >
              {{ task.error }}
            </span>
          </li>
        </ul>
      </div>
    </div>

    <!-- 已上传文档列表（保持不变） -->
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

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getAppConfig } from '../api/config'
import { uploadDocument, getDocuments, deleteDocument, reindexDocument } from '../api/document'
import {
  buildAcceptAttr,
  getMaxSizeBytes,
  uploadConfigFromEnv,
} from '../config/upload'
import type { UploadLimits } from '../config/upload'
import { formatToCNTime } from '../utils/time'
import { validateUploadFile } from '../utils/uploadValidate'

const props = defineProps({
  knowledgeBaseId: {
    type: Number,
    default: undefined,
  },
})

// ---- 上传队列 ----

interface UploadTask {
  id: number
  file: File
  status: 'pending' | 'uploading' | 'success' | 'failed'
  error?: string
}

const queue = ref<UploadTask[]>([])
let nextTaskId = 0

// ---- 文档列表 ----

const docs = ref<any[]>([])
const uploadLimits = ref<UploadLimits | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
const folderInputRef = ref<HTMLInputElement | null>(null)
const retryingIds = ref<number[]>([])

const acceptAttr = computed(() => {
  if (uploadLimits.value?.accept) {
    return uploadLimits.value.accept
  }
  return buildAcceptAttr(uploadConfigFromEnv.allowedExtensions)
})

const doneCount = computed(() =>
  queue.value.filter((t) => t.status === 'success' || t.status === 'failed').length,
)

const STATUS_LABELS: Record<string, string> = {
  pending: '等待处理',
  processing: '向量化中…',
  ready: '就绪',
  failed: '失败',
}

const statusLabel = (s: string) => STATUS_LABELS[s] || s

const statusIcon = (s: UploadTask['status']) => {
  switch (s) {
    case 'success':
      return '✅'
    case 'failed':
      return '❌'
    case 'uploading':
      return '⏳'
    default:
      return '⏸'
  }
}

const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// ---- 上传限制加载 ----

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

// ---- 文档列表加载 ----

const loadDocs = async () => {
  if (props.knowledgeBaseId == null) return
  docs.value = await getDocuments(props.knowledgeBaseId)
}

watch(
  () => props.knowledgeBaseId,
  () => {
    loadDocs()
  },
  { immediate: true },
)

// ---- 轮询 ----

let pollTimer: ReturnType<typeof setInterval> | null = null
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
    } catch {
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

// ---- 文件选择 ----

const openFilePicker = () => {
  fileInputRef.value?.click()
}

const openFolderPicker = () => {
  folderInputRef.value?.click()
}

const onInputChange = (e: Event) => {
  const input = e.target as HTMLInputElement
  const fileList = input.files
  if (!fileList || fileList.length === 0) return

  const files = Array.from(fileList)
  input.value = '' // 清空以便重复选择同一文件
  addToQueue(files)
}

// ---- 拖拽处理 ----

const dragOver = ref(false)
let dragEnterCount = 0

const onDragEnter = () => {
  dragEnterCount++
  dragOver.value = true
}

const onDragOver = () => {
  dragOver.value = true
}

const onDragLeave = () => {
  dragEnterCount--
  if (dragEnterCount <= 0) {
    dragEnterCount = 0
    dragOver.value = false
  }
}

const onDrop = async (e: DragEvent) => {
  dragOver.value = false
  dragEnterCount = 0

  const items = e.dataTransfer?.items
  if (!items || items.length === 0) return

  const files: File[] = []
  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    if (!item) continue
    const entry = item.webkitGetAsEntry()
    if (entry) {
      await traverseFileTree(entry, files)
    }
  }

  if (files.length > 0) {
    addToQueue(files)
  }
}

async function traverseFileTree(
  entry: FileSystemEntry,
  result: File[],
): Promise<void> {
  if (entry.isFile) {
    const file = await new Promise<File>((resolve, reject) => {
      ;(entry as FileSystemFileEntry).file(resolve, reject)
    })
    result.push(file)
  } else if (entry.isDirectory) {
    const reader = (entry as FileSystemDirectoryEntry).createReader()
    // readEntries 每次最多返回一批，需要循环读取
    const allEntries: FileSystemEntry[] = []
    let batch: FileSystemEntry[]
    do {
      batch = await new Promise<FileSystemEntry[]>((resolve, reject) => {
        reader.readEntries(resolve, reject)
      })
      allEntries.push(...batch)
    } while (batch.length > 0)

    for (const child of allEntries) {
      await traverseFileTree(child, result)
    }
  }
}

// ---- 队列处理 ----

const addToQueue = (files: File[]) => {
  if (!uploadLimits.value) return

  for (const f of files) {
    const err = validateUploadFile(f, uploadLimits.value)
    if (err) {
      queue.value.push({
        id: nextTaskId++,
        file: f,
        status: 'failed',
        error: err,
      })
      continue
    }
    queue.value.push({
      id: nextTaskId++,
      file: f,
      status: 'pending',
    })
  }

  processQueue()
}

let processing = false
const processQueue = async () => {
  if (processing) return
  processing = true

  for (const task of queue.value) {
    if (task.status !== 'pending') continue

    task.status = 'uploading'
    try {
      if (props.knowledgeBaseId == null) {
        task.status = 'failed'
        task.error = '未选择知识库'
        continue
      }
      await uploadDocument(task.file, props.knowledgeBaseId)
      task.status = 'success'
    } catch (e: any) {
      task.status = 'failed'
      task.error =
        e?.response?.data?.detail || (e instanceof Error ? e.message : '上传失败')
    }
  }

  processing = false

  // 刷新文档列表并启动轮询
  await loadDocs()
  startPolling()
}

const clearDone = () => {
  queue.value = queue.value.filter(
    (t) => t.status !== 'success' && t.status !== 'failed',
  )
}

// ---- 文档操作 ----

const removeDoc = async (id: number) => {
  if (!confirm('确定删除该文档吗？相关向量也会一并删除。')) return
  await deleteDocument(id)
  await loadDocs()
}

const retryDoc = async (id: number) => {
  retryingIds.value.push(id)
  try {
    await reindexDocument(id)
    await loadDocs()
    startPolling()
  } catch (e: any) {
    // 静默失败，轮询会反映状态
  } finally {
    retryingIds.value = retryingIds.value.filter((x) => x !== id)
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

/* ---- 拖拽区 ---- */

.drop-zone {
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  padding: 24px 16px;
  text-align: center;
  transition: border-color 0.2s, background 0.2s;
  cursor: pointer;
}

.drop-zone:hover,
.drop-zone--active {
  border-color: #1677ff;
  background: #e6f4ff;
}

.drop-zone__icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.drop-zone__text {
  font-size: 14px;
  color: #999;
  margin-bottom: 12px;
}

.drop-zone__actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}

/* ---- 上传队列 ---- */

.queue-panel {
  margin-top: 16px;
}

.queue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 8px;
}

.queue-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 240px;
  overflow: auto;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
}

.queue-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  font-size: 13px;
  border-bottom: 1px solid #f5f5f5;
}

.queue-item:last-child {
  border-bottom: none;
}

.queue-item__icon {
  flex-shrink: 0;
  font-size: 14px;
}

.queue-item__name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-item__size {
  color: #999;
  font-size: 12px;
  flex-shrink: 0;
}

.queue-item__hint {
  color: #1677ff;
  font-size: 12px;
  flex-shrink: 0;
}

.queue-item__err {
  color: #ff4d4f;
  font-size: 12px;
  flex-shrink: 0;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.queue-item--failed {
  background: #fff2f0;
}

.queue-item--uploading {
  background: #e6f4ff;
}

.queue-item--success {
  background: #f6ffed;
}

/* ---- 文档列表 ---- */

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
