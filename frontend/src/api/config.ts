import { http } from './http'

import type { UploadLimits } from '@/config/upload'

export interface AppConfig {
  upload?: UploadLimits
}

export const getAppConfig = async () => {
  const res = await http.get<AppConfig>('/config')
  return res.data
}
