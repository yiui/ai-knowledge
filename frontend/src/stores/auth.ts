import { computed, ref } from 'vue'

const TOKEN_KEY = 'access_token'
const USER_KEY = 'user'

export interface AuthUser {
  id: number
  username: string
  email: string | null
}

function loadUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthUser
  } catch {
    return null
  }
}

const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
const user = ref<AuthUser | null>(loadUser())
export const sessionValidated = ref(false)

export const isLoggedIn = computed(() => Boolean(token.value))

export function getToken(): string | null {
  return token.value
}

export function getUser(): AuthUser | null {
  return user.value
}

export function setAuth(accessToken: string, userData: AuthUser) {
  token.value = accessToken
  user.value = userData
  sessionValidated.value = true
  localStorage.setItem(TOKEN_KEY, accessToken)
  localStorage.setItem(USER_KEY, JSON.stringify(userData))
}

export function clearAuth() {
  token.value = null
  user.value = null
  sessionValidated.value = false
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}
