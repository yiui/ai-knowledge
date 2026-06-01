<template>
  <div class="kb-page">
    <aside class="kb-sidebar">
      <div class="sidebar-header">
        <h2>我的知识库</h2>
        <el-button type="primary" size="small" @click="showCreateDialog = true">
          新建
        </el-button>
      </div>

      <div v-if="kbs.length === 0" class="empty-tip">
        暂无知识库，请先创建
      </div>

      <ul v-else class="kb-list">
        <li
          v-for="kb in kbs"
          :key="kb.id"
          :class="{ active: selectedId === kb.id }"
          @click="selectKb(kb.id)"
        >
          <span class="kb-name">{{ kb.name }}</span>
          <el-button
            type="danger"
            link
            size="small"
            @click.stop="handleDeleteKb(kb.id)"
          >
            删除
          </el-button>
        </li>
      </ul>
    </aside>

    <main class="kb-main">
      <UploadPanel v-if="selectedId" :knowledge-base-id="selectedId" />
      <div v-else class="placeholder">
        请选择或创建一个知识库，然后上传文档
      </div>
    </main>

    <el-dialog v-model="showCreateDialog" title="新建知识库" width="400px">
      <el-input
        v-model="newKbName"
        placeholder="请输入知识库名称"
        maxlength="100"
        @keyup.enter="handleCreate"
      />
      <p v-if="createError" class="error">{{ createError }}</p>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'

import {
  createKnowledgeBase,
  deleteKnowledgeBase,
  listKnowledgeBases,
  type KnowledgeBase,
} from '@/api/knowledgeBase'
import UploadPanel from '@/components/UploadPanel.vue'

const kbs = ref<KnowledgeBase[]>([])
const selectedId = ref<number | null>(null)
const showCreateDialog = ref(false)
const newKbName = ref('')
const creating = ref(false)
const createError = ref('')

const loadKbs = async () => {
  kbs.value = await listKnowledgeBases()
  if (kbs.value.length > 0 && !selectedId.value) {
    selectedId.value = kbs.value[0].id
  }
  if (selectedId.value && !kbs.value.some((kb) => kb.id === selectedId.value)) {
    selectedId.value = kbs.value[0]?.id ?? null
  }
}

const selectKb = (id: number) => {
  selectedId.value = id
}

const handleCreate = async () => {
  const name = newKbName.value.trim()
  if (!name) {
    createError.value = '请输入知识库名称'
    return
  }

  creating.value = true
  createError.value = ''
  try {
    const kb = await createKnowledgeBase(name)
    showCreateDialog.value = false
    newKbName.value = ''
    await loadKbs()
    selectedId.value = kb.id
  } catch (e: unknown) {
    const detail =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    createError.value = typeof detail === 'string' ? detail : '创建失败'
  } finally {
    creating.value = false
  }
}

const handleDeleteKb = async (id: number) => {
  try {
    await ElMessageBox.confirm('删除后该知识库内所有文档将被清除，是否继续？', '确认删除', {
      type: 'warning',
    })
    await deleteKnowledgeBase(id)
    await loadKbs()
  } catch {
    // cancelled or failed
  }
}

onMounted(loadKbs)
</script>

<style scoped>
.kb-page {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.kb-sidebar {
  width: 260px;
  border-right: 1px solid #eee;
  padding: 16px;
  overflow: auto;
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 16px;
}

.empty-tip {
  color: #999;
  font-size: 14px;
}

.kb-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.kb-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 4px;
}

.kb-list li:hover {
  background: #f5f7fa;
}

.kb-list li.active {
  background: #e6f4ff;
  color: #1677ff;
}

.kb-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  margin-right: 8px;
}

.kb-main {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #999;
}

.error {
  color: #f56c6c;
  font-size: 14px;
  margin-top: 8px;
}
</style>
