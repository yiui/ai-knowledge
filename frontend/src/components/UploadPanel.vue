<template>
  <div class="layout">
    <div class="upload-panel">
      <h2>上传文档</h2>

      <input type="file" @change="onFileChange" />

      <button @click="upload">上传</button>

      <p>{{ msg }}</p>
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
import { ref, watch } from 'vue'
import { uploadDocument, getDocuments, deleteDocument } from '../api/document'
import { formatToCNTime } from '../utils/time'

const props = defineProps({
  knowledgeBaseId: {
    type: Number,
    required: true,
  },
})

const file = ref(null)
const msg = ref('')
const docs = ref([])

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

const onFileChange = (e) => {
  file.value = e.target.files[0]
}

const removeDoc = async (id) => {
  await deleteDocument(id)
  await loadDocs()
}

const upload = async () => {
  if (!file.value) return
  msg.value = '上传中...'
  try {
    await uploadDocument(file.value, props.knowledgeBaseId)
    msg.value = '上传成功'
    await loadDocs()
  } catch {
    msg.value = '上传失败'
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
