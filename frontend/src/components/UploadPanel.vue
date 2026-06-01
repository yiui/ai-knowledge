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
          <div class="name">📄 {{ doc.filename }}</div>

          <div class="meta">
            <span>📦 {{ doc.size }}</span>
            <span>🕒 {{ formatToCNTime(doc.created_at) }}</span>
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
import { computed, onMounted, ref, watch } from 'vue'
import { getAppConfig } from '../api/config'
import { uploadDocument, getDocuments, deleteDocument } from '../api/document'
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

const acceptAttr = computed(() => {
  if (uploadLimits.value?.accept) {
    return uploadLimits.value.accept
  }
  return buildAcceptAttr(uploadConfigFromEnv.allowedExtensions)
})

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
  await deleteDocument(id)
  await loadDocs()
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
    msg.value = '上传成功'
    file.value = null
    if (fileInputRef.value) {
      fileInputRef.value.value = ''
    }
    await loadDocs()
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

.msg {
  margin-top: 8px;
  font-size: 14px;
  color: #52c41a;
}

.msg.error {
  color: #ff4d4f;
}

.del-btn {
  margin-left: auto;
  padding: 4px 8px;
  font-size: 12px;
  background: #ff4d4f;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.del-btn:hover {
  background: #d9363e;
}
</style>
