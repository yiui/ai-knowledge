<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1>注册</h1>
      <p class="subtitle">创建账号后即可使用知识库</p>

      <el-form @submit.prevent="handleRegister">
        <el-form-item label="用户名">
          <el-input v-model="username" placeholder="3-50 个字符" />
        </el-form-item>
        <el-form-item label="邮箱（选填）">
          <el-input v-model="email" placeholder="example@email.com" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="password"
            type="password"
            placeholder="至少 6 位"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input
            v-model="confirmPassword"
            type="password"
            placeholder="再次输入密码"
            show-password
            @keyup.enter="handleRegister"
          />
        </el-form-item>

        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="success" class="success">{{ success }}</p>

        <el-button type="primary" class="submit-btn" :loading="loading" @click="handleRegister">
          注册
        </el-button>
      </el-form>

      <p class="footer-link">
        已有账号？
        <router-link to="/login">返回登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { register } from '@/api/auth'

const router = useRouter()

const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')

const handleRegister = async () => {
  if (!username.value || !password.value) {
    error.value = '请填写用户名和密码'
    return
  }
  if (password.value.length < 6) {
    error.value = '密码至少 6 位'
    return
  }
  if (password.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }

  loading.value = true
  error.value = ''
  success.value = ''
  try {
    await register({
      username: username.value,
      password: password.value,
      email: email.value || undefined,
    })
    success.value = '注册成功，即将跳转到登录页…'
    setTimeout(() => router.replace('/login'), 1500)
  } catch (e: unknown) {
    const detail =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : '注册失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.auth-card {
  width: 400px;
  padding: 32px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
}

h1 {
  margin: 0 0 4px;
  font-size: 24px;
}

.subtitle {
  margin: 0 0 24px;
  color: #888;
  font-size: 14px;
}

.submit-btn {
  width: 100%;
  margin-top: 8px;
}

.error {
  color: #f56c6c;
  font-size: 14px;
  margin: 0 0 8px;
}

.success {
  color: #67c23a;
  font-size: 14px;
  margin: 0 0 8px;
}

.footer-link {
  margin-top: 20px;
  text-align: center;
  font-size: 14px;
  color: #666;
}

.footer-link a {
  color: #1677ff;
}
</style>
