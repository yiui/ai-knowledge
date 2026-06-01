<template>
  <div class="layout">
    <!-- 左侧上传 -->
    <div class="upload-panel">
      <h2>上传文档</h2>

      <input type="file" @change="onFileChange" />

      <button @click="upload">上传</button>

      <p>{{ msg }}</p>
    </div>

    <!-- 右侧文档列表 -->
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
import { ref, onMounted } from 'vue'
import { uploadDocument, getDocuments } from '../api/document'
import { formatToCNTime } from '../utils/time'
import { deleteDocument } from '../api/document'

const removeDoc = async (id) => {
  await deleteDocument(id)
  await loadDocs()
}
  
const file = ref(null)
const msg = ref('')
const docs = ref([])

const loadDocs = async () => {
  docs.value = await getDocuments()
}

onMounted(() => {
  loadDocs()
})

const onFileChange = (e) => {
  file.value = e.target.files[0]
}

  const removeDocFunc = async (id) => {
    await deleteDocument(id)
    await loadDocs()
} 

const upload = async () => {
  if (!file.value) return
  msg.value = '上传中...'
  try {
    await uploadDocument(file.value)
    msg.value = '上传成功'

    // 🔥 上传后刷新列表
    await loadDocs()
  } catch (e) {
    msg.value = '上传失败'
  }
}
</script>

<style scoped>
.layout {
  display: flex;
  height: 100%;
}

/* 左侧 */
.upload-panel {
  width: 40%;
  padding: 20px;
  border-right: 1px solid #eee;
}

/* 右侧 */
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