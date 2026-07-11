<template>
  <div class="auth-page">
    <div class="bg-layer">
      <svg class="bg-lines" viewBox="0 0 1200 800" preserveAspectRatio="none">
        <line x1="100" y1="200" x2="350" y2="150" stroke="rgba(22,119,255,0.08)" stroke-width="1"/>
        <line x1="350" y1="150" x2="600" y2="300" stroke="rgba(22,119,255,0.06)" stroke-width="1"/>
        <line x1="600" y1="300" x2="850" y2="180" stroke="rgba(22,119,255,0.08)" stroke-width="1"/>
        <line x1="850" y1="180" x2="1100" y2="350" stroke="rgba(22,119,255,0.05)" stroke-width="1"/>
        <line x1="200" y1="500" x2="450" y2="420" stroke="rgba(100,140,255,0.06)" stroke-width="1"/>
        <line x1="450" y1="420" x2="700" y2="550" stroke="rgba(22,119,255,0.07)" stroke-width="1"/>
        <line x1="700" y1="550" x2="950" y2="450" stroke="rgba(100,140,255,0.05)" stroke-width="1"/>
        <line x1="50" y1="350" x2="300" y2="600" stroke="rgba(22,119,255,0.05)" stroke-width="1"/>
        <line x1="800" y1="100" x2="1050" y2="250" stroke="rgba(100,140,255,0.06)" stroke-width="1"/>
      </svg>

      <div class="bg-node bg-node--1"></div>
      <div class="bg-node bg-node--2"></div>
      <div class="bg-node bg-node--3"></div>
      <div class="bg-node bg-node--4"></div>
      <div class="bg-node bg-node--5"></div>
      <div class="bg-node bg-node--6"></div>
      <div class="bg-node bg-node--7"></div>
      <div class="bg-node bg-node--8"></div>

      <div class="bg-glow bg-glow--1"></div>
      <div class="bg-glow bg-glow--2"></div>
      <div class="bg-glow bg-glow--3"></div>

      <div class="bg-geo bg-geo--1">⬡</div>
      <div class="bg-geo bg-geo--2">◈</div>
      <div class="bg-geo bg-geo--3">△</div>
      <div class="bg-geo bg-geo--4">○</div>
    </div>

    <div class="auth-card">
      <div class="auth-brand">
        <span class="auth-logo">◆</span>
        <h1>创建账号</h1>
        <p>注册后即可使用 AI 知识库</p>
      </div>

      <div class="auth-form">
        <div class="field">
          <input v-model="username" placeholder="用户名（3-50 个字符）" autocomplete="username" />
        </div>
        <div class="field">
          <input v-model="email" placeholder="邮箱（选填）" autocomplete="email" />
        </div>
        <div class="field">
          <input v-model="password" type="password" placeholder="密码（至少 6 位）" autocomplete="new-password" />
        </div>
        <div class="field">
          <input
            v-model="confirmPassword"
            type="password"
            placeholder="确认密码"
            autocomplete="new-password"
            @keyup.enter="handleRegister"
          />
        </div>

        <p v-if="error" class="msg msg--error">{{ error }}</p>
        <p v-if="success" class="msg msg--success">{{ success }}</p>

        <button class="btn" :disabled="loading" @click="handleRegister">
          {{ loading ? '注册中…' : '注 册' }}
        </button>
      </div>

      <p class="auth-footer">
        已有账号？<router-link to="/login">返回登录</router-link>
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
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : '注册失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: linear-gradient(160deg, #f0f3f8 0%, #f8f9fc 40%, #eef2f8 100%);
}

.bg-layer { position: absolute; inset: 0; overflow: hidden; }

.bg-lines {
  position: absolute; inset: 0; width: 100%; height: 100%;
  animation: linesShift 20s ease-in-out infinite alternate;
}

@keyframes linesShift {
  0% { opacity: 0.5; }
  100% { opacity: 1; }
}

.bg-node {
  position: absolute;
  border-radius: 50%;
  animation: nodePulse 4s ease-in-out infinite alternate;
}

.bg-node--1 { width: 12px; height: 12px; background: rgba(22,119,255,0.35); top: 18%; left: 8%; }
.bg-node--2 { width: 8px; height: 8px; background: rgba(22,119,255,0.25); top: 12%; left: 29%; animation-delay: 0.6s; }
.bg-node--3 { width: 14px; height: 14px; background: rgba(80,120,255,0.3); top: 30%; left: 50%; animation-delay: 1.2s; }
.bg-node--4 { width: 10px; height: 10px; background: rgba(22,119,255,0.25); top: 15%; left: 71%; animation-delay: 1.8s; }
.bg-node--5 { width: 12px; height: 12px; background: rgba(100,140,255,0.3); top: 55%; left: 17%; animation-delay: 2.4s; }
.bg-node--6 { width: 8px; height: 8px; background: rgba(22,119,255,0.2); top: 45%; left: 38%; animation-delay: 3s; }
.bg-node--7 { width: 14px; height: 14px; background: rgba(80,120,255,0.3); top: 60%; left: 58%; animation-delay: 0.3s; }
.bg-node--8 { width: 10px; height: 10px; background: rgba(22,119,255,0.22); top: 48%; left: 79%; animation-delay: 1.5s; }

@keyframes nodePulse {
  0% { transform: scale(1); opacity: 0.5; box-shadow: 0 0 0 0 rgba(22,119,255,0.3); }
  100% { transform: scale(1.6); opacity: 1; box-shadow: 0 0 12px 4px rgba(22,119,255,0.12); }
}

.bg-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  animation: glowFloat 14s ease-in-out infinite alternate;
}

.bg-glow--1 {
  width: 600px; height: 600px;
  background: rgba(22,119,255,0.07);
  top: -20%; right: -10%;
}

.bg-glow--2 {
  width: 400px; height: 400px;
  background: rgba(80,100,220,0.05);
  bottom: -15%; left: -5%;
  animation-delay: -5s;
}

.bg-glow--3 {
  width: 300px; height: 300px;
  background: rgba(22,160,255,0.04);
  top: 40%; left: 55%;
  animation-delay: -10s;
  animation-duration: 16s;
}

@keyframes glowFloat {
  0% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(40px, -30px) scale(1.1); }
  66% { transform: translate(-25px, 20px) scale(0.9); }
  100% { transform: translate(15px, -10px) scale(1.05); }
}

.bg-geo {
  position: absolute;
  font-size: 28px;
  opacity: 0.06;
  color: #1677ff;
  animation: geoDrift 18s ease-in-out infinite;
}

.bg-geo--1 { top: 8%; right: 18%; font-size: 32px; }
.bg-geo--2 { top: 65%; left: 10%; font-size: 24px; animation-delay: -6s; }
.bg-geo--3 { bottom: 15%; right: 22%; font-size: 26px; animation-delay: -12s; }
.bg-geo--4 { top: 35%; left: 5%; font-size: 30px; animation-delay: -3s; }

@keyframes geoDrift {
  0% { transform: translate(0, 0) rotate(0deg); opacity: 0.03; }
  25% { transform: translate(20px, -15px) rotate(5deg); opacity: 0.08; }
  50% { transform: translate(-10px, -25px) rotate(-3deg); opacity: 0.04; }
  75% { transform: translate(-20px, 10px) rotate(8deg); opacity: 0.07; }
  100% { transform: translate(5px, 0) rotate(0deg); opacity: 0.03; }
}

.auth-card {
  position: relative;
  width: 410px;
  padding: 50px 44px 38px;
  background: #fff;
  border-radius: 22px;
  box-shadow:
    0 2px 4px rgba(0,0,0,0.03),
    0 12px 48px rgba(0,0,0,0.07),
    0 0 0 1px rgba(0,0,0,0.03);
}

.auth-brand { text-align: center; margin-bottom: 32px; }

.auth-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px; height: 52px;
  border-radius: 16px;
  background: linear-gradient(135deg, #1677ff, #5b8eff);
  color: #fff;
  font-size: 22px;
  margin-bottom: 20px;
  box-shadow: 0 6px 24px rgba(22,119,255,0.22);
}

.auth-brand h1 {
  margin: 0 0 8px;
  font-size: 26px;
  font-weight: 700;
  color: #14171f;
  letter-spacing: -0.5px;
}

.auth-brand p { margin: 0; font-size: 15px; color: #8b8f9a; }

.auth-form { display: flex; flex-direction: column; gap: 14px; }

.field input {
  width: 100%;
  padding: 14px 18px;
  border: 1.5px solid #e8eaf0;
  border-radius: 12px;
  font-size: 15px;
  color: #1d1f24;
  background: #f9fafc;
  outline: none;
  box-sizing: border-box;
  font-family: inherit;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}

.field input::placeholder { color: #b8bcc4; }
.field input:focus {
  border-color: #1677ff;
  box-shadow: 0 0 0 4px rgba(22,119,255,0.07);
  background: #fff;
}

.btn {
  width: 100%;
  padding: 14px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #1677ff, #4096ff);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  letter-spacing: 2px;
  transition: opacity 0.2s, transform 0.1s, box-shadow 0.2s;
  margin-top: 8px;
  box-shadow: 0 4px 20px rgba(22,119,255,0.2);
}

.btn:hover { opacity: 0.93; box-shadow: 0 6px 28px rgba(22,119,255,0.28); }
.btn:active { transform: scale(0.98); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }

.msg { font-size: 13px; margin: 0; text-align: center; }
.msg--error { color: #e85555; }
.msg--success { color: #389e0d; }

.auth-footer {
  margin-top: 28px;
  text-align: center;
  font-size: 14px;
  color: #a0a4ac;
}

.auth-footer a { color: #1677ff; text-decoration: none; font-weight: 600; }
.auth-footer a:hover { text-decoration: underline; }
</style>
