import { http } from './http'

import type { UploadLimits } from '@/config/upload'

export interface LlmConfig {
  provider: string
  model: string
  base_url: string
}

export interface AppConfig {
  llm?: LlmConfig
  upload?: UploadLimits
}

export const getAppConfig = async () => {
  const res = await http.get<AppConfig>('/config')
  return res.data
}
