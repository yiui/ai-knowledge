import { http } from './http'

import type { AuthUser } from '@/stores/auth'

export interface LoginPayload {
  username: string
  password: string
}

export interface RegisterPayload {
  username: string
  password: string
  email?: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

export const login = async (payload: LoginPayload) => {
  const res = await http.post<TokenResponse>('/auth/login', payload)
  return res.data
}

export const register = async (payload: RegisterPayload) => {
  const res = await http.post<AuthUser>('/auth/register', payload)
  return res.data
}

export const fetchMe = async () => {
  const res = await http.get<AuthUser>('/auth/me')
  return res.data
}
