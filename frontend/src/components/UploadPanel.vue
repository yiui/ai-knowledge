<template>
  <div class="layout">
    <!-- 头栏：标题 + 统计 + 刷新 -->
    <div class="doc-header">
      <div class="doc-header__left">
        <h3 class="doc-header__title">📄 已上传文档</h3>
        <span class="doc-header__count">
          共 <strong>{{ totalDocs }}</strong> 个
        </span>
      </div>
      <el-button size="small" @click="refreshDocs">刷新</el-button>
    </div>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <el-input
        v-model="searchText"
        placeholder="搜索文件名..."
        size="small"
        clearable
        class="search-bar__input"
        @keyup.enter="handleSearch"
        @clear="handleSearch"
      >
        <template #prefix>
          <span>🔍</span>
        </template>
      </el-input>
      <el-select
        v-model="statusFilter"
        placeholder="状态筛选"
        size="small"
        clearable
        style="width: 130px"
        @change="handleSearch"
      >
        <el-option label="全部状态" value="" />
        <el-option label="就绪" value="ready" />
        <el-option label="处理中" value="processing" />
        <el-option label="等待处理" value="pending" />
        <el-option label="失败" value="failed" />
      </el-select>
    </div>

    <!-- 操作栏：上传 + 批量（固定高度，表格不跳动） -->
    <div class="action-bar">
      <el-button type="primary" size="small" @click="openUploadDialog">
        📤 上传文档
      </el-button>
      <div v-if="selectedDocs.length > 0" class="action-bar__batch">
        <span class="action-bar__info">
          已选 <strong>{{ selectedDocs.length }}</strong> 项
        </span>
        <el-button size="small" @click="clearTableSelection">取消选择</el-button>
        <el-button
          type="danger"
          size="small"
          :loading="batchDeleting"
          @click="handleBatchDelete"
        >
          批量删除
        </el-button>
      </div>
    </div>

    <!-- 文档表格 -->
    <el-table
      ref="docTableRef"
      :data="docItems"
      v-loading="docsLoading"
      stripe
      size="small"
      class="doc-table"
      empty-text="暂无文档"
      @selection-change="onSelectionChange"
    >
      <el-table-column type="selection" width="40" />
      <el-table-column prop="filename" label="文件名" min-width="200">
        <template #default="{ row }">
          <div class="doc-filename">
            <span class="doc-filename__icon">📄</span>
            <span class="doc-filename__text" :title="row.filename">{{ row.filename }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="size" label="大小" width="100" align="right" />
      <el-table-column label="状态" width="120" align="center">
        <template #default="{ row }">
          <span :class="['status-tag', `status-tag--${row.status}`]">
            {{ statusLabel(row.status) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="vector_count" label="向量块" width="90" align="right" />
      <el-table-column label="上传时间" width="180">
        <template #default="{ row }">
          <span class="doc-time">{{ formatToCNTime(row.created_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" align="center" fixed="right">
        <template #default="{ row }">
          <div class="doc-actions">
            <el-button
              type="primary"
              link
              size="small"
              @click="openPreview(row)"
            >
              预览
            </el-button>
            <el-button
              v-if="row.status === 'failed' || row.status === 'processing'"
              type="primary"
              link
              size="small"
              :loading="retryingIds.includes(row.id)"
              @click="retryDoc(row.id)"
            >
              重试
            </el-button>
            <el-button
              type="danger"
              link
              size="small"
              @click="removeDoc(row.id)"
            >
              删除
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="doc-pagination">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="totalDocs"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        background
        small
        @current-change="loadDocs"
        @size-change="onPageSizeChange"
      />
    </div>

    <!-- 上传弹窗 -->
    <el-dialog
      v-model="showUploadDialog"
      title="上传文档"
      width="560px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <p v-if="uploadLimits" class="upload-hint">{{ uploadLimits.hint }}</p>

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
            📋 上传队列 ({{ doneCount }}/{{ queue.length }} 完成)
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

      <template #footer>
        <el-button @click="showUploadDialog = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 文档预览抽屉 -->
    <el-drawer
      v-model="showPreviewDrawer"
      :title="previewData ? `预览: ${previewData.document.filename}` : '预览'"
      size="600px"
      destroy-on-close
    >
      <div v-loading="previewLoading" class="preview-container">
        <template v-if="previewData && previewData.chunks.length > 0">
          <div class="preview-meta">
            <span>文件大小：{{ previewData.document.size }}</span>
            <span>共 {{ previewData.chunks.length }} 个片段</span>
          </div>
          <div
            v-for="(chunk, i) in previewData.chunks"
            :key="i"
            class="chunk-block"
          >
            <div class="chunk-header">
              片段 {{ chunk.chunk_index + 1 }}/{{ chunk.chunk_total || previewData.chunks.length }}
            </div>
            <div class="chunk-content">{{ chunk.content }}</div>
          </div>
        </template>
        <div v-else-if="!previewLoading" class="preview-empty">
          暂无内容
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { getAppConfig } from '../api/config'
import {
  uploadDocument,
  getDocuments,
  deleteDocument,
  batchDeleteDocuments,
  reindexDocument,
  getDocumentStatuses,
  getDocumentChunks,
  type DocumentItem,
  type DocumentChunksResponse,
} from '../api/document'
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

// ---- 上传弹窗 ----
const showUploadDialog = ref(false)

const openUploadDialog = () => {
  showUploadDialog.value = true
}

// ---- 上传队列 ----

interface UploadTask {
  id: number
  file: File
  status: 'pending' | 'uploading' | 'success' | 'failed'
  error?: string
}

const queue = ref<UploadTask[]>([])
let nextTaskId = 0

// ---- 文档列表 & 分页 ----

const docItems = ref<DocumentItem[]>([])
const docsLoading = ref(false)
const docsPolling = ref(false)
const totalDocs = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const searchText = ref('')
const statusFilter = ref('')
const selectedDocs = ref<DocumentItem[]>([])
const batchDeleting = ref(false)
const docTableRef = ref<any>(null)

const clearTableSelection = () => {
  docTableRef.value?.clearSelection()
}

// ---- 文档预览 ----

const showPreviewDrawer = ref(false)
const previewLoading = ref(false)
const previewData = ref<DocumentChunksResponse | null>(null)

const openPreview = async (row: DocumentItem) => {
  previewLoading.value = true
  showPreviewDrawer.value = true
  try {
    previewData.value = await getDocumentChunks(row.id)
  } catch {
    previewData.value = null
  } finally {
    previewLoading.value = false
  }
}

// ---- 上传限制 ----

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

const loadDocs = async (opts?: { silent?: boolean }) => {
  if (props.knowledgeBaseId == null) return
  if (!opts?.silent) {
    docsLoading.value = true
  } else {
    docsPolling.value = true
  }
  try {
    const res = await getDocuments({
      knowledgeBaseId: props.knowledgeBaseId,
      page: currentPage.value,
      pageSize: pageSize.value,
      search: searchText.value || undefined,
      status: statusFilter.value || undefined,
    })
    docItems.value = res.items
    totalDocs.value = res.total
  } catch {
    if (!opts?.silent) {
      docItems.value = []
      totalDocs.value = 0
    }
  } finally {
    docsLoading.value = false
    docsPolling.value = false
  }
}

const refreshDocs = () => {
  currentPage.value = 1
  loadDocs()
}

const handleSearch = () => {
  currentPage.value = 1
  loadDocs()
}

const onPageSizeChange = () => {
  currentPage.value = 1
  loadDocs()
}

const onSelectionChange = (rows: DocumentItem[]) => {
  selectedDocs.value = rows
}

watch(
  () => props.knowledgeBaseId,
  () => {
    currentPage.value = 1
    searchText.value = ''
    statusFilter.value = ''
    loadDocs()
  },
  { immediate: true },
)

// ---- 轮询：仅用轻量端点原地修补状态，表格不闪不跳 ----

let pollTimer: ReturnType<typeof setInterval> | null = null
let pollInterval = 5000 // 基础 5 秒
let noChangeRounds = 0

const collectDirtyIds = (): number[] =>
  docItems.value
    .filter((d) => d.status === 'pending' || d.status === 'processing')
    .map((d) => d.id)

const pollDocStatuses = async () => {
  const dirtyIds = collectDirtyIds()
  if (dirtyIds.length === 0) {
    stopPolling()
    return
  }

  try {
    const statuses = await getDocumentStatuses(props.knowledgeBaseId!, dirtyIds)
    const map = new Map(statuses.map((s) => [s.id, s]))

    let changed = false
    for (const row of docItems.value) {
      const fresh = map.get(row.id)
      if (!fresh) continue
      if (
        fresh.status !== row.status ||
        fresh.vector_count !== row.vector_count ||
        fresh.error_message !== row.error_message
      ) {
        row.status = fresh.status
        row.vector_count = fresh.vector_count
        row.error_message = fresh.error_message
        changed = true
      }
    }

    // 自适应间隔：无变化加倍（上限 20s），有变化重置
    if (changed) {
      pollInterval = 5000
      noChangeRounds = 0
    } else {
      noChangeRounds++
      if (noChangeRounds >= 2) {
        pollInterval = Math.min(pollInterval * 2, 20000)
        noChangeRounds = 0
      }
    }

    // 重置定时器以应用新间隔
    if (pollTimer) clearInterval(pollTimer)
    pollTimer = setInterval(pollDocStatuses, pollInterval)
  } catch {
    // 静默失败
  }
}

const startPolling = () => {
  if (pollTimer) return
  pollInterval = 5000
  noChangeRounds = 0
  pollTimer = setInterval(pollDocStatuses, pollInterval)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  docsPolling.value = false
}

watch(
  () => docItems.value.map((d) => d.status).join(','),
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

  // 上传完成 → 全量刷新一次（跳到第 1 页），后续由轻量轮询负责
  currentPage.value = 1
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
  try {
    await ElMessageBox.confirm('确定删除该文档吗？相关向量也会一并删除。', '确认删除', {
      type: 'warning',
    })
    await deleteDocument(id)
    await loadDocs()
  } catch {
    // cancelled
  }
}

const handleBatchDelete = async () => {
  const ids = selectedDocs.value.map((d) => d.id)
  if (ids.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${ids.length} 个文档吗？相关向量也会一并删除。`,
      '批量删除',
      { type: 'warning' },
    )
    batchDeleting.value = true
    await batchDeleteDocuments(ids)
    clearTableSelection()
    await loadDocs()
  } catch {
    // cancelled or failed
  } finally {
    batchDeleting.value = false
  }
}

const retryDoc = async (id: number) => {
  retryingIds.value.push(id)
  try {
    await reindexDocument(id)
    await loadDocs()
    startPolling()
  } catch (e: any) {
    // 静默失败
  } finally {
    retryingIds.value = retryingIds.value.filter((x) => x !== id)
  }
}
</script>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* ---- 头栏 ---- */

.doc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}

.doc-header__left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.doc-header__title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.doc-header__count {
  font-size: 13px;
  color: #666;
}

.doc-header__count strong {
  font-weight: 600;
  color: #333;
}

/* ---- 搜索栏 ---- */

.search-bar {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 10px 20px;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}

.search-bar__input {
  width: 320px;
}

/* ---- 操作栏 ---- */

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 20px;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
  min-height: 40px;
}

.action-bar__batch {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-bar__info {
  font-size: 13px;
  color: #1677ff;
}

.action-bar__info strong {
  font-weight: 600;
}

.doc-table {
  flex: 1;
  font-size: 13px;
}

.doc-table :deep(th) {
  font-weight: 600;
  color: #555;
}

.doc-filename {
  display: flex;
  align-items: center;
  gap: 6px;
}

.doc-filename__icon {
  flex-shrink: 0;
}

.doc-filename__text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-time {
  font-size: 12px;
  color: #888;
}

.doc-actions {
  display: flex;
  gap: 4px;
  justify-content: center;
}

/* ---- 状态标签 ---- */

.status-tag {
  display: inline-block;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
  line-height: 1.4;
}

.status-tag--pending {
  background: #f0f0f0;
  color: #666;
}

.status-tag--processing {
  background: #e6f4ff;
  color: #1677ff;
}

.status-tag--ready {
  background: #f6ffed;
  color: #389e0d;
}

.status-tag--failed {
  background: #fff1f0;
  color: #cf1322;
}

/* ---- 分页 ---- */

.doc-pagination {
  padding: 10px 20px;
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid #eee;
  flex-shrink: 0;
  background: #fff;
}

/* ---- 上传弹窗 ---- */

.upload-hint {
  font-size: 13px;
  color: #666;
  margin: 0 0 16px;
  line-height: 1.5;
}

.drop-zone {
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  padding: 28px 16px;
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
  font-size: 36px;
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
  margin-bottom: 6px;
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

/* ---- 文档预览 ---- */

.preview-container {
  padding: 0 4px;
}

.preview-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #999;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #eee;
}

.chunk-block {
  margin-bottom: 20px;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
}

.chunk-header {
  padding: 6px 14px;
  background: #e6f4ff;
  color: #1677ff;
  font-size: 12px;
  font-weight: 600;
}

.chunk-content {
  padding: 12px 14px;
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  color: #333;
}

.preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #999;
  font-size: 14px;
}
</style>
